"""Install a separate localized copy; never patch the source application."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import plistlib
import shutil
import subprocess
import sys
import tempfile

from .archive import add_hook, parse, verify_preserved
from .hook import Translator

SOURCE_HASH = "aaf8f36737d698af6d536a88d9072682d51b4099c267ea72373958768adfbb16"
DEFAULT_SOURCE = Path("/Applications/Ultimate Vocal Remover.app")
DEFAULT_DESTINATION = Path("/Applications/Ultimate Vocal Remover 中文版.app")
OFFICIAL_DOWNLOAD = "https://github.com/Anjok07/ultimatevocalremovergui/releases/download/v5.6/Ultimate_Vocal_Remover_v5_6_MacOS_arm64.dmg"
PACKAGE = Path(__file__).resolve().parent


def sha256(path):
    result = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(block)
    return result.hexdigest()


def validate_bundle_paths(bundle):
    """Every directory we write through must belong to this bundle itself."""
    bundle = Path(bundle)
    root = bundle.resolve()
    for relative in ("Contents", "Contents/MacOS", "Contents/Resources", "Contents/Frameworks"):
        path = bundle / relative
        if path.is_symlink() or not path.is_dir() or not path.resolve().is_relative_to(root):
            raise ValueError("Bundle contains a symlinked or invalid write ancestor: " + relative)
    for relative in ("Contents/Info.plist", "Contents/MacOS/UVR"):
        path = bundle / relative
        if path.is_symlink() or not path.is_file() or not path.resolve().is_relative_to(root):
            raise ValueError("Bundle metadata and executable must be contained regular files")
    if os.path.lexists(bundle / "Contents/Resources/uvr_zh"):
        raise ValueError("Bundle already contains localization resources")
    # codesign --deep visits nested frameworks. Official internal links are fine;
    # an outbound symlink could make a staged signing operation touch other files.
    for parent, directories, files in os.walk(bundle, followlinks=False):
        for name in directories + files:
            path = Path(parent) / name
            if path.is_symlink() and not path.resolve().is_relative_to(root):
                raise ValueError("Bundle contains a symlink outside its root: " + str(path.relative_to(bundle)))


def preflight(source, destination):
    if sys.version_info[:2] != (3, 11):
        raise ValueError("Installer requires Python 3.11 to match the app bytecode")
    if platform.system() != "Darwin" or platform.machine() != "arm64":
        raise ValueError("This release supports Apple Silicon macOS only")
    source, destination = Path(source).expanduser().absolute(), Path(destination).expanduser().absolute()
    if source.is_symlink() or not source.is_dir() or source.suffix != ".app":
        raise ValueError("Source must be an installed, non-symlink .app directory")
    if destination.suffix != ".app" or not destination.parent.is_dir():
        raise ValueError("Destination must be a new .app in an existing directory")
    if os.path.lexists(destination):
        raise ValueError("Destination already exists; nothing will be overwritten")
    if source.resolve() in destination.resolve().parents:
        raise ValueError("Destination cannot be inside the source app")
    validate_bundle_paths(source)
    info_path = source / "Contents/Info.plist"
    executable = source / "Contents/MacOS/UVR"
    if info_path.is_symlink() or executable.is_symlink():
        raise ValueError("Source metadata and executable must be regular files")
    info = plistlib.loads(info_path.read_bytes())
    if info.get("CFBundleExecutable") != "UVR" or info.get("CFBundleIdentifier") != "UVR":
        raise ValueError("Unexpected UVR bundle identity")
    digest = sha256(executable)
    if digest != SOURCE_HASH:
        raise ValueError("Unverified UVR executable: refusing to modify this build (SHA-256 " + digest + ")")
    archive = parse(executable.read_bytes())
    if archive.python_version != 311:
        raise ValueError("Unexpected embedded Python version")
    translations = json.loads((PACKAGE / "translations.json").read_text(encoding="utf-8"))
    Translator(translations)
    if not translations:
        raise ValueError("Translation catalog is empty")
    for command in ("/usr/bin/ditto", "/usr/bin/codesign"):
        if not Path(command).is_file():
            raise ValueError("Required macOS utility not found: " + command)
    return source, destination, info, translations


def install(source, destination):
    source, destination, info, translations = preflight(source, destination)
    from PyInstaller.utils.osx import fix_exe_for_code_signing, update_exe_identifier

    stage_root = Path(tempfile.mkdtemp(prefix=".uvr-zh-", dir=destination.parent))
    stage = stage_root / destination.name
    try:
        print("Copying official app; the English original is preserved.", flush=True)
        subprocess.run(["/usr/bin/ditto", str(source), str(stage)], check=True)
        # Recheck the actual copy before codesign or any writes (source may change).
        validate_bundle_paths(stage)
        executable = stage / "Contents/MacOS/UVR"
        if sha256(executable) != SOURCE_HASH:
            raise ValueError("Copied executable no longer matches the verified source")
        original = executable.read_bytes()
        # Remove only the signature of our private copy, before changing its archive.
        subprocess.run(["/usr/bin/codesign", "--remove-signature", str(executable)], check=True)
        unsigned = executable.read_bytes()
        patched = add_hook(unsigned, (PACKAGE / "hook.py").read_text(encoding="utf-8"))
        executable.write_bytes(patched)
        fix_exe_for_code_signing(str(executable))
        update_exe_identifier(str(executable), str(executable))
        resources = stage / "Contents/Resources/uvr_zh"
        resources.mkdir()
        shutil.copy2(PACKAGE / "translations.json", resources / "translations.json")
        manifest = {
            "patch_version": "0.1.0", "language": "zh-CN",
            "source_executable_sha256": SOURCE_HASH,
            "official_download": OFFICIAL_DOWNLOAD,
            "translation_entries": len(translations),
            "scope": "Tk display text only; original archive members preserved byte-for-byte",
        }
        (resources / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        info.update(CFBundleIdentifier="local.uvr.zhCN.v56.arm64", CFBundleName="UVR 中文版",
                    CFBundleDisplayName="UVR 中文版", CFBundleShortVersionString="5.6.0",
                    CFBundleGetInfoString="Unofficial Simplified Chinese display patch 0.1.0")
        (stage / "Contents/Info.plist").write_bytes(plistlib.dumps(info))
        print("Signing the localized copy locally (no Apple notarization).", flush=True)
        subprocess.run(["/usr/bin/codesign", "--force", "--deep", "--sign", "-", "--timestamp=none", str(stage)], check=True)
        subprocess.run(["/usr/bin/codesign", "--verify", "--deep", "--strict", str(stage)], check=True)
        verify_preserved(original, executable.read_bytes())
        if sha256(source / "Contents/MacOS/UVR") != SOURCE_HASH:
            raise ValueError("Original executable changed during installation")
        if os.path.lexists(destination):
            raise ValueError("Destination appeared during installation; refusing to replace it")
        stage.rename(destination)
        print("Installed: " + str(destination), flush=True)
        return destination
    finally:
        # Remove only our generated temporary staging directory.
        shutil.rmtree(stage_root, ignore_errors=True)


def main(argv=None):
    parser = argparse.ArgumentParser(description="UVR 5.6 Apple Silicon 简体中文显示补丁（保留英文原版）")
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--destination", type=Path, default=DEFAULT_DESTINATION)
    parser.add_argument("--check", action="store_true", help="只检查兼容性，不写入应用")
    args = parser.parse_args(argv)
    try:
        if args.check:
            source, destination, _, catalog = preflight(args.source, args.destination)
            print(json.dumps({"compatible": True, "source": str(source), "destination": str(destination),
                              "translation_entries": len(catalog), "verified_sha256": SOURCE_HASH}, ensure_ascii=False, indent=2))
        else:
            install(args.source, args.destination)
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        parser.exit(1, "安装未完成：" + str(error) + "\n")


if __name__ == "__main__":
    main()
