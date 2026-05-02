# BanEnforcer

Enforces the federation ban list when members join affiliated groups.

## Class

`tcbot.agents.ban_enforcer.BanEnforcer(bot: Bot)`

## Methods

### `enforce_on_join(chat_id, user_id, user_fname) -> bool`

Checks whether `user_id` is federation-banned. If so, bans them from `chat_id`
and returns `True`. Returns `False` if the user is clean.

Use this from join-event handlers across all affiliated groups.

### `sweep_group(chat_id) -> tuple[int, int]`

Iterates the full active ban list and bans any current members found in it.
Returns `(banned_count, error_count)`. Individual errors do not abort the sweep.

### `sweep_all_groups() -> dict[int, tuple[int, int]]`

Runs `sweep_group()` across every affiliated group.
Returns a mapping of `chat_id → (banned, errors)`.

## Usage

```python
from tcbot.agents import BanEnforcer

enforcer = BanEnforcer(bot)
was_banned = await enforcer.enforce_on_join(chat_id, user.id, user.first_name)
if was_banned:
    # user was removed — notify the group if needed
    pass
```
