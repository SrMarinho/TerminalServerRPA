import typer

from src.password_vault.logger import configure_logger

app = typer.Typer()
configure_logger()


@app.command()
def web(port: int = 8080, browser: bool = True):
    from src.password_vault.server import run_server
    run_server(port=port, open_browser=browser)


@app.command()
def vault():
    from src.password_vault.cli import vault_app
    vault_app()


@app.command()
def run(task_name: str):
    from src.password_vault.cli import run as run_cli
    run_cli(task_name)


@app.command()
def logs(level: str = "info", since: str = "", task: str = "", json: bool = False):
    from src.password_vault.cli import logs as logs_cmd
    logs_cmd(level, since, task, json)


if __name__ == "__main__":
    app()
