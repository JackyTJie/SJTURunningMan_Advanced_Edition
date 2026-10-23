"""打包 Tauri 2 桌面产物；仅在构建机运行，不随应用分发。"""
import argparse
import json
import os
from pathlib import Path
import plistlib
import re
import shutil
import subprocess


ROOT = Path(__file__).resolve().parents[1]

ELF_MACHINES = {"amd64": 0x3E, "arm64": 0xB7}

TAURI_CONFIG = ROOT / "desktop" / "src-tauri" / "tauri.conf.json"

# Tauri 的 deb 配置没有 Recommends 字段，这一项只存在于手工打包的 control 里。
DEB_RECOMMENDS = "xdg-desktop-portal, fonts-noto-cjk"


def deb_depends():
    """deb 依赖的唯一来源是 tauri.conf.json 的 bundle.linux.deb.depends。"""
    config = json.loads(TAURI_CONFIG.read_text(encoding="utf-8"))
    depends = config["bundle"]["linux"]["deb"]["depends"]
    if not isinstance(depends, list) or not all(
        isinstance(item, str) and item.strip() for item in depends
    ):
        raise ValueError(f"{TAURI_CONFIG.relative_to(ROOT)} has an invalid bundle.linux.deb.depends")
    return [item.strip() for item in depends]


def cargo_version():
    """桌面版本号的唯一来源是 desktop/src-tauri/Cargo.toml 的 package.version。"""
    manifest = (ROOT / "desktop" / "src-tauri" / "Cargo.toml").read_text(encoding="utf-8")
    match = re.search(r'(?m)^version\s*=\s*"([^"]+)"', manifest)
    if not match:
        raise ValueError("desktop/src-tauri/Cargo.toml is missing package.version")
    return match.group(1)


def check_binary_arch(binary, arch):
    """deb 的 Architecture 由 --arch 决定，这里核对输入 ELF 的 machine 是否一致。"""
    header = binary.read_bytes()[:20]
    if header[:4] != b"\x7fELF":
        return  # 非 ELF（如 macOS Mach-O）不在这里判断
    if len(header) < 20:
        raise ValueError("Truncated ELF header")
    if int.from_bytes(header[18:20], "little") != ELF_MACHINES[arch]:
        raise ValueError(f"Binary architecture does not match --arch {arch}")


def package(platform, binary, output, version, arch):
    if not re.fullmatch(r"\d+\.\d+\.\d+(?:[-+][A-Za-z0-9.-]+)?", version):
        raise ValueError("Invalid APP_VERSION")
    binary = binary.resolve(strict=True)
    output.mkdir(parents=True, exist_ok=True)
    if platform == "macos":
        stage = output / "dmg-stage"
        contents = stage / "SJTURunningMan.app" / "Contents"
        if stage.exists():
            raise FileExistsError("Use a fresh output directory for packaging")
        (contents / "MacOS").mkdir(parents=True)
        (contents / "Resources").mkdir()
        shutil.copy2(binary, contents / "MacOS" / "SJTURunningMan")
        shutil.copy2(ROOT / "assets/SJTURM.icns", contents / "Resources/SJTURM.icns")
        with (contents / "Info.plist").open("wb") as file:
            plistlib.dump({
                "CFBundleExecutable": "SJTURunningMan",
                "CFBundleIdentifier": "com.sjtu.runningman",
                "CFBundleName": "SJTURunningMan",
                "CFBundleDisplayName": "SJTU RunningMan",
                "CFBundlePackageType": "APPL",
                "CFBundleShortVersionString": version.split("-")[0].split("+")[0],
                "CFBundleVersion": version.split("-")[0].split("+")[0],
                "CFBundleIconFile": "SJTURM.icns",
                "NSHighResolutionCapable": True,
                "LSMinimumSystemVersion": "11.0",
                "LSApplicationCategoryType": "public.app-category.education",
            }, file)
        subprocess.run(["codesign", "--force", "--deep", "--sign", "-", str(contents.parent)], check=True)
        (stage / "Applications").symlink_to("/Applications")
        subprocess.run(["hdiutil", "create", "-volname", f"SJTURunningMan {version}", "-srcfolder", str(stage),
                        "-ov", "-format", "UDZO", str(output / f"SJTURunningMan_{version}_macOS.dmg")], check=True)
    else:
        check_binary_arch(binary, arch)
        stage = output / f"deb-{arch}"
        if stage.exists():
            raise FileExistsError("Use a fresh output directory for packaging")
        for directory in ["DEBIAN", "usr/bin", "usr/share/applications", "usr/share/pixmaps"]:
            (stage / directory).mkdir(parents=True, exist_ok=True)
        shutil.copy2(binary, stage / "usr/bin/sjturunningman")
        (stage / "usr/bin/sjturunningman").chmod(0o755)
        shutil.copy2(ROOT / "assets/SJTURM.png", stage / "usr/share/pixmaps/sjturunningman.png")
        (stage / "usr/share/applications/sjturunningman.desktop").write_text(
            "[Desktop Entry]\nType=Application\nName=SJTU RunningMan\nExec=sjturunningman\n"
            "Icon=sjturunningman\nTerminal=false\nCategories=Education;Sports;\n", encoding="utf-8")
        (stage / "DEBIAN/control").write_text(
            f"Package: sjturunningman\nVersion: {version.replace('-', '~', 1)}\nArchitecture: {arch}\n"
            "Maintainer: Jacky Tang <tang.jie@live.com>\n"
            f"Depends: {', '.join(deb_depends())}\nRecommends: {DEB_RECOMMENDS}\n"
            "Homepage: https://github.com/JackyTJie/SJTURunningMan_Advanced_Edition\n"
            "Description: SJTU RunningMan Tauri desktop client\n"
            " Rust backend with a Material Design 3 interface (React 19 + @material/web).\n"
            " Uses the system WebKitGTK webview; no bundled Chromium.\n"
            " Built on Ubuntu 24.04 (glibc 2.39); newer distributions are backwards compatible.\n",
            encoding="utf-8",
        )
        subprocess.run(["dpkg-deb", "--build", "--root-owner-group", str(stage),
                        str(output / f"SJTURunningMan_{version}_linux_{arch}.deb")], check=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("platform", choices=["macos", "linux"])
    parser.add_argument("--binary", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=ROOT / "dist")
    parser.add_argument("--arch", choices=["amd64", "arm64"], default="amd64")
    parser.add_argument("--version", default=os.environ.get("APP_VERSION") or cargo_version())
    args = parser.parse_args()
    package(args.platform, args.binary, args.output, args.version, args.arch)
