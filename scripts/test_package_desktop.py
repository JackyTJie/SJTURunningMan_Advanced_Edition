"""验证打包布局，系统打包命令通过 mock 隔离。"""
import json
import plistlib
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from package_desktop import ROOT, TAURI_CONFIG, cargo_version, deb_depends, package


class PackagingTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.binary = self.root / "sjturunningman"
        self.binary.write_bytes(b"offline packaging fixture")

    @patch("package_desktop.subprocess.run")
    def test_linux_control_and_desktop_launcher(self, run):
        output = self.root / "output"
        package("linux", self.binary, output, "4.5.0-rc.1", "arm64")
        stage = output / "deb-arm64"
        control = (stage / "DEBIAN/control").read_text(encoding="utf-8")
        self.assertIn("Architecture: arm64", control)
        self.assertIn("Version: 4.5.0~rc.1", control)
        self.assertIn("libc6 (>= 2.39)", control)
        self.assertIn("libwebkit2gtk-4.1-0", control)
        self.assertIn(f"Depends: {', '.join(deb_depends())}\n", control)
        self.assertEqual((stage / "usr/bin/sjturunningman").read_bytes(), self.binary.read_bytes())
        self.assertIn("Exec=sjturunningman", (stage / "usr/share/applications/sjturunningman.desktop").read_text())
        self.assertEqual(run.call_args.args[0][0], "dpkg-deb")
        with self.assertRaises(FileExistsError):
            package("linux", self.binary, output, "4.5.0", "arm64")

    def test_deb_depends_come_from_the_tauri_config(self):
        depends = deb_depends()
        config = json.loads(TAURI_CONFIG.read_text(encoding="utf-8"))
        self.assertEqual(depends, config["bundle"]["linux"]["deb"]["depends"])
        self.assertIn("libwebkit2gtk-4.1-0", depends)
        self.assertIn("libgtk-3-0", depends)
        control = (ROOT / "scripts/package_desktop.py").read_text(encoding="utf-8")
        self.assertNotIn("libxkbcommon-x11-0", control)

    @patch("pathlib.Path.symlink_to")
    @patch("package_desktop.subprocess.run")
    def test_macos_bundle_metadata_and_application_link(self, run, symlink):
        output = self.root / "output"
        package("macos", self.binary, output, "4.5.0-rc.1", "amd64")
        contents = output / "dmg-stage/SJTURunningMan.app/Contents"
        with (contents / "Info.plist").open("rb") as file:
            info = plistlib.load(file)
        self.assertEqual(info["CFBundleShortVersionString"], "4.5.0")
        self.assertEqual(info["CFBundleExecutable"], "SJTURunningMan")
        self.assertTrue((contents / "Resources/SJTURM.icns").exists())
        symlink.assert_called_once_with("/Applications")
        self.assertEqual([call.args[0][0] for call in run.call_args_list], ["codesign", "hdiutil"])

    def test_invalid_version_rejected_before_staging(self):
        for version in ["../escape", "4.5", "4.5.0/../../bad", "4.5.0\n"]:
            with self.subTest(version=version), self.assertRaises(ValueError):
                package("linux", self.binary, self.root / "output", version, "amd64")
        self.assertFalse((self.root / "output").exists())

    def test_version_defaults_to_the_cargo_manifest(self):
        self.assertRegex(cargo_version(), r"^\d+\.\d+\.\d+")

    @patch("package_desktop.subprocess.run")
    def test_linux_rejects_binary_arch_mismatch(self, run):
        elf = bytearray(64)
        elf[0:4] = b"\x7fELF"
        elf[18:20] = (0x3E).to_bytes(2, "little")  # x86-64
        self.binary.write_bytes(bytes(elf))
        package("linux", self.binary, self.root / "matching", "4.5.0", "amd64")
        self.assertTrue((self.root / "matching/deb-amd64/usr/bin/sjturunningman").exists())
        with self.assertRaises(ValueError):
            package("linux", self.binary, self.root / "mismatch", "4.5.0", "arm64")
        self.assertFalse((self.root / "mismatch/deb-arm64").exists())


if __name__ == "__main__":
    unittest.main()
