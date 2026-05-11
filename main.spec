# -*- mode: python ; coding: utf-8 -*-
import sys
from pathlib import Path

block_cipher = None

a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=[],
    datas=[
        ("src/interfaces/web/templates", "src/interfaces/web/templates"),
        ("src/interfaces/web/static", "src/interfaces/web/static"),
    ],
    hiddenimports=[
        "structlog",
        "structlog.dev",
        "structlog.processors",
        "structlog.stdlib",
        "keyring",
        "keyring.backends.Windows",
        "cryptography",
        "cryptography.fernet",
        "fastapi",
        "uvicorn",
        "httpx",
        "typer",
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
    name="senior-rpa",
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
)
