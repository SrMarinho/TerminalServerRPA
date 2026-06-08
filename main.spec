# -*- mode: python ; coding: utf-8 -*-
import sys
import tomllib
from pathlib import Path

block_cipher = None

with open("pyproject.toml", "rb") as _f:
    _VERSION = tomllib.load(_f)["project"]["version"]

a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=[],
    datas=[
        ("src/interfaces/web/templates", "src/interfaces/web/templates"),
        ("src/interfaces/web/static", "src/interfaces/web/static"),
        ("assets", "assets"),
        ("plugins", "plugins"),
        ("pyproject.toml", "."),
    ],
    hiddenimports=[
        "tsrpa",
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
        "src.automation.tasks",
        "src.automation.pages",
        "src.automation.pages.home_page",
        "src.automation.pages.senior_login_page",
        "src.automation.pages.sidebar_navigator",
        "src.automation.pages.ts_applications_page",
        "src.automation.pages.ts_login_page",
        "src.config",
        "src.config.version",
        "src.infrastructure.updater",
        "src.interfaces.gui.server",
        "src.interfaces.web.server",
        "src.interfaces.base_server",
        "webview",
        "webview.platforms.winforms",
        "pystray",
        "pystray._win32",
        "PIL",
        "PIL.Image",
        "jinja2",
        "pydantic",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "matplotlib", "scipy", "pandas", "IPython", "notebook"],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# opencv-python-headless already ships without Qt/GUI libs, so no manual strip.
# Drop the bundled playwright driver (downloaded at runtime to APP_DATA), and any
# committed bytecode/test artifacts that slipped into the data globs.
a.datas = [entry for entry in a.datas if "playwright" not in entry[1] or "driver" not in entry[1]]
a.binaries = [entry for entry in a.binaries if "playwright" not in entry[1] or "driver" not in entry[1]]

_JUNK = ("__pycache__", ".pyc", ".pyo")
a.datas = [entry for entry in a.datas if not any(j in entry[0] for j in _JUNK)]

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

splash = Splash(
    "assets/splash.png",
    binaries=a.binaries,
    datas=a.datas,
    text_pos=(260, 296),
    text_size=10,
    text_color="#5a5f6b",
    text_default=f"v{_VERSION} — carregando...",
    minify_script=True,
)

exe = EXE(
    pyz,
    a.scripts,
    splash,
    [],
    name="TerminalServerRPA",
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
    icon="assets/icon.ico",
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    splash.binaries,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="TerminalServerRPA",
)

import os
_stub = os.path.join("dist", "TerminalServerRPA.exe")
if os.path.exists(_stub):
    os.remove(_stub)
