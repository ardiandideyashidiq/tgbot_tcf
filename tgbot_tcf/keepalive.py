import logging
import os
import threading

from flask import Flask

logger = logging.getLogger(__name__)

_app = Flask(__name__)


@_app.route("/")
def index() -> str:
    return "OK"


_PORT = int(os.environ.get("KEEPALIVE_PORT", "8000"))


def _run() -> None:
    _app.run(host="0.0.0.0", port=_PORT, debug=False, use_reloader=False)


def start_keepalive() -> None:
    t = threading.Thread(target=_run, name="keepalive", daemon=True)
    t.start()
    logger.info("Keep-alive server started on 0.0.0.0:%d", _PORT)
