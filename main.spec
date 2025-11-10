# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['qtui.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('assets', 'assets'),
        ('default.txt', '.'),
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
    icon='assets\\SJTURM.png',
)
