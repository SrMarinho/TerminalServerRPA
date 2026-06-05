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
        ("assets", "assets"),
        ("plugins", "plugins"),
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
        "src.automation.tasks.financas",
        "src.automation.tasks.financas.gestao_contas_receber",
        "src.automation.tasks.financas.gestao_contas_receber.contas_receber",
        "src.automation.tasks.financas.gestao_contas_receber.contas_receber.relatorios",
        "src.automation.tasks.financas.gestao_contas_receber.contas_receber.relatorios.report_generation",
        "src.automation.pages",
        "src.automation.pages.contas_receber",
        "src.automation.pages.contas_receber.reports",
        "src.automation.pages.contas_receber.reports.r703_rot_conciliacao",
        "src.automation.pages.contas_receber.reports.constants",
        "src.automation.pages.contas_receber.reports.base_report",
        "src.automation.pages.contas_receber.selecao_modelos_para_execucao_page",
        "src.automation.pages.contas_receber.valores_entrada_modelo_page",
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

_CV2_GUI_PREFIXES = ("Qt5", "Qt6", "libQt", "opengl32sw")
a.binaries = [b for b in a.binaries if not b[0].startswith(_CV2_GUI_PREFIXES)]

a.datas = [entry for entry in a.datas if "playwright" not in entry[1] or "driver" not in entry[1]]
a.binaries = [entry for entry in a.binaries if "playwright" not in entry[1] or "driver" not in entry[1]]

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

splash = Splash(
    "assets/splash.png",
    binaries=a.binaries,
    datas=a.datas,
    text_pos=(260, 296),
    text_size=10,
    text_color="#5a5f6b",
    text_default="carregando...",
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
