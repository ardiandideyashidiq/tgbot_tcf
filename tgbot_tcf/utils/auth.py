from ..db import fed_admins, fed_owners


async def is_fed_owner(user_id: int) -> bool:
    return await fed_owners.find_one({"user_id": user_id}) is not None


async def is_fed_admin(user_id: int) -> bool:
    return await fed_admins.find_one({"user_id": user_id}) is not None


async def is_authorized(user_id: int) -> bool:
    if await is_fed_owner(user_id):
        return True
    return await is_fed_admin(user_id)


async def get_owner_id() -> int | None:
    doc = await fed_owners.find_one({})
    return doc["user_id"] if doc else None
