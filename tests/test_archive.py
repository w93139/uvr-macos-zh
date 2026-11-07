import marshal
from pathlib import Path
import types
import zlib

import pytest

from uvr_zh.archive import Archive, Member, add_hook, parse, serialize, unpack, verify_preserved


def sample():
    main = marshal.dumps(compile("answer = 42", "UVR.py", "exec"))
    members = (
        Member("pyi_rth__tkinter", b"s", 1, len(main), zlib.compress(main)),
        Member("UVR", b"s", 1, len(main), zlib.compress(main)),
        Member("pyi-contents-directory _internal", b"o", 0, 0, b""),
        Member("PYZ-00.pyz", b"z", 0, 11, b"originalpyz"),
    )
    return serialize(Archive(b"native prefix", members, 311, b"Python"))


def test_preserves_original_main_and_pyz_bytes_and_order():
    original = sample()
    patched = add_hook(original, "localized = True")
    verify_preserved(original, patched)
    members = parse(patched).members
    assert [m.name for m in members] == ["pyi_rth__tkinter", "pyi_rth_uvr_zh", "UVR", "pyi-contents-directory _internal", "PYZ-00.pyz"]
    assert parse(original).prefix == parse(patched).prefix
    scope = {}
    exec(marshal.loads(unpack(members[1])), scope)
    exec(marshal.loads(unpack(members[2])), scope)
    assert scope["localized"] is True and scope["answer"] == 42


def test_rejects_wrong_python_and_double_install():
    archive = parse(sample())
    wrong = serialize(Archive(archive.prefix, archive.members, 312, archive.library))
    with pytest.raises(ValueError, match="Python 3.11"):
        add_hook(wrong, "pass")
    with pytest.raises(ValueError, match="already localized"):
        add_hook(add_hook(sample(), "pass"), "pass")


@pytest.mark.parametrize("payload", [b"", b"MEI\014\013\012\013\016", sample()[:-1]])
def test_rejects_corrupt_archive(payload):
    with pytest.raises((ValueError, UnicodeDecodeError)):
        parse(payload)


def test_detects_any_original_member_change():
    archive = parse(add_hook(sample(), "pass"))
    members = list(archive.members)
    members[-1] = Member("PYZ-00.pyz", b"z", 0, 7, b"changed")
    damaged = serialize(Archive(archive.prefix, tuple(members), archive.python_version, archive.library))
    with pytest.raises(ValueError, match="Original UVR"):
        verify_preserved(sample(), damaged)
