# GroupHealthAgent

Detects stale or migrated affiliated groups and keeps the database clean.

## Class

`tcbot.agents.group_health.GroupHealthAgent(bot: Bot)`

## Methods

### `run(auto_remove=True) -> dict[str, list[int]]`

Iterates all affiliated groups and probes each one via `bot.get_chat()`.
Returns a report dict with three keys:

```python
{
    "healthy":  [chat_ids...],   # bot is present and group is reachable
    "stale":    [chat_ids...],   # bot removed or group deleted (deactivated if auto_remove=True)
    "migrated": [chat_ids...],   # group migrated to a new chat_id (record updated)
}
```

### `summary() -> str`

Runs `run(auto_remove=False)` and returns a human-readable summary string
suitable for bot replies or the log channel.

## Usage

```python
from tcbot.agents import GroupHealthAgent

agent  = GroupHealthAgent(bot)
report = await agent.run()
print("Stale groups:", report["stale"])

# Or just get a formatted summary
text = await agent.summary()
await msg.reply_text(text)
```
