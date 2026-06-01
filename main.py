import typer

from src.infrastructure.logger import configure_logger
from src.interfaces.cli.cli import vault_app

app = typer.Typer(no_args_is_help=True)
app.add_typer(vault_app)
configure_logger()


@app.command()
def web(port: int = 8080, browser: bool = True, dev: bool = False):
    from src.interfaces.web.server import run_server

    run_server(port=port, open_browser=browser, dev=dev)


@app.command()
def run(task_name: str):
    from src.interfaces.cli.cli import run as run_cli

    run_cli(task_name)


@app.command()
def logs(level: str = "info", since: str = "", task: str = "", json: bool = False):
    from src.interfaces.cli.cli import logs as logs_cmd

    logs_cmd(level, since, task, json)


@app.command()
def shutdown():
    from src.interfaces.cli.cli import shutdown as shutdown_cmd

    shutdown_cmd()


if __name__ == "__main__":
    app()
