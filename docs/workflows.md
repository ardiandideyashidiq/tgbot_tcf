# Conversation Flows — TCF Bot

This document describes every `ConversationHandler` flow in the project — state graphs, entry points, exit conditions, and implementation conventions.  
For architecture context, see [docs/architecture.md](architecture.md).  
For per-module details, see [docs/modules.md](modules.md).

---

## Key Rule: No `*_conv.py` Files

Every `ConversationHandler` is built inside a `*_flow.py` file via a factory function. Module files only define the entry point and call the factory:

```python
# kicking.py
from tcbot.modules.helper.workflows.kicking_flow import kick_conversation

__handlers__ = [kick_conversation(cmd_kick_entry)]
```

Never create `*_conv.py` files. Never duplicate state handlers across modules.

---

## Shared States (`reason_flow.py`)

```python
WAITING_REASON: int = 0
WAITING_PROOF:  int = 1
```

`WAITING_REASON` and `WAITING_PROOF` are the shared state constants used by kick, mute, and warn. They are defined once in `reason_flow.py` and imported wherever needed.

---

## Central Factory: `reason_flow.build_modaction_conv()`

Kick, mute, and warn all share the same ConversationHandler structure. `build_modaction_conv()` is the single factory that produces it:

```
Entry (command message)
  │
  ├── reason is inline → prompt for proof → WAITING_PROOF
  └── no reason → prompt for reason → WAITING_REASON
        │
        ├── user sends text reason → prompt for proof → WAITING_PROOF
        └── user taps "Skip reason" → prompt for proof → WAITING_PROOF
              │
              ├── user sends photo/video proof → execute action → END
              ├── user taps "Skip proof" → execute action → END
              └── user taps "Cancel" → abort → END
```

The factory accepts:
- `action: str` — `"kick"`, `"mute"`, or `"warn"` — used for labeling prompts and callbacks
- `entry_fn` — the async function that handles the command message and returns `WAITING_REASON | WAITING_PROOF | END`
- `executor` — async adapter `_exec_*(update, ctx, target_id, fname, reason, proof_desc, admin_id, admin_fname)` that performs the actual action
- `entry_filter` — the `MessageFilter` or combined filter for the command

### Keyboard and Prompt Helpers

```python
from tcbot.modules.helper.workflows.reason_flow import (
    WAITING_REASON, WAITING_PROOF,
    reason_kb, proof_kb,
    reason_prompt, reason_noted_prompt,
    parse_inline_reason, record_proof,
)

# reason step prompt
reason_prompt(target_mention, action, extra_info="")

# "reason noted, add proof?" prompt (when reason was inline)
reason_noted_prompt(action, inline_reason, target_mention, extra_info="")

# keyboard for reason step: [Skip reason] [Cancel]
reason_kb(action)

# keyboard for proof step: [Skip proof] [Cancel]
proof_kb(action)

# extract inline reason from command args
inline_reason = parse_inline_reason(remaining_args, has_explicit_target=False)

# store proof media in ctx.user_data
record_proof(ctx, action, message)
```

---

## Kick Flow (`kicking_flow.kick_conversation`)

**File:** `tcbot/modules/helper/workflows/kicking_flow.py`  
**Factory:** `kick_conversation(entry_fn)` — delegates to `reason_flow.build_modaction_conv()`

**State graph:**

```
WAITING_REASON (if no inline reason in command)
  ├── text message → record reason → WAITING_PROOF
  └── "Skip reason" button → WAITING_PROOF

WAITING_PROOF
  ├── photo/video → record proof → execute_kick() → END
  ├── "Skip proof" button → execute_kick() → END
  └── "Cancel" button → abort, delete prompt → END
```

**Executor:** `execute_kick(bot, groups, target_id, target_fname, reason, proof_desc, executor_id, executor_fname)`

- Calls `fan_out([bot.ban_chat_member(g["chat_id"], target_id) for g in groups])`
- Immediately unbans after ban to produce a kick (not a permanent ban)
- Logs to the log channel
- Returns `(kicked_count, error_count)`

**Triggers:** `/tckick`, `/tck`, and any configured prefix equivalent.

---

## Mute Flow (`muting_flow.mute_conversation`)

**File:** `tcbot/modules/helper/workflows/muting_flow.py`  
**Factory:** `mute_conversation(entry_fn)` — delegates to `reason_flow.build_modaction_conv()`

**Additional features over kick:**

