# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

block_cipher = None

project_root = Path(SPECPATH).resolve()
assets_dir = project_root / 'assets'
icon_path = assets_dir / 'SJTURM.ico'

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
        'src.trajectory_risk_analyzer',
        'utils.auxiliary_util',
        'assets.resources_rc',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='SJTURunningMan',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(icon_path),
)
