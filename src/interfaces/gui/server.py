import threading

import uvicorn
import webview

from src.config.settings import ASSETS_DIR
from src.infrastructure.logger import configure_logger, get_logger
from src.infrastructure.single_instance import focus_existing_instance, is_first_instance, save_port
from src.interfaces.web.server import _build_app, _uvicorn_log_config, find_free_port

log = get_logger("TerminalServerRPA.gui")


def run_server(port: int = 8080, dev: bool = False) -> None:
    if not is_first_instance():
        log.info("instance.duplicate", action="focus_existing")
        if focus_existing_instance():
            return
        log.warning("instance.focus_failed", action="start_anyway")

    configure_logger()
    actual_port = find_free_port(start=port)
    save_port(actual_port)

    if dev:
        import src.config.settings as _settings

        _settings.DEV_MODE = True

    app = _build_app()
    url = f"http://127.0.0.1:{actual_port}"

    config = uvicorn.Config(app, host="127.0.0.1", port=actual_port, log_config=_uvicorn_log_config(), access_log=False)
    server = uvicorn.Server(config)
    app.state.server = server

    threading.Thread(target=server.run, daemon=True).start()

    icon = str(ASSETS_DIR / "icon.ico")
    webview.create_window("Terminal Server RPA", url, width=1280, height=800, min_size=(900, 600), maximized=True)
    webview.start(icon=icon)
