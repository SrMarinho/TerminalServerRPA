import asyncio
import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

import structlog
import structlog.processors
from structlog.processors import JSONRenderer, TimeStamper

LOG_DIR = Path("logs")
LOG_FILE = LOG_DIR / "senior-rpa.jsonl"

LOG_DIR.mkdir(parents=True, exist_ok=True)

_ws_queue: asyncio.Queue | None = None
_configured = False

def set_ws_queue(queue: asyncio.Queue):
    global _ws_queue
    _ws_queue = queue

def _ws_processor(logger, method_name, event_dict):
    if _ws_queue is not None:
        _ws_queue.put_nowait(event_dict)
    return event_dict

def configure_logger(level=logging.INFO):
    global _configured
    if _configured:
        return
    _configured = True
    timestamper = TimeStamper(fmt="iso", utc=True)

    shared_processors = [
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        timestamper,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
    ]

    file_handler = RotatingFileHandler(
        LOG_FILE, maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8"
    )
    file_handler.setLevel(level)
    file_fmt = structlog.stdlib.ProcessorFormatter(
        processors=[
            timestamper,
            structlog.stdlib.add_log_level,
            structlog.processors.UnicodeDecoder(),
            _ws_processor,
            JSONRenderer(),
        ],
        foreign_pre_chain=shared_processors,
    )
    file_handler.setFormatter(file_fmt)

    root_logger = logging.getLogger()
    root_logger.addHandler(file_handler)

    if sys.stderr is not None:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(level)
        console_fmt = structlog.stdlib.ProcessorFormatter(
            processors=[
                timestamper,
                structlog.stdlib.add_log_level,
                structlog.dev.ConsoleRenderer(),
            ],
            foreign_pre_chain=shared_processors,
        )
        console_handler.setFormatter(console_fmt)
        root_logger.addHandler(console_handler)

    root_logger.setLevel(level)

    for name in ("uvicorn", "uvicorn.access", "uvicorn.error"):
        logging.getLogger(name).handlers.clear()
        logging.getLogger(name).propagate = False

    structlog.configure(
        processors=[
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            timestamper,
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

def get_logger(name: str):
    return structlog.get_logger(name)
