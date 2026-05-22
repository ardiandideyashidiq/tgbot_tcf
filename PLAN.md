# TCF Bot — Project Plan

This document describes the current state of the codebase and the planned path forward. Items are ordered by priority within each phase. Phase boundaries are approximate; work may overlap.

---

## Current State

The bot is functional and covers its core scope: federation-wide bans, appeals, role management, group moderation, and connected-group administration. The codebase is well-structured with a clear module boundary, consistent use of async/await, and a passing test suite (121 tests).

The immediate problems are not architectural — they are accumulated defects, silent failure points, missing safety nets, and gaps in test coverage that will become harder to address as the feature set grows.

---

## Phase 1 — Defect Resolution

These are concrete bugs or silent failures identified in the current code. None require design decisions; they are straightforward to fix.

### 1.1 Silent exception swallowing

Twelve locations across the codebase use bare `except ... pass` or `except Exception: pass` with no log line. When these branches are hit in production, failures are invisible.

| File | Location | Issue |
|---|---|---|
| `tcbot/database/mongos.py` | `connect()` | Swallows connection errors on index creation |
| `tcbot/modules/helper/workflows/appeal_flow.py` | `_update_or_send_appeal_log()` | Second-attempt send failure is lost |
| `tcbot/modules/helper/workflows/connected_flow.py` | Group monitor | Silently discards errors during pending-join cleanup |
| `tcbot/modules/helper/decorators.py` | Rate-limit reply (×3) | Slow-down notice failures are lost |
| `tcbot/modules/helper/extraction.py` | `resolve_identity()` (×3) | `get_chat` failures return partial info without any trace |
| `tcbot/modules/admins.py` | Button cleanup (×2) | Edit-markup failures after promote/demote are lost |
| `tcbot/utils/prefixes.py` | `ast.literal_eval` fallback | Malformed `PREFIXES` env var is silently ignored |
| `tcbot/__main__.py` | Asyncio error reporter | Reporting failure itself is swallowed |

**Fix:** Replace each `pass` with at minimum `log.debug(...)`. Where the error is meaningful to an admin, use `log.warning(...)`.

---

### 1.2 TTLCache thundering herd

`tcbot/database/cache.py` `get_or_fetch()` has a race condition: if N coroutines request the same missing key at the same time, all N will call the database before any of them has stored the result.

```python
# current — no guard
async def get_or_fetch(self, key, fetch):
    if (val := self.get(key)) is not None:
        return val
    val = await fetch()  # all N coroutines reach here
    self.put(key, val)
    return val
```

**Fix:** Add a per-key `asyncio.Lock` (or use an in-flight dict) so only the first coroutine fetches; the rest wait and read from cache.

---

### 1.3 Rate-limiter memory leak

`_RateLimiter` in `tcbot/modules/helper/decorators.py` stores per-user timestamp buckets in a dict that is only pruned when that user sends another message. Users who send one message and never interact again accumulate stale entries indefinitely.

**Fix:** Run a periodic cleanup coroutine (e.g., every 10 minutes via `Application.job_queue`) that removes buckets whose most recent timestamp is older than the window.

---

### 1.4 `asyncio.gather` missing `return_exceptions=True`

Several `gather()` calls across moderation flows do not set `return_exceptions=True`. A single Telegram API error in any task cancels all remaining tasks in that gather and raises, leaving the operation in an inconsistent state (e.g., ban recorded in DB but log not posted, or group enforcement partially applied).

Files affected: `tcbot/modules/banning.py`, `tcbot/modules/kicking.py`, `tcbot/modules/muting.py`, `tcbot/modules/warnings.py`.

**Fix:** Add `return_exceptions=True` and inspect results for `BaseException` instances, logging any failures.

---

### 1.5 Module-level f-string in `appeal_flow.py`

`_INSTRUCTION_TEXT` on line 59 is a module-level constant that interpolates `cfg.community_name` at import time. If `community_name` changes at runtime (e.g., env var update + restart), the string must be a lazy call rather than a frozen constant. Currently this is harmless but fragile.

**Fix:** Convert to a `@functools.lru_cache(maxsize=1)` function or evaluate inside the handler.

---

## Phase 2 — Reliability and Safety

These require small design decisions but are well-bounded.

### 2.1 Outgoing Telegram API rate limiting

