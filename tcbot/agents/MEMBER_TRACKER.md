# MemberTracker

Handles member join and leave events for affiliated groups — caching user info
and enforcing bans at the point of entry.

## Class

`tcbot.agents.member_tracker.MemberTracker(bot: Bot)`

## Methods

### `on_join(chat_id, user) -> bool`

Called when a member joins an affiliated group.

1. Caches `user_id`, `username`, `first_name`, and `last_name` in the users collection.
2. Checks the federation ban list.
3. If banned → bans the user from `chat_id` and returns `True`.
4. If clean → returns `False`.

### `on_leave(chat_id, user) -> None`

Called when a member leaves. Currently logs a debug entry — extend as needed
(e.g. update membership tracking, clear caches).

## Usage

```python
from tcbot.agents.member_tracker import MemberTracker

tracker = MemberTracker(bot)

# In a NEW_CHAT_MEMBERS handler:
for member in msg.new_chat_members:
    was_banned = await tracker.on_join(chat.id, member)
    if was_banned:
        await msg.reply_text(
            f"{member.first_name} is federation-banned and was removed."
        )
```
