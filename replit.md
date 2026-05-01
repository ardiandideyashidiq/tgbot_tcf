# Transsion Core Federation (TCF) Telegram Bot

Production Telegram bot for the Transsion Core Federation. Manages group affiliation, centralised banning with proof uploads (**automatic** cross-group enforcement), admin hierarchy with promotion requests, appeal flow, broadcast, interactive help/start menu, welcome/goodbye, member tracking, group-scoped kick/mute/warn moderation, and detailed channel logging.

## Stack

- Python 3.11
- python-telegram-bot 22.5 (async, polling) with JobQueue
- MongoDB via `motor` (database: `tcf_bot`)
- Flask for a small keep-alive server on port 8080

## Layout

```
tgbot_tcf/
├── __init__.py          # Env loading, branding, hardcoded chat/topic IDs, exact-text constants
├── __main__.py          # Entry point: builds the Application and registers handlers
├── keepalive.py         # Tiny Flask app on port 8080
├── modules/             # Domain layer: business logic for every feature
│   ├── messages.py      # Centralised user-facing copy (M.*)
│   ├── log_templates.py # Builders for log-channel messages
│   ├── keyboards.py     # Reusable inline-keyboard factories
│   ├── help_text.py     # Help module catalogue and detail copy
│   ├── bans.py          # Ban / unban lifecycle and proof-caption builders
│   ├── kicking.py       # Kick lifecycle (ban+unban, audit record)
│   ├── muting.py        # Mute / unmute lifecycle, duration parsing
│   ├── warnings.py      # Warn / unwarn / warn-list lifecycle
│   ├── affiliations.py  # Group affiliation lifecycle and permission checks
│   ├── admins_mod.py    # Owner / admin role lifecycle and promotion requests
│   ├── appeals.py       # Appeal parsing, 12-hour rule, review templates
│   ├── broadcast_mod.py # Broadcast loop over active federated groups
│   ├── maintenance_mod.py # Leave-all and cleanup loops
│   └── cache_repo.py    # Member-cache write paths and admin-list seeding
├── database/
│   ├── mongo.py         # Motor client + collections + index init
│   ├── admins.py        # tc_owners / tc_admins repository
│   ├── bans.py          # bans repository
│   ├── groups.py        # federated_groups repository
│   ├── joins.py         # pending_joins repository
│   ├── kicks.py         # kicks audit-log repository (no is_active)
│   ├── members.py       # member_cache repository
│   ├── muted.py         # muted repository (per-group, is_active)
│   ├── requests.py      # promotion_requests repository
│   ├── warns.py         # warns repository (per-group, is_active)
│   └── __init__.py      # Re-exports raw collections + repos + init_db
├── utils/
│   ├── auth.py          # is_tc_owner / is_tc_admin / is_authorized
│   ├── format.py        # UTC time formatting, HTML link builders, group_display, topic links
│   ├── logger.py        # log_to_channel and edit_log_message helpers
│   ├── prefix.py        # Multi-prefix dispatcher for `.cmd` and `!cmd`
│   ├── targets.py       # Reply / @username / numeric-id target resolver
│   └── users.py         # Identity resolver with member_cache fallback
└── handlers/
    ├── helper/
    │   ├── auth.py      # Owner-only / authorized-only deny helpers
    │   ├── enforce.py   # Automatic cross-group ban / unban enforcement (Features 5, 6, 8)
    │   ├── messaging.py # safe_edit_text and reply utilities
    │   └── targets.py   # Resolve-target-or-reply-with-error helpers
    ├── affiliate.py     # Group affiliation + pending_joins fallback + auto-completion on bot promotion
    ├── admins.py        # /tcpromote, /tcdemote, /tctransfer, /tcpromoterequests + promotion request flow
    ├── ban.py           # /tcban (proof-collection state machine) and /tcunban (with auto cross-group enforcement)
    ├── appeal.py        # Deep-link appeal flow + admin Approve/Reject (12h rule, auto cross-group unban)
    ├── kicking.py       # /kick, /tckkick, /kickout (single-group kick, PRD Feature 39)
    ├── mutes.py         # /mute, /tmute, /unmute, /tunmute (PRD Features 34–35)
    ├── warns.py         # /warn, /twarn, /unwarn, /tunwarn, /warns, /twarnlist (PRD Features 36–38)
    ├── broadcast.py     # /tcbroadcast
    ├── checks.py        # /checkme, /baninfo
    ├── lists.py         # /tcfgroups, /tcstats (also build_admins_text for info sub-menu)
    ├── links.py         # /tclinks (official links with URL buttons)
    ├── menu.py          # /start menu and interactive /help system
    ├── welcome.py       # Welcome / goodbye in MAIN_GROUP and EXEC_GROUP only
    ├── help.py          # /start, /help, /commands entry points
    ├── maintenance.py   # /leaveall, /cleanup
    └── membercache.py   # Per-affiliated-group member tracking (Feature 33)
```

## MongoDB Collections

