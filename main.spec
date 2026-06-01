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
        "src.automation.tasks",
        "src.automation.tasks.financas",
        "src.automation.tasks.financas.gestao_contas_receber",
        "src.automation.tasks.financas.gestao_contas_receber.contas_receber",
        "src.automation.tasks.financas.gestao_contas_receber.contas_receber.relatorios",
        "src.automation.tasks.financas.gestao_contas_receber.contas_receber.relatorios.report_generation",
        "src.automation.pages",
        "src.automation.pages.contas_receber",
        "src.automation.pages.contas_receber.reports",
        "src.automation.pages.contas_receber.reports.rot_conciliacao_703",
        "src.config",
        "src.config.version",
        "src.infrastructure.updater",
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