`fan_out()` in `tcbot/utils/dispatch.py` uses a hardcoded `asyncio.Semaphore(10)` with no retry logic. When the bot operates on large federations, mass bans and broadcasts will trigger Telegram's flood control (HTTP 429). Currently those errors surface as exceptions caught by `fan_out` and counted as failures, but the action is not retried.

**Plan:**
- Make the semaphore size configurable via `FAN_OUT_CONCURRENCY` env var (default 10).
- Add exponential backoff with jitter on `RetryAfter` exceptions inside `fan_out`.
- Cap total retry duration per task at 60 seconds before giving up and logging.

---

### 2.2 Broadcast timeout per group

`tcbot/modules/broadcasting.py` dispatches via `fan_out()` with no per-task timeout. A single unresponsive group can hold a semaphore slot for the duration of the HTTP timeout (currently 15 s), stalling the broadcast for all subsequent groups.

**Fix:** Wrap each fan-out task in `asyncio.wait_for(..., timeout=10)` inside `fan_out`, or add a `task_timeout` parameter to `fan_out()` itself.

---

### 2.3 Album accumulator state in `ban_flow.py`

`_albums` and `_album_meta` are module-level dicts. With `concurrent_updates=True` enabled in the PTB application, multiple coroutines may read and write these dicts concurrently during a media group upload. The `asyncio.create_task(_flush_album(...))` pattern is the mitigation, but the dicts themselves are not guarded.

**Fix:** Wrap mutations in a module-level `asyncio.Lock`, or move the accumulator state into `ctx.bot_data` (which PTB serialises per-chat-per-user).

---

### 2.4 Granular admin permission levels

`tcbot/database/admins_db.py` has a `TODO` noting that all admins currently have identical permissions. The role hierarchy (Founder → Admin → Developer → Tester) exists in `roles_db.py`, but within the Admin tier there is no further distinction.

**Plan:** Define two Admin sub-tiers — `admin` (full moderation + group management) and `moderator` (moderation only, no group connect/disconnect or broadcast). Store sub-tier in the `tc_admins` collection. Update `can_act_on()` and the `@staff_only` / `@mod_only` decorators accordingly.

---

### 2.5 Direct Developer/Tester promotion security gap

Per `agents/RULES.md`, promotion to Developer or Tester is direct (no approval queue), while promotion to Admin goes through a request queue reviewed by the Founder. An Admin can therefore grant a malicious actor Developer-level permissions (which include ban/unban rights) without Founder visibility.

**Plan:** Add an audit log entry to the log channel for every direct Developer/Tester promotion, posted immediately when the promotion completes. This does not block the action but ensures the Founder can see it.

---

## Phase 3 — Test Coverage

The current suite tests pure functions and isolated helpers well. Entire modules — particularly the conversation flows and DB interaction layers — have no direct tests.

### 3.1 Coverage gaps

| Module / Layer | Current coverage | Target |
|---|---|---|
| `tcbot/modules/banning.py` | None | Entry validation, permission checks |
| `tcbot/modules/unbanning.py` | None | Active-ban check, group dispatch |
| `tcbot/modules/admins.py` | None | Promote/demote permission matrix |
| `tcbot/modules/broadcasting.py` | None | Fan-out result handling |
| `tcbot/database/*.py` | None | All DB operations (via mongomock) |
| `tcbot/modules/helper/workflows/ban_flow.py` | None | Album accumulation, proof upload path |
| `tcbot/modules/helper/workflows/reason_flow.py` | None | State machine transitions |
| `tcbot/utils/dispatch.py` | None | Semaphore bounding, exception isolation |
| `tcbot/database/cache.py` | None | TTL expiry, concurrent fetch guard |

### 3.2 Infrastructure needed

- Add `mongomock-motor` (or `motor-stubs` with a test fixture) to the test extras so DB tests can run without a live MongoDB instance.
- Add `pytest-cov` to track coverage percentages in CI. Set a baseline floor (e.g., 60%) and enforce it.
- Add a `conftest.py` fixture that builds a minimal PTB `Application` for integration tests of conversation handlers.

### 3.3 Property-based testing

The `_RateLimiter` and `fan_out` are good candidates for property-based testing with `hypothesis` — their correctness under arbitrary timing and failure patterns is hard to cover with fixed test cases.

---

## Phase 4 — Feature Additions

These are net-new capabilities. None are blocked by earlier phases, but Phase 1 defects should be resolved first to avoid building on top of known silent failures.

