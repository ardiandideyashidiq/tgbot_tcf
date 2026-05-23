# © Copyright 2024 - 2026 Transsion Core
# © Copyright 2024 - 2026 Dizzy
# © Copyright 2026 Aveum Apps

"""
Logging setup for the TCF bot.

Provides:
    - BotLogFormatter      - human-readable console format with ANSI colors
    - TelegramErrorHandler - ships every ERROR/CRITICAL log record to LOG_ERRORS
                             automatically via the running asyncio event loop
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

from tcbot import cfg


# ────────────────────── Console Log Formatter ───────────────────── #
# * Custom log formatter with ANSI color-coded output
# * Short module name only (last segment), no full dotted path
# * All timestamps in UTC for consistency across timezones

class BotLogFormatter(logging.Formatter):
    """
    Custom log formatter for console output with ANSI color badges
    * Output format: HH:MM DD/MM/YY [LEVEL] module:line → message
    * Level badges: color-coded via ANSI escape codes
    * Module name: last segment only (e.g. ban_flow, not tcbot.modules.helper.workflows.ban_flow)
    * Timestamps in UTC
    """

    _RESET  = "\033[0m"
    _BADGES = {
        logging.DEBUG:    "\033[1;37;100m DEBUG \033[0m",
        logging.INFO:     "\033[1;30;42m INFO  \033[0m",
        logging.WARNING:  "\033[1;30;43m WARN  \033[0m",
        logging.ERROR:    "\033[1;37;41m ERROR \033[0m",
        logging.CRITICAL: "\033[1;37;45m CRIT  \033[0m",
    }
    _TIME   = "\033[38;5;242m"
    _DATE   = "\033[38;5;238m"
    _MODULE = "\033[38;5;75m"
    _LINE   = "\033[38;5;242m"
    _ARROW  = "\033[38;5;242m"

    def __init__(self, project_name: str) -> None:
        super().__init__()
        self.project_name = project_name

    def format(self, record: logging.LogRecord) -> str:
        now    = datetime.now(timezone.utc)
        badge  = self._BADGES.get(record.levelno, " ??? ")
        module = record.name.split(".")[-1]
        return (
            f"{self._TIME}{now.strftime('%H:%M')}{self._RESET} "
            f"{self._DATE}{now.strftime('%d/%m/%y')}{self._RESET} "
            f"{badge} "
            f"{self._MODULE}{module}{self._RESET}"
            f"{self._LINE}:{record.lineno}{self._RESET}"
            f"{self._ARROW} → {self._RESET}"
            f"{record.getMessage()}"
        )


# ─────────────────── Telegram Error Log Handler ─────────────────── #
# * Sends ERROR/CRITICAL logs to the configured LOG_ERRORS channel
# * Zero blocking — schedules coroutine on the running asyncio event loop
# * Suppression list prevents infinite loops and network noise

_SUPPRESS_PREFIXES: tuple[str, ...] = (
    "tcbot.utils.error_reporter",
    "httpcore",
    "httpx._client",
)


class TelegramErrorHandler(logging.Handler):
    """
    Async logging handler that ships errors to Telegram
    * Intercepts every ERROR/CRITICAL log record across the entire codebase
    * Schedules coroutine on running event loop — zero blocking, zero extra code
    * Skips known noise sources to prevent spam in the logs channel
    * Avoids infinite loops by suppressing its own logger's errors
    """

    def __init__(self) -> None:
        super().__init__(logging.ERROR)

    def emit(self, record: logging.LogRecord) -> None:
        if any(record.name.startswith(p) for p in _SUPPRESS_PREFIXES):
            return
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return
        from tcbot.utils import error_reporter
        loop.create_task(error_reporter.report_record(record))


# ─────────────────────── Logging Setup Entry ────────────────────── #
# * Called once at bot startup — initializes all handlers and log levels

def setup(level: int = logging.INFO) -> None:
    """
    Initialize and configure the bot's logging system
    * Attaches BotLogFormatter to console handler
    * Attaches TelegramErrorHandler for ERROR/CRITICAL shipping
    * Suppresses third-party library noise on console
    * Must be called once before any logging occurs
    """
    con_handler = logging.StreamHandler()
    con_handler.setFormatter(BotLogFormatter(cfg.community_name))

    root = logging.getLogger()
    root.setLevel(level)
    root.addHandler(con_handler)
    root.addHandler(TelegramErrorHandler())

    for lib in ("httpx", "telegram", "motor", "pymongo"):
        logging.getLogger(lib).setLevel(logging.WARNING)