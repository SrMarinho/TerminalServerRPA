"""Shared dependencies for the web routes: bearer auth + template rendering."""

import secrets
from pathlib import Path

from fastapi import Header, HTTPException
from jinja2 import Environment, FileSystemLoader, select_autoescape

from src.infrastructure.single_instance import get_or_create_token

TEMPLATES_DIR = Path(__file__).parent.parent / "templates"

_jinja_env = Environment(
    loader=FileSystemLoader(str(TEMPLATES_DIR)),
    autoescape=select_autoescape(["html"]),
)


def render_template(name: str, **context) -> str:
    return _jinja_env.get_template(name).render(**context)


def verify_token(authorization: str = Header(default="")):
    """Validate the Bearer token from the Authorization header.

    Header-only on REST: query strings leak into history/proxies/logs more
    easily. The WebSocket handshake still uses ?token= (browsers cannot set
    headers on WS connections). compare_digest avoids timing side-channels.
    """
    extracted = authorization.removeprefix("Bearer ")
    actual = get_or_create_token()
    if not extracted or not secrets.compare_digest(extracted, actual):
        raise HTTPException(401, "Unauthorized — invalid or missing API token")
