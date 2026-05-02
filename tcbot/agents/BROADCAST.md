# BroadcastAgent

Sends messages to all affiliated groups with configurable rate limiting
and per-group retry logic.

A more controllable alternative to the inline broadcast loop in
`broadcasting.py` — useful when you need progress tracking or fine-grained
retry behaviour.

## Class

`tcbot.agents.broadcast_agent.BroadcastAgent(bot, *, delay=0.05, retries=2)`

| Parameter | Default | Description                                    |
|-----------|---------|------------------------------------------------|
| `delay`   | `0.05`  | Seconds between each group                     |
| `retries` | `2`     | Retry attempts per group on transient failure  |

## Methods

### `send_text(text, **kwargs) -> BroadcastResult`

Sends a plain text message to all affiliated groups. Supports all keyword
arguments accepted by `bot.send_message()` (e.g. `parse_mode`, `reply_markup`).

### `forward_message(message) -> BroadcastResult`

Forwards an existing `telegram.Message` object to all affiliated groups.

### `format_summary(result) -> str`

Returns a concise summary string suitable for bot replies.

## BroadcastResult

```python
@dataclass
class BroadcastResult:
    total:      int       = 0
    success:    int       = 0
    failed:     int       = 0
    failed_ids: list[int] = field(default_factory=list)
```

## Usage

```python
from tcbot.agents.broadcast_agent import BroadcastAgent

agent  = BroadcastAgent(bot)
result = await agent.send_text(
    "Important update for all TCF groups.",
    parse_mode="HTML",
)
await msg.reply_text(agent.format_summary(result))
```