- Optional duration token parsed **before** entering the ConversationHandler (`parse_duration()`)
- Duration token regex: `_DURATION_RE` matches `3d`, `1w`, `2h`, `30m`, `1mo`, `2ye`, `45s`
- `fmt_duration(secs | None)` formats duration for display (`"7 days"`, `"permanent"`)
- Permanent mute when duration is `None` (no duration token provided)
- Duration is stored in `ctx.user_data["mute_duration"]` and passed to the executor

**Duration tokens:**

| Token | Unit | Example |
|---|---|---|
| `s` | seconds | `45s` |
| `m` | minutes | `30m` |
| `h` | hours | `2h` |
| `d` | days | `7d` |
| `w` | weeks | `1w` |
| `mo` | months | `3mo` |
| `ye` | years | `1ye` |

**Unmute** (`/tcunmute`, `/tcunm`, `/tcum`) is a direct `MessageHandler` — not a ConversationHandler:

```python
cmd_unmute → extract_target → execute_unmute(update, ctx, target_id, fname)
```

**Triggers:** `/tcmute`, `/tcm`, and configured prefix equivalents.

---

## Warn Flow (`warning_flow.warn_conversation`)

**File:** `tcbot/modules/helper/workflows/warning_flow.py`  
**Factory:** `warn_conversation(entry_fn)` — delegates to `reason_flow.build_modaction_conv()`

**Warn state graph:** Same as kick/mute (WAITING_REASON → WAITING_PROOF → END).

**Additional direct commands:**

| Command | Handler | DB operation |
|---|---|---|
| `/tcunwarn` | `cmd_unwarn` | `warns_db.remove_warn()` |
| `/tcwarnlist` | `cmd_warnlist` | `warns_db.get_warns()` |
| `/tcresetwarn` | `cmd_resetwarns` | `warns_db.reset_warns()` |

**Triggers:** `/tcwarn`, `/tcw`, and configured prefix equivalents.

---

## Ban Flow (`ban_flow.ban_conversation`)

**File:** `tcbot/modules/helper/workflows/ban_flow.py`  
**Factory:** `ban_conversation(entry_fn)` — **does not** use `reason_flow` (different state graph)

**Key difference from kick/mute/warn:** Ban requires a reason in the command itself (no reason step in the conversation), but supports multi-media album proof collection.

**State graph:**

```
Entry (command message with inline reason)
  │
  ├── permission check passes → prompt for proof → WAITING_PROOF
  └── permission check fails → reply error → END

WAITING_PROOF
  ├── photo/video → buffer into album cache → (debounce timer)
  │     album complete → record all media → prompt "Done?" → WAITING_PROOF
  ├── "Done" button (after at least one photo/video) → _execute_ban() → END
  ├── "Skip" button → _execute_ban() with no proof → END
  └── "Cancel" button → abort → END
```

**Album handling:**

Multiple photos/videos from the same album (forwarded or sent as a group) are buffered using `cfg.album_debounce` (default 2 s). When the debounce timer fires, all buffered media is treated as a single proof entry.

**Executor:** `_execute_ban(update, ctx)`

1. Checks if an active ban already exists for the user (`bans_db.get_active_ban()`)
2. If yes: updates the existing ban record (`bans_db.update_ban()`)
3. If no: creates a new ban record (`bans_db.create_ban()`)
4. Uploads proof media to the proof channel (`proof_flow.upload_proof()`)
5. Applies the ban to all connected groups via `fan_out([bot.ban_chat_member(...)])`
6. Posts a ban log to the log channel with `ban_log_new` or `ban_log_update` keyboard

**Triggers:** `/tcban`, `/tcb`, and configured prefix equivalents.

---

## Appeal Flow (`appeal_flow.build_handler`)

**File:** `tcbot/modules/helper/workflows/appeal_flow.py`  
**Factory:** `build_handler()` — standalone, completely independent of `reason_flow`

**Entry:** `/start appeal_<ban_id>` deep link in bot PM

**State graph:**

```
/start appeal_<ban_id>   (command message in PM)
  │
  ├── user has no active ban → reply "no active ban" → END
  ├── ban_id does not match user → reply "not your appeal" → END
  └── valid → prompt for appeal text → WAITING_APPEAL

WAITING_APPEAL
  ├── text starting with #appeal → validate format → WAITING_CONFIRM
  │     missing sections → reply hint → stay WAITING_APPEAL
  └── "Cancel" button → abort → END

WAITING_CONFIRM
  ├── "Submit" button → forward appeal to appeal channel + post review card → END
  └── "Edit" button → return to WAITING_APPEAL
  └── "Cancel" button → abort → END
```

**Required appeal text format:**

