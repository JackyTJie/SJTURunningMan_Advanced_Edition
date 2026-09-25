# -*- mode: python ; coding: utf-8 -*-

import sys
from pathlib import Path

project_root = Path(SPECPATH).resolve()
assets_dir = project_root / 'assets'
is_mac = sys.platform == 'darwin'
app_version = '4.4.0'
icon_path = assets_dir / ('SJTURM.icns' if is_mac else 'SJTURM.ico')

a = Analysis(
    [str(project_root / 'qtui.py')],
    pathex=[str(project_root)],
    binaries=[],
    datas=[
        (str(assets_dir), 'assets'),
    ],
    hiddenimports=[
        'PySide6.QtCore',
        'PySide6.QtGui',
        'PySide6.QtWidgets',
        'requests',
        'tenacity',
        'src.main',
        'src.api_client',
        'src.data_generator',
        'src.info_dialog',
        'src.login',
        'src.config',
        'src.route_preview',
        'utils.auxiliary_util',
        'assets.resources_rc',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['PIL', 'numpy', 'matplotlib', 'tkinter', 'scipy', 'pandas',
              'cryptography', 'cffi', 'pycparser'],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='SJTURunningMan',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=not sys.platform == 'darwin',
    upx_exclude=[],
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch='universal2' if is_mac else None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(icon_path),
)

if is_mac:
    app = BUNDLE(
        exe,
        name='SJTURunningMan.app',
        icon=str(icon_path),
        bundle_identifier='com.sjtu.runningman',
        info_plist={
            'CFBundleShortVersionString': app_version,
            'CFBundleVersion': app_version,
            'NSHighResolutionCapable': True,
        },
    )
