from motor.motor_asyncio import AsyncIOMotorClient

from ..config import DB_NAME, MONGODB_URI

_client = AsyncIOMotorClient(MONGODB_URI)
db = _client[DB_NAME]

federated_groups = db["federated_groups"]
fed_owners = db["fed_owners"]
fed_admins = db["fed_admins"]
bans = db["bans"]


async def init_db() -> None:
    await federated_groups.create_index("chat_id", unique=True)
    await fed_owners.create_index("user_id", unique=True)
    await fed_admins.create_index("user_id", unique=True)
    await bans.create_index("ban_id", unique=True)
    await bans.create_index([("banned_user_id", 1), ("is_active", 1)])
