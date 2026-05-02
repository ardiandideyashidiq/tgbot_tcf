# © Copyright 2024 - 2026 Transsion Core
# © Copyright 2024 - 2026 Dizzy
# © Copyright 2026 Aveum Apps
"""MongoDB connection manager – single client shared across the app."""
from __future__ import annotations

import logging

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

log = logging.getLogger(__name__)

_db: AsyncIOMotorDatabase | None = None


def db() -> AsyncIOMotorDatabase:
    if _db is None:
        raise RuntimeError("DB not initialised – call connect() first.")
    return _db


async def connect() -> None:
    global _db
    from tcbot import cfg

    client = AsyncIOMotorClient(cfg.mongodb_uri, serverSelectionTimeoutMS=10_000)
    _db = client[cfg.db_name]
    await _db.command("ping")
    log.info("MongoDB connected → %s", cfg.db_name)


## Collection accessors
def col(name: str):
    return db()[name]
