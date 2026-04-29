# Transsion Core Federation (TCF) Telegram Bot

Production Telegram bot for the Transsion Core Federation. Manages group affiliation, centralized banning with proof uploads (with **automatic** cross-group enforcement), admin hierarchy with promotion requests, appeal flow, broadcast, interactive help/start menu, welcome/goodbye messages, member tracking, and detailed channel logging.

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
├── modules/             # Reserved for feature-specific extra logic
├── database/
│   ├── mongo.py         # Motor client + collections + index init
│   └── __init__.py      # Re-exports collections + init_db
├── utils/
│   ├── auth.py          # is_tc_owner / is_tc_admin / is_authorized
│   ├── format.py        # UTC time formatting, HTML link builders, topic links
│   ├── logger.py        # log_to_channel helper (HTML, optional inline keyboard)
│   ├── prefix.py        # Multi-prefix dispatcher for `.cmd` and `!cmd`
│   └── targets.py       # Reply / @username / numeric-id target resolver
└── handlers/
    ├── helper/
    │   └── enforce.py   # Automatic cross-group ban / unban enforcement (Features 5, 6, 8)
    ├── affiliate.py     # Group affiliation + pending_joins fallback + auto-completion on bot promotion
    ├── admins.py        # /tcpromote, /tcdemote, /tctransfer, /tcpromoterequests + promotion request flow
    ├── ban.py           # /tcban (proof-collection state machine) and /tcunban (with auto cross-group enforcement)
    ├── appeal.py        # Deep-link appeal flow + admin Approve/Reject (12h rule, auto cross-group unban)
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
