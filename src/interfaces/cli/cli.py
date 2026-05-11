import asyncio
from getpass import getpass
from pathlib import Path

import typer

from src.infrastructure.vault import Vault

vault_app = typer.Typer(name="vault", help="Manage encrypted credentials")
_vault: Vault | None = None


def _get_vault() -> Vault:
    global _vault
    if _vault is None:
        _vault = Vault()
    return _vault


@vault_app.command()
def set(service: str, username: str = typer.Option(..., "-u", "--username", prompt=True)):
    password = getpass("Password: ")
    _get_vault().set_password(service, username, password)
    typer.echo(f"Credential saved for {service}/{username}")


@vault_app.command()
def get(service: str, username: str = typer.Option(..., "-u", "--username", prompt=True)):
    password = _get_vault().get_password(service, username)
    if password is None:
        typer.echo(f"No credential found for {service}/{username}", err=True)
        raise typer.Exit(code=1)
    typer.echo(f"Username: {username}")
    typer.echo(f"Password: {password}")


@vault_app.command()
def delete(service: str):
    _get_vault().delete_password(service)
    typer.echo(f"All credentials deleted for {service}")


@vault_app.command()
def list():
    services = _get_vault().list_services()
    if not services:
        typer.echo("No credentials stored.")
        return
    for svc in services:
        creds = _get_vault().list_credentials(svc)
        usernames = ", ".join(c["username"] for c in creds)
        typer.echo(f"{svc}: {usernames}")


def run(task_name: str):
    from src.infrastructure.task_runner import TaskRunner
    typer.echo(f"Running task: {task_name}")
    runner = TaskRunner()
    asyncio.run(runner.run(task_name))
    typer.echo(f"Task finished: {runner.status.value}")


def logs(level: str = "info", since: str = "", task: str = "", json: bool = False):
    import json as json_mod

    log_file = Path("logs") / "senior-rpa.jsonl"
    if not log_file.exists():
        typer.echo("No log file found.", err=True)
        raise typer.Exit(code=1)

    level_map = {"debug": 10, "info": 20, "warning": 30, "error": 40}
    min_level = level_map.get(level, 20)

    with log_file.open(encoding="utf-8") as f:
        lines = f.readlines()

    tail = lines[-200:]
    for line in tail:
        try:
            entry = json_mod.loads(line)
        except json_mod.JSONDecodeError:
            continue
        lvl = entry.get("level", 0)
        if isinstance(lvl, str):
            lvl = level_map.get(lvl, 20)
        if lvl < min_level:
            continue
        if task and entry.get("task") != task:
            continue
        if json:
            typer.echo(line.rstrip())
        else:
            ts = entry.get("timestamp", "")[11:19] if entry.get("timestamp") else ""
            ev = entry.get("event", "")
            lv = entry.get("level", "?").upper() if isinstance(entry.get("level"), str) else "?"
            typer.echo(f"{ts} [{lv}] {ev}")


def shutdown():
    import httpx

    from src.infrastructure.single_instance import read_port
    port = read_port()
    if port is None:
        typer.echo("No running instance found.", err=True)
        raise typer.Exit(code=1)
    try:
        resp = httpx.post(f"http://127.0.0.1:{port}/api/shutdown", timeout=5)
        typer.echo(f"Server shut down: {resp.json()['status']}")
    except httpx.ConnectError:
        typer.echo("No running instance found.", err=True)
        raise typer.Exit(code=1)