- `tc_owners` — federation owner(s)
- `tc_admins` — federation admins
- `federated_groups` — affiliated groups
- `bans` — ban records (includes proof_message_id, review_message_id, review_timestamp)
- `promotion_requests` — pending promote/demote requests
- `pending_joins` — affiliations waiting for the bot to be granted admin rights
- `member_cache` — per-(chat_id, user_id) cache of seen members and their statuses
- `kicks` — immutable audit log of kick events (no is_active; one-group, non-propagating)
- `muted` — per-(user_id, chat_id) mute records with is_active and optional until_date
- `warns` — per-(user_id, chat_id) warning records with is_active

## Required Secrets

- `BOT_TOKEN` – Telegram bot token
- `MONGODB_URI` – MongoDB connection string

## Command Aliases (all work with `/`, `.`, `!` prefixes)

| Feature              | Aliases                                  |
|----------------------|------------------------------------------|
| Start/menu           | `/start`                                 |
| Help                 | `/help`, `/commands`                     |
| Ban                  | `/tcban`, `/ban`, `/tcfban`              |
| Unban                | `/tcunban`, `/unban`, `/tcfunban`        |
| Check own ban        | `/checkme`, `/myban`, `/amibanned`       |
| Ban info             | `/baninfo`, `/checkban`, `/banstatus`    |
| Promote              | `/tcpromote`, `/promote`, `/tcfpromote`  |
| Demote               | `/tcdemote`, `/demote`, `/tcfdemote`     |
| Transfer owner       | `/tctransfer`, `/transfer`, `/tcowner`   |
| Promo requests       | `/tcpromoterequests`, `/promoreqs`, `/tcreqs` |
| Broadcast            | `/tcbroadcast`, `/broadcast`, `/tcannounce` |
| Join federation      | `/jointc`, `/requestjoin`, `/applytc`    |
| Disaffiliate (self)  | `/detc`, `/leavetc`, `/untc`             |
| Remove group by ID   | `/rmtc`, `/removetc`, `/deletetc`        |
| List groups          | `/tcfgroups`, `/groups`, `/listtc`       |
| Stats                | `/tcstats`, `/stats`, `/tcinfo`          |
| Links                | `/tclinks`, `/links`, `/tcconfig`        |
| Leave all groups     | `/leaveall`, `/exitall`, `/tcleave`      |
| Cleanup dead groups  | `/cleanup`, `/purge`, `/tcclean`         |
| Kick (single group)  | `/kick`, `/tckkick`, `/kickout`          |
| Mute (group-scoped)  | `/mute`, `/tmute`                        |
| Unmute               | `/unmute`, `/tunmute`                    |
| Warn (group-scoped)  | `/warn`, `/twarn`                        |
| Unwarn               | `/unwarn`, `/tunwarn`                    |
| List warnings        | `/warns`, `/twarnlist`                   |

> Per PROMPT Feature 5/6, **no manual sync command exists**. Cross-group ban and unban enforcement is automatic on every `/tcban`, `/tcunban`, and approved appeal.

## Notes

- Every command works with three prefixes: `/cmd`, `.cmd`, and `!cmd`.
- All log messages sent to `LOG_CHANNEL` include the branded line `𝘛𝘊𝘍 - 𝘛𝘳𝘢𝘯𝘴𝘴𝘪𝘰𝘯 𝘊𝘰𝘳𝘦 𝘍𝘦𝘥𝘦𝘳𝘢𝘵𝘪𝘰𝘯`.
- Ban / unban / appeal-approve logs include an `Enforced in N group(s); failed in M group(s).` summary.
- Affiliation flow: if the bot lacks the required perms when the owner clicks Join, the request is parked in `pending_joins`. As soon as the bot is later promoted with the required perms, affiliation completes automatically via `my_chat_member`.
- Member cache is seeded with reachable administrators on first affiliation, then kept fresh by every chat message (group ≥ 2 handler) and every per-user `chat_member` update.
- Timestamps are UTC formatted as `DD-MM-YYYY | HH:MM`.
- Keep-alive Flask server runs on port **8080**.
- About text is reached only via deep link `https://t.me/<bot>?start=about` or the start menu.
- Promotion by admins creates a pending request reviewed by the owner; promotion by the owner is immediate.
- Ban proof collection uses a 60-second timeout state machine.
- Appeal flow: 12-hour window where only the banning admin may act; after that any TC admin can approve/reject.
- On startup the bot seeds the initial TC Owner (`INITIAL_OWNER_ID`) into `tc_owners` if empty.
- Run locally with `python -m tgbot_tcf`.

## Hardcoded Telegram IDs (`tgbot_tcf/__init__.py`)

- `LOG_CHANNEL = -1003941141635`
- `MAIN_GROUP = -1003872207988` (forum)
- `PROOF_TOPIC = 67`
- `APPEAL_TOPIC = 12`
- `APPEAL_DISCUSSION_TOPIC = 11`
- `MAIN_CHANNEL = -1003852970764`
- `EXEC_GROUP = -1002333013065`
- `INITIAL_OWNER_ID = 7146954165`
