"""Conservative reader/writer for the verified PyInstaller CArchive layout."""

from __future__ import annotations

from dataclasses import dataclass
import marshal
import struct
import types
import zlib

MAGIC = b"MEI\014\013\012\013\016"
COOKIE = struct.Struct("!8sIIII64s")
ENTRY = struct.Struct("!iIIIBc")
HOOK_NAME = "pyi_rth_uvr_zh"


@dataclass(frozen=True)
class Member:
    name: str
    kind: bytes
    flag: int
    size: int
    payload: bytes


@dataclass(frozen=True)
class Archive:
    prefix: bytes
    members: tuple[Member, ...]
    python_version: int
    library: bytes


def parse(data):
    cookie_at = data.rfind(MAGIC)
    if cookie_at < 0 or cookie_at + COOKIE.size > len(data):
        raise ValueError("Missing or truncated PyInstaller archive cookie")
    _, length, toc_at, toc_size, version, library = COOKIE.unpack_from(data, cookie_at)
    start = cookie_at + COOKIE.size - length
    if start < 0 or toc_at < 0 or toc_size <= 0 or start + toc_at + toc_size != cookie_at:
        raise ValueError("Invalid PyInstaller archive bounds")
    cursor, end = start + toc_at, cookie_at
    members, names, spans = [], set(), []
    while cursor < end:
        if cursor + ENTRY.size > end:
            raise ValueError("Truncated archive table entry")
        record_size, offset, size, unpacked, flag, kind = ENTRY.unpack_from(data, cursor)
        if record_size <= ENTRY.size or record_size % 16 or cursor + record_size > end:
            raise ValueError("Invalid archive table record size")
        raw_name = data[cursor + ENTRY.size : cursor + record_size]
        if b"\0" not in raw_name:
            raise ValueError("Unterminated archive member name")
        name = raw_name.split(b"\0", 1)[0].decode("utf-8")
        if not name or name in names or flag not in (0, 1):
            raise ValueError("Invalid or duplicate archive member")
        if offset + size > toc_at:
            raise ValueError("Archive member crosses table boundary")
        if size:
            for left, right in spans:
                if max(left, offset) < min(right, offset + size):
                    raise ValueError("Overlapping archive members")
            spans.append((offset, offset + size))
        names.add(name)
        members.append(Member(name, kind, flag, unpacked, data[start + offset : start + offset + size]))
        cursor += record_size
    if cursor != end or not library.rstrip(b"\0"):
        raise ValueError("Invalid archive table or Python library")
    return Archive(data[:start], tuple(members), version, library)


def unpack(member):
    raw = zlib.decompress(member.payload) if member.flag else member.payload
    if len(raw) != member.size:
        raise ValueError("Archive member size mismatch")
    return raw


def serialize(archive):
    payload = bytearray()
    table = bytearray()
    for member in archive.members:
        name = member.name.encode("utf-8") + b"\0"
        record_size = (ENTRY.size + len(name) + 15) // 16 * 16
        table.extend(ENTRY.pack(record_size, len(payload), len(member.payload), member.size, member.flag, member.kind))
        table.extend(name.ljust(record_size - ENTRY.size, b"\0"))
        payload.extend(member.payload)
    cookie = COOKIE.pack(MAGIC, len(payload) + len(table) + COOKIE.size, len(payload), len(table), archive.python_version, archive.library)
    return archive.prefix + payload + table + cookie


def add_hook(data, source):
    archive = parse(data)
    if archive.python_version != 311:
        raise ValueError("Only the verified Python 3.11 UVR build is supported")
    if any(m.name == HOOK_NAME for m in archive.members):
        raise ValueError("Archive is already localized")
    matches = [m for m in archive.members if m.name == "UVR" and m.kind == b"s"]
    if len(matches) != 1:
        raise ValueError("Expected exactly one UVR entry point")
    # The caller verifies the complete executable hash before any marshal load.
    if not isinstance(marshal.loads(unpack(matches[0])), types.CodeType):
        raise ValueError("UVR entry point is not a Python code object")
    code = compile(source, "uvr_zh_runtime_hook.py", "exec", dont_inherit=True, optimize=0)
    raw = marshal.dumps(code)
    hook = Member(HOOK_NAME, b"s", 1, len(raw), zlib.compress(raw, 9))
    members = []
    for member in archive.members:
        if member.name == "UVR":
            members.append(hook)
        members.append(member)
    result = serialize(Archive(archive.prefix, tuple(members), archive.python_version, archive.library))
    verify_preserved(data, result)
    return result


def verify_preserved(before, after):
    original, patched = parse(before), parse(after)
    actual = [m for m in patched.members if m.name != HOOK_NAME]
    if actual != list(original.members):
        raise ValueError("Original UVR archive members changed")
    hooks = [m for m in patched.members if m.name == HOOK_NAME]
    if len(hooks) != 1:
        raise ValueError("Expected exactly one localization hook")
    if not isinstance(marshal.loads(unpack(hooks[0])), types.CodeType):
        raise ValueError("Localization hook is not a Python code object")
