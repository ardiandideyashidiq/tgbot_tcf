# © Copyright 2024 - 2026 Transsion Core
# © Copyright 2024 - 2026 Dizzy
# © Copyright 2026 Aveum Apps
"""Centralized config loader – parses all env vars from config.env once."""
from __future__ import annotations

import os
from dataclasses import dataclass, field


def _chat(val: str) -> tuple[int, int | None]:
    """Parse 'chat_id' or 'chat_id/thread_id' into (chat_id, thread_id)."""
    if "/" in val:
        cid, tid = val.split("/", 1)
        return int(cid.strip()), int(tid.strip())
    return int(val.strip()), None


def _int(val: str, default: int) -> int:
    try:
        return int(val)
    except (TypeError, ValueError):
        return default


def _port(val: str, default: int) -> int:
    if not val or val == "auto":
        return default
    return _int(val, default)


@dataclass(frozen=True)
class Config:
    bot_token: str
    owner_id: int
    mongodb_uri: str
    db_name: str
    community_name: str

    ## chat IDs
    main_group: int
    main_channel: int
    exec_group: int
    initial_owner_id: int

    ## topic-aware channel IDs (chat_id, thread_id | None)
    proofs: tuple[int, int | None]
    logs: tuple[int, int | None]
    logs_errors: tuple[int, int | None]
    appeals: tuple[int, int | None]

    ## timeouts
    proof_timeout: int
    appeal_timeout: int
    album_debounce: float

    ## keep-alive port
    port: int


def load() -> Config:
    from dotenv import load_dotenv
    load_dotenv("config.env")
    load_dotenv(".env")

    def _g(key: str, default: str = "") -> str:
        return os.getenv(key, default).strip().strip('"').strip("'")

    proofs_raw = _g("PROOFS") or f"{_g('MAIN_GROUP')}/67"
    logs_raw = _g("LOGS") or "-1003941141635"
    logs_err_raw = _g("LOGS_ERRORS") or logs_raw
    appeals_raw = _g("APPEALS") or f"{_g('MAIN_GROUP')}/12"

    return Config(
        bot_token=_g("BOT_TOKEN"),
        owner_id=_int(_g("OWNER_ID"), 7146954165),
        mongodb_uri=_g("MONGODB_URI"),
        db_name=_g("DB_NAME") or "tcf_bot",
        community_name=_g("COMMUNITY_NAME") or "TCF",
        main_group=_int(_g("MAIN_GROUP"), -1003872207988),
        main_channel=_int(_g("MAIN_CHANNEL"), -1003852970764),
        exec_group=_int(_g("EXEC_GROUP") or "-1002333013065", -1002333013065),
        initial_owner_id=_int(_g("OWNER_ID"), 7146954165),
        proofs=_chat(proofs_raw),
        logs=_chat(logs_raw),
        logs_errors=_chat(logs_err_raw),
        appeals=_chat(appeals_raw),
        proof_timeout=_int(_g("PROOF_TIMEOUT_SECONDS"), 100),
        appeal_timeout=_int(_g("APPEAL_TIMEOUT_SECONDS"), 600),
        album_debounce=float(_g("ALBUM_DEBOUNCE_SECONDS") or "2"),
        port=_port(_g("PORT"), 5000),
    )


## Singleton – loaded once at startup
cfg: Config = load()
