# © Copyright 2024 - 2026 Transsion Core
# © Copyright 2024 - 2026 Dizzy
# © Copyright 2026 Aveum Apps
"""Entry point – initialise DB, register all module handlers, start polling."""
from __future__ import annotations

import importlib
import logging
import pkgutil
from pathlib import Path
from typing import Any

from telegram.ext import Application, ApplicationBuilder

import tcbot.modules as _mods_pkg
from tcbot.config import cfg
from tcbot.utils.logger import setup as setup_logging

log = logging.getLogger(__name__)


def _discover_handlers() -> list[Any]:
    """Auto-discover and collect all handlers from tcbot.modules.*"""
    handlers: list[Any] = []
    pkg_path = str(Path(_mods_pkg.__file__).parent)

    ## Load modules in a sensible order – start/greeting last to avoid filter conflicts
    PRIORITY_FIRST = ["connecting", "admins", "banning", "appealing"]
    PRIORITY_LAST = ["start", "greeting"]

    mods_found: dict[str, Any] = {}
    for _, mod_name, _ in pkgutil.iter_modules([pkg_path]):
        try:
            mod = importlib.import_module(f"tcbot.modules.{mod_name}")
            mods_found[mod_name] = mod
        except Exception as exc:
            log.error("Failed to import module tcbot.modules.%s: %s", mod_name, exc)

    ordered = (
        [n for n in PRIORITY_FIRST if n in mods_found]
        + [n for n in mods_found if n not in PRIORITY_FIRST and n not in PRIORITY_LAST]
        + [n for n in PRIORITY_LAST if n in mods_found]
    )

    for mod_name in ordered:
        mod = mods_found[mod_name]
        mod_handlers = getattr(mod, "__handlers__", [])
        if mod_handlers:
            handlers.extend(mod_handlers)
            log.debug("Loaded %d handler(s) from %s", len(mod_handlers), mod_name)

    return handlers


async def _post_init(app: Application) -> None:
    from tcbot.database.mongos import connect
    from tcbot.database.admins_db import ensure_initial_owner

    await connect()
    await ensure_initial_owner(cfg.initial_owner_id)
    log.info("Bot initialised. Owner: %d", cfg.initial_owner_id)


def main() -> None:
    setup_logging()
    log.info("Starting %s bot...", cfg.community_name)

    from tcbot.alive import start_keepalive
    start_keepalive()

    app: Application = (
        ApplicationBuilder()
        .token(cfg.bot_token)
        .post_init(_post_init)
        .build()
    )

    for handler in _discover_handlers():
        app.add_handler(handler)

    log.info("Handlers registered. Starting polling...")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
