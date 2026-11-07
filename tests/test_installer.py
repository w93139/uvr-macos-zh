import hashlib
import json
import plistlib

import pytest

from uvr_zh import installer


@pytest.fixture
def app(tmp_path, monkeypatch):
    source = tmp_path / "Original.app"
    (source / "Contents/MacOS").mkdir(parents=True)
    (source / "Contents/Resources").mkdir()
    (source / "Contents/Frameworks").mkdir()
    executable = source / "Contents/MacOS/UVR"
    executable.write_bytes(b"verified fixture")
    (source / "Contents/Info.plist").write_bytes(plistlib.dumps({"CFBundleIdentifier": "UVR", "CFBundleExecutable": "UVR"}))
    monkeypatch.setattr(installer.platform, "system", lambda: "Darwin")
    monkeypatch.setattr(installer.platform, "machine", lambda: "arm64")
    monkeypatch.setattr(installer, "SOURCE_HASH", hashlib.sha256(executable.read_bytes()).hexdigest())
    class Parsed:
        python_version = 311
    monkeypatch.setattr(installer, "parse", lambda _: Parsed())
    return source, tmp_path / "Chinese.app"


def test_preflight_rejects_unknown_binary_without_creating_destination(app):
    source, target = app
    (source / "Contents/MacOS/UVR").write_bytes(b"different build")
    with pytest.raises(ValueError, match="Unverified"):
        installer.preflight(source, target)
    assert not target.exists()


def test_preflight_never_overwrites_existing_destination(app):
    source, target = app
    target.mkdir()
    marker = target / "keep.txt"
    marker.write_text("existing installation")
    with pytest.raises(ValueError, match="already exists"):
        installer.preflight(source, target)
    assert marker.read_text() == "existing installation"


def test_preflight_rejects_dangling_destination_symlink(app):
    source, target = app
    target.symlink_to(target.parent / "missing.app")
    with pytest.raises(ValueError, match="already exists"):
        installer.preflight(source, target)
    assert target.is_symlink()


def test_preflight_rejects_destination_inside_source(app):
    source, _ = app
    target = source / "Nested.app"
    with pytest.raises(ValueError, match="inside"):
        installer.preflight(source, target)
    assert not target.exists()


def test_preflight_rejects_source_symlink(app):
    source, target = app
    alias = source.parent / "Alias.app"
    alias.symlink_to(source)
    with pytest.raises(ValueError, match="non-symlink"):
        installer.preflight(alias, target)


def test_preflight_rejects_unknown_bundle_identity(app):
    source, target = app
    (source / "Contents/Info.plist").write_bytes(plistlib.dumps({"CFBundleIdentifier": "different", "CFBundleExecutable": "UVR"}))
    with pytest.raises(ValueError, match="identity"):
        installer.preflight(source, target)


@pytest.mark.parametrize("relative", ["Contents", "Contents/MacOS", "Contents/Resources", "Contents/Frameworks"])
def test_preflight_rejects_symlinked_write_ancestors(app, relative):
    source, target = app
    original = source / relative
    moved = source.parent / (relative.replace("/", "-") + "-external")
    original.rename(moved)
    original.symlink_to(moved, target_is_directory=True)
    with pytest.raises(ValueError, match="write ancestor"):
        installer.preflight(source, target)
    assert not target.exists()


def test_preflight_rejects_outbound_link_but_allows_internal_link(app):
    source, target = app
    resources = source / "Contents/Resources"
    (resources / "internal").symlink_to("../MacOS/UVR")
    installer.validate_bundle_paths(source)
    outside = source.parent / "outside.txt"
    outside.write_text("must not be touched")
    (resources / "external").symlink_to(outside)
    with pytest.raises(ValueError, match="outside its root"):
        installer.preflight(source, target)
    assert outside.read_text() == "must not be touched"
