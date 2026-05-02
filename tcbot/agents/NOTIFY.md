# NotifyAgent

Routes system notifications to the owner, all staff, or the configured
log channel. Use this for events that cannot be surfaced as inline bot
replies — e.g. scheduled task results, failed operations, audit alerts.

## Class

`tcbot.agents.notify_agent.NotifyAgent(bot: Bot)`

## Methods

### `notify_owner(text, **kwargs) -> bool`

Sends `text` to the current federation owner. Returns `True` on success.
Logs a warning and returns `False` if no owner is set or delivery fails.

### `notify_all_staff(text, **kwargs) -> tuple[int, int]`

Sends `text` to every admin and the owner. Returns `(success_count, fail_count)`.

### `log_channel(text, **kwargs) -> bool`

Posts `text` to the configured log channel (`cfg.logs`), respecting the
thread ID if one is set. Returns `True` on success.

## Usage

```python
from tcbot.agents.notify_agent import NotifyAgent

notifier = NotifyAgent(bot)

# Alert the owner only
await notifier.notify_owner("Sweep complete — 5 users banned across 12 groups.")

# Post to the log channel
await notifier.log_channel(
    "<b>Scheduled health check complete.</b>",
    parse_mode="HTML",
)

# Alert all staff
success, fail = await notifier.notify_all_staff(
    "Maintenance window starting in 10 minutes."
)
```