### 4.1 Per-group moderation configuration

Currently all connected groups share the same moderation settings (warn threshold, mute duration defaults). Store per-group overrides in MongoDB so group admins can tune thresholds without affecting the federation-wide defaults.

Required: new `tc_group_config` collection, a `/tcconfig` command (staff only), and updated warn/mute logic to read per-group values with federation defaults as fallback.

### 4.2 Scheduled unban

Allow bans to be issued with an optional duration: `/tcban @user 7d [reason]`. Store `expires_at` in the ban document and add a `job_queue` task that polls for expired bans and lifts them automatically.

Required: `expires_at` field in `tc_bans`, duration parser utility, scheduled job.

### 4.3 Action history per user

`/tchistory @user` — shows the last N moderation actions (bans, kicks, mutes, warns, role changes) for a target user. Currently this data is split across multiple collections with no unified query path.

Required: either a `tc_audit_log` collection written to on every action, or a cross-collection aggregation query.

### 4.4 Bulk group status report

`/tcstatus` — returns a paginated list of all connected groups with their member count (from Telegram API), last-seen activity date, and pending-join count. Intended for Founder use to identify dead or stale groups.

### 4.5 Appeal cooldown

Prevent a user from submitting multiple appeals in rapid succession. After a rejected appeal, block resubmission for a configurable window (e.g., 72 hours). Store `last_appeal_at` and `appeal_count` in the ban document.

---

## Phase 5 — Infrastructure and Operations

### 5.1 Schema migration tooling

There is no migration path for breaking MongoDB schema changes. Adding fields (e.g., `expires_at` in Phase 4.2) is additive and safe, but future changes that rename or remove fields need a plan.

**Approach:** Add a `tc_meta` collection that stores the current schema version. Write a `migrations/` directory with numbered scripts (`001_add_expires_at.py`, etc.) that are run once on startup if the stored version is behind.

### 5.2 Structured logging

The current logger (`tcbot/utils/logger.py`) emits human-readable text. In a deployed environment this makes log aggregation and search harder.

**Plan:** Add a `LOG_FORMAT=json` env var option that switches to structured JSON output (using `python-json-logger` or a small custom formatter). Keep the human-readable format as default for local development.

### 5.3 Health check endpoint improvements

`tcbot/alive.py` exposes a `/` route that returns a static string. It does not verify that the bot or database is actually reachable.

**Plan:** Add a `/health` route that checks:
1. MongoDB ping (via `client.admin.command("ping")`)
2. Bot token validity (cached — not called on every request)

Return `{"status": "ok"}` (200) or `{"status": "degraded", "reason": "..."}` (503).

### 5.4 Dependency pinning and automated updates

`uv.lock` pins all transitive dependencies. Add a periodic review process (Dependabot or a manual monthly task) to update `python-telegram-bot`, `motor`, and `cryptography` — the three packages most likely to have security-relevant updates.

---

## Tracking

Issues identified across this plan that are concrete enough to file immediately:

| ID | Description | Phase |
|---|---|---|
| DEF-01 | Silent `pass` in 12 locations | 1.1 |
| DEF-02 | TTLCache thundering herd | 1.2 |
| DEF-03 | Rate-limiter bucket memory leak | 1.3 |
| DEF-04 | Missing `return_exceptions` in gather calls | 1.4 |
| DEF-05 | Module-level f-string in appeal_flow | 1.5 |
| REL-01 | `fan_out` — no retry on 429, fixed concurrency | 2.1 |
| REL-02 | Broadcast — no per-group timeout | 2.2 |
| REL-03 | Album accumulator — unguarded concurrent writes | 2.3 |
| REL-04 | Admin granular permissions | 2.4 |
| REL-05 | Direct promotion audit gap | 2.5 |
| TST-01 | DB layer tests (mongomock) | 3.1–3.2 |
| TST-02 | Conversation handler integration tests | 3.2 |
| TST-03 | Coverage floor enforcement | 3.2 |
| FEA-01 | Scheduled unban | 4.2 |
| FEA-02 | Per-group moderation config | 4.1 |
| FEA-03 | Action history per user | 4.3 |
| OPS-01 | Schema migration tooling | 5.1 |
| OPS-02 | Structured JSON logging | 5.2 |
| OPS-03 | Real health check endpoint | 5.3 |
