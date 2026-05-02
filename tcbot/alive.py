# © Copyright 2024 - 2026 Transsion Core
# © Copyright 2024 - 2026 Dizzy
# © Copyright 2026 Aveum Apps
"""Minimal Flask keep-alive server – daemon thread, health check only."""
from __future__ import annotations

import logging
import threading

from flask import Flask

log = logging.getLogger(__name__)
app = Flask(__name__)


@app.route("/")
def _health():
    return "OK"


def start_keepalive() -> None:
    from tcbot.config import cfg

    def _run():
        log.info("Keep-alive running on 0.0.0.0:%d", cfg.port)
        app.run(host="0.0.0.0", port=cfg.port, debug=False, use_reloader=False)

    threading.Thread(target=_run, daemon=True).start()
