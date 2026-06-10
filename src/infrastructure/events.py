"""Process-wide event bus decoupling the infrastructure layer from its consumers.

Infrastructure (execution manager, task runner) calls `publish()` without knowing
who listens. The web layer registers `broadcast_event` as a subscriber at startup.
In CLI mode no subscriber is registered, so `publish()` is a clean no-op.
"""

from collections.abc import Callable

from src.infrastructure.logger import get_logger

_log = get_logger("TerminalServerRPA.events")
_subscribers: list[Callable[[dict], None]] = []


def subscribe(cb: Callable[[dict], None]) -> None:
    if cb not in _subscribers:
        _subscribers.append(cb)


def unsubscribe(cb: Callable[[dict], None]) -> None:
    if cb in _subscribers:
        _subscribers.remove(cb)


def publish(event: dict) -> None:
    for cb in list(_subscribers):
        try:
            cb(event)
        except Exception:
            _log.debug("event.publish_failed", event_type=event.get("type", "unknown"))
