# © Copyright 2024 - 2026 Transsion Core
# © Copyright 2024 - 2026 Dizzy
# © Copyright 2026 Aveum Apps
"""MongoDB connection and collection references."""
from __future__ import annotations

from typing import Any

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorCollection

from .. import DB_NAME, MONGODB_URI

_client = AsyncIOMotorClient(MONGODB_URI)
db = _client[DB_NAME]

# Typed collection handles to help static analysis (documents are dicts)
federated_groups: AsyncIOMotorCollection[dict[str, Any]] = db["federated_groups"]
tc_owners: AsyncIOMotorCollection[dict[str, Any]] = db["tc_owners"]
tc_admins: AsyncIOMotorCollection[dict[str, Any]] = db["tc_admins"]
bans: AsyncIOMotorCollection[dict[str, Any]] = db["bans"]
promotion_requests: AsyncIOMotorCollection[dict[str, Any]] = db["promotion_requests"]
pending_joins: AsyncIOMotorCollection[dict[str, Any]] = db["pending_joins"]
member_cache: AsyncIOMotorCollection[dict[str, Any]] = db["member_cache"]
kicks: AsyncIOMotorCollection[dict[str, Any]] = db["kicks"]
muted: AsyncIOMotorCollection[dict[str, Any]] = db["muted"]
warns: AsyncIOMotorCollection[dict[str, Any]] = db["warns"]


async def _drop_stale_index(
    col: Any, index_name: str
) -> None:
    """Drop a legacy index by name, ignoring errors when it does not exist."""
    import logging as _logging
    _log = _logging.getLogger(__name__)
    try:
        await col.drop_index(index_name)
        _log.info("Dropped stale index '%s' from '%s'", index_name, col.name)
    except Exception:
        pass


async def init_db() -> None:
    """Create indexes for all collections on startup.

    Also removes any stale single-field indexes that were created by earlier
    versions of the code and now conflict with the correct compound indexes.
    """
    # Remove legacy solo user_id index on member_cache that conflicts with
    # the correct compound (chat_id, user_id) index.
    await _drop_stale_index(member_cache, "user_id_1")

    await federated_groups.create_index("chat_id", unique=True)
    await tc_owners.create_index("user_id", unique=True)
    await tc_admins.create_index("user_id", unique=True)
    await bans.create_index("ban_id", unique=True)
    await bans.create_index([("banned_user_id", 1), ("is_active", 1)])
    await promotion_requests.create_index("request_id", unique=True)
    await promotion_requests.create_index([("target_id", 1), ("status", 1)])
    await pending_joins.create_index("chat_id", unique=True)
    await member_cache.create_index(
        [("chat_id", 1), ("user_id", 1)], unique=True
    )
    await kicks.create_index("kick_id", unique=True)
    await kicks.create_index([("kicked_user_id", 1), ("timestamp", -1)])
    await muted.create_index("mute_id", unique=True)
    await muted.create_index(
        [("muted_user_id", 1), ("chat_id", 1), ("is_active", 1)]
    )
    await warns.create_index("warn_id", unique=True)
    await warns.create_index(
        [("warned_user_id", 1), ("chat_id", 1), ("is_active", 1)]
    )