```
#appeal
Log link: https://t.me/...
Clarification: explanation of the situation
Agreement: commitment to follow community rules
```

All three sections are required. The bot validates each section is present before moving to the confirm step.

**Review card:**

After submission, the bot posts a review card to `APPEAL_DISCUSSION_TOPIC` inside `MAIN_GROUP`:

```
[Appeal] @username | ban_id
Submitted: DD MMM YYYY HH:MM UTC

#appeal
Log link: https://...
Clarification: ...
Agreement: ...

[Approve] [Reject]
```

**Reviewer lock window:**

The admin who issued the original ban has a 12-hour priority window. During this window, only the original banning admin and the Founder can approve or reject. After 12 hours, any admin or above can act.

`reviewer_locked_out(review_timestamp, ban_admin_id, reviewer_id)` is the pure function that implements this check (in `appeals.py`).

**`on_appeal_decision(update, ctx)`:**

- Registered as a `CallbackQueryHandler` with pattern `^appeal_(approve|reject)_\S+$`
- On approve: calls `execute_unban()` across all groups, notifies the user by DM
- On reject: marks ban as reviewed, notifies the user by DM

---

## Promote Flow (no ConversationHandler)

**File:** `tcbot/modules/helper/workflows/promote_flow.py`  
**No ConversationHandler.** Promotion is a single command + optional inline button confirmation.

**Direct promote (role provided in command):**

```
/tcpromote @user developer
  → _execute_promote(...)
  → success message or error
```

**Button menu (no role in command):**

```
/tcpromote @user
  → show promote_role_kb(target_id, available_roles)
  → user taps a role button
  → on_promote_role_select callback
  → _execute_promote(...)
  → edit the menu message to show result
```

**Admin-to-Admin promotion path:**

When an Admin tries to promote someone to Admin rank:

```
Admin runs /tcpromote @user admin
  → _execute_promote() detects executor is Admin requesting Admin promotion
  → creates a promotion request in queues_db
  → sends approval request card to Founder in PM
  → replies "Request submitted" to the Admin

Founder sees card [Approve] [Reject]
  → on_promo_decision callback
  → approve: add_admin() in admins_db
  → reject: update request status, notify requester
```

---

## Demote Flow (no ConversationHandler)

**File:** `tcbot/modules/admins.py`  
**No ConversationHandler.** Demote is a single command + confirm button.

```
/tcdemote @user
  → validate executor rank > target rank
  → show demote_confirm_kb(target_id)

[Confirm] button (on_demote_confirm)
  → remove role or admin
  → log + notify target
  → edit message to show result

[Cancel] button (on_demote_cancel)
  → edit message to show "cancelled"
```

---

## Unban Flow (no ConversationHandler)

**File:** `tcbot/modules/helper/workflows/unban_flow.py`  
**No ConversationHandler.** Unban is a single direct command.

```
/tcunban <user_id|ban_id>
  → resolve target (by user_id or ban_id)
  → validate executor rank
  → execute_unban(update, ctx, target_id, fname)
    → bans_db.deactivate_ban(ban_id)
    → fan_out([bot.unban_chat_member(...) for g in active_groups])
    → log to log channel
    → reply summary
```

---

## Connect/Disconnect Flow (`connected_flow.py`)

Group federation join and approval flow.

```
Group owner: /connect
  → bot is in the group (verified via bot.get_chat_member)
  → add_pending(chat_id, title, owner_id, message_id)
  → post approval request to configured channel

Admin sees [Connect] [Reject] card
  → on_connect_approve:
    → add_group(chat_id, title, added_by)
    → execute_sweep(bot, chat_id)  — ban all active federation bans
    → reply to owner's message in the group: "Connected"
  → on_connect_reject:
    → remove_pending(chat_id)
    → reply to owner's message: "Rejected"

Group owner: /disconnect
  → deactivate_group(chat_id)
  → reply: "Disconnected"
```

---

## Timeout Handling

All ConversationHandlers define a `conversation_timeout` callback. When the timeout fires:

1. The bot replies (or edits the prompt) with a "timed out" message
2. Any buffered data in `ctx.user_data` is cleaned up
3. The handler returns `ConversationHandler.END`

Timeout durations:
- Proof flows (ban, kick, mute, warn): `cfg.proof_timeout` seconds
- Appeal flow: `cfg.appeal_timeout` seconds

Never hardcode timeout values. Always reference `cfg`.

---

## Related Documentation

- [Architecture](architecture.md)
- [Modules and service boundaries](modules.md)
- [Development workflow and onboarding](development.md)
- [AI agent instructions](../agents/CLAUDE.md)
