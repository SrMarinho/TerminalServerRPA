import typer
from getpass import getpass
from src.password_vault.vault import Vault

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
