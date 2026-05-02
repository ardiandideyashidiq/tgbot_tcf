# SweepAgent

Retroactively applies all active federation bans across every affiliated group.

Run this after issuing a new ban (to catch members already inside groups)
or as a scheduled maintenance sweep.

## Class

`tcbot.agents.sweep.SweepAgent(bot, *, concurrency=4, delay=0.05)`

| Parameter     | Default | Description                                           |
|---------------|---------|-------------------------------------------------------|
| `concurrency` | `4`     | Max groups processed in parallel                      |
| `delay`       | `0.05`  | Seconds between individual ban calls within a group   |

## Methods

### `sweep_group(chat_id) -> SweepResult`

Scans a single group and bans all members who appear in the active
federation ban list.

### `sweep_all() -> list[SweepResult]`

Runs `sweep_group()` across all affiliated groups with bounded concurrency.
Returns a list of `SweepResult` objects.

### `format_summary(results) -> str`

Returns a concise summary suitable for bot replies.

## SweepResult

```python
@dataclass
class SweepResult:
    chat_id: int
    banned:  int = 0
    errors:  int = 0
```

## Usage

```python
from tcbot.agents.sweep import SweepAgent

agent   = SweepAgent(bot)
results = await agent.sweep_all()
summary = agent.format_summary(results)
await msg.reply_text(summary)
```
