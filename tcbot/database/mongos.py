# © Copyright 2024 - 2026 Transsion Core
# © Copyright 2024 - 2026 Dizzy
# © Copyright 2026 Aveum Apps
"""MongoDB connection manager – single client shared across the app."""
from __future__ import annotations

import logging
import secrets
import string

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from tcbot import cfg

log = logging.getLogger(__name__)

_db: AsyncIOMotorDatabase | None = None

_ID_ALPHABET: str = string.ascii_lowercase + string.digits


def make_short_id(length: int = 10) -> str:
    """Generate a random URL-safe lowercase alphanumeric ID."""
    return "".join(secrets.choice(_ID_ALPHABET) for _ in range(length))


def db() -> AsyncIOMotorDatabase:
    if _db is None:
        raise RuntimeError("DB not initialised – call connect() first.")
    return _db


async def connect() -> None:
    global _db
    client = AsyncIOMotorClient(cfg.mongodb_uri, serverSelectionTimeoutMS=10_000)
    _db = client[cfg.db_name]
    await _db.command("ping")
    log.info("MongoDB connected → %s", cfg.db_name)


def col(name: str):
    return db()[name]
