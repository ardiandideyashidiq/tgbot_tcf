# Transsion Core Federation (TCF) Telegram Bot

Production Telegram bot for the Transsion Core Federation (TCF). Manages group affiliation,
federation-wide bans with proof uploads (with automatic cross-group enforcement), an admin
hierarchy with promotion requests, an appeal flow, broadcast, interactive help/start menu,
welcome/goodbye messages, member tracking, and detailed channel logging.

## Stack

- Python 3.11+
- python-telegram-bot 22.5 (async, long-polling) with JobQueue
- MongoDB via `motor` async driver (database: `tcf_bot`)
- Flask - minimal keep-alive server on port 8080

---

## Setup

```bash
git clone <repo>
cd <repo>

# Python 3.11+
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Copy the example environment file and fill in your credentials:

```bash
cp c.env.example .env
```

| Variable      | Description                                       |
| ------------- | ------------------------------------------------- |
| `BOT_TOKEN`   | Telegram bot token from @BotFather                |
| `MONGODB_URI` | MongoDB connection string (Atlas or self-hosted)  |

All other variables in `c.env.example` have defaults matching the live federation IDs.

---

## Running

```bash
python -m tgbot_tcf
```

On startup the bot will:
1. Load environment variables from `.env` (or `c.env`).
2. Connect to MongoDB and create required indexes.
3. Seed the initial Federation Owner if `tc_owners` is empty.
4. Start the Flask keep-alive server in a daemon thread on port `8080`.
5. Begin long-polling Telegram for all update types.

---

## Command prefixes and aliases

Every command works with three prefixes and at least three aliases:

- Prefixes: `/`, `.`, `!`
- Example: `/tcban`, `.tcban`, `!tcban` are all equivalent.

---

## Commands

### Ban management

| Command                        | Aliases                      | Who              | Description                                          |
| ------------------------------ | ---------------------------- | ---------------- | ---------------------------------------------------- |
| `/tcban <target> <reason>`     | `/ban`, `/tcfban`            | TC Owner / Admin | Federation ban with mandatory proof upload           |
| `/tcunban <target> [reason]`   | `/unban`, `/tcfunban`        | TC Owner / Admin | Lift a federation ban                                |
| `/checkme`                     | `/myban`, `/amibanned`       | Everyone         | Check your own ban status                            |
| `/baninfo <target>`            | `/checkban`, `/banstatus`    | Everyone         | View detailed ban info for any user                  |

### Admin management

| Command                  | Aliases                          | Who                                  | Description                              |
| ------------------------ | -------------------------------- | ------------------------------------ | ---------------------------------------- |
| `/tcpromote <target>`    | `/promote`, `/tcfpromote`        | TC Owner (immediate) / Admin (request) | Promote a user to TC Admin             |
| `/tcdemote <target>`     | `/demote`, `/tcfdemote`          | TC Owner only                        | Demote a TC Admin                        |
| `/tctransfer <target>`   | `/transfer`, `/tcowner`          | TC Owner only                        | Transfer federation ownership            |
| `/tcpromoterequests`     | `/promoreqs`, `/tcreqs`          | TC Owner only                        | List and act on pending promotion requests |

### Group affiliation

| Command              | Aliases                       | Who                   | Description                                  |
| -------------------- | ----------------------------- | --------------------- | -------------------------------------------- |
| `/jointc`            | `/requestjoin`, `/applytc`    | Group Owner           | Explicitly affiliate the current group       |
| `/detc`              | `/leavetc`, `/untc`           | Group Owner / TC Admin | Disaffiliate the current group              |
| `/rmtc <group_id>`   | `/removetc`, `/deletetc`      | TC Owner / Admin      | Remove a group by ID from anywhere           |

### Listings and info

| Command       | Aliases                  | Who       | Description                     |
| ------------- | ------------------------ | --------- | ------------------------------- |
| `/tcfgroups`  | `/groups`, `/listtc`     | Everyone  | List active affiliated groups   |
| `/tcstats`    | `/stats`, `/tcinfo`      | Everyone  | Federation statistics           |
| `/tclinks`    | `/links`, `/tcconfig`    | Everyone  | Official TCF links              |

### Maintenance

| Command                    | Aliases                      | Who              | Description                                        |
| -------------------------- | ---------------------------- | ---------------- | -------------------------------------------------- |
| `/tcbroadcast <message>`   | `/broadcast`, `/tcannounce`  | TC Owner / Admin | Send a message to all affiliated groups            |
| `/leaveall`                | `/exitall`, `/tcleave`       | TC Owner only    | Leave every affiliated group                       |
| `/cleanup`                 | `/purge`, `/tcclean`         | TC Owner / Admin | Remove groups where the bot is no longer present   |

### Help and navigation

| Command                     | Description                           |
| --------------------------- | ------------------------------------- |
| `/start`                    | Interactive start menu (PM only)      |
| `/start appeal_<ban_id>`    | Begin an appeal (PM only)             |
| `/start about`              | About TCF                             |
| `/help` or `/commands`      | Interactive help system               |

---

## Main features

1. **Group affiliation on add** - when the bot is added to a group it sends a Join / Cancel
   prompt (visible to the group owner only). Permissions are checked; if missing, the bot
   waits and completes affiliation automatically once they are granted.
2. **Federation-wide bans** - `/tcban` opens a 60-second proof-collection window. Single or
   album media (photos / videos) are accepted. The ban is immediately enforced across every
   active affiliated group where the bot has `can_restrict_members`.
3. **Appeal flow** - banned users receive a Submit Appeal button on the log entry. The flow
   starts via `/start appeal_<ban_id>` in PM. An approved appeal automatically unbans the user
   across all groups. The original banning admin has a 12-hour exclusivity window before other
   admins can decide.
4. **Promotion requests** - TC admins can initiate a promotion; the owner must approve it via
   inline buttons sent to them in PM (or in the log channel if PM fails).
5. **Welcome / goodbye messages** - sent in `MAIN_GROUP` and `EXEC_GROUP` only; no other group.
6. **Member cache** - on affiliation the bot seeds admin-list data; every subsequent message
   and chat-member event updates the cache for accurate display in logs.
7. **Interactive start menu** - About, Help, Groups, Additional, Information, Privacy sections
   with full back-navigation. Edits the existing message rather than sending new ones.
8. **Audit log** - every federation event is logged to `LOG_CHANNEL` with the branding line
   and a UTC timestamp formatted `DD-MM-YYYY | HH:MM`.

---

## Project structure

```
tgbot_tcf/
|-- __init__.py          # Env loading, branding, hardcoded chat/topic IDs
|-- __main__.py          # Entry point: builds the Application and registers all handlers
|-- keepalive.py         # Tiny Flask app on 0.0.0.0:8080 started in a daemon thread
|-- database/
|   |-- __init__.py      # Re-exports raw collections + named repository modules
|   |-- mongo.py         # Motor client + collection handles + index creation
|   |-- admins.py        # tc_owners / tc_admins repository helpers
|   |-- bans.py          # bans collection repository helpers
|   |-- groups.py        # federated_groups repository helpers
|   |-- joins.py         # pending_joins repository helpers
|   |-- members.py       # member_cache repository helpers
|   |-- requests.py      # promotion_requests repository helpers
|-- modules/
|   |-- __init__.py
|   |-- admins_mod.py    # Owner/admin role management business logic
|   |-- affiliations.py  # Group affiliation lifecycle
|   |-- appeals.py       # Appeal parsing, 12-hour reviewer rule, posting logic
|   |-- bans.py          # Ban lifecycle, proof posting, caption builders
|   |-- broadcast_mod.py # Broadcast loop over active groups
|   |-- cache_repo.py    # Member-cache write paths and seeding
|   |-- help_text.py     # Help module catalogue and detail text
|   |-- keyboards.py     # All inline keyboard factories
|   |-- log_templates.py # Builders for every log-channel message
|   |-- maintenance_mod.py # Leave-all and cleanup loops
|   |-- messages.py      # Single source of truth for every user-facing string
|-- handlers/
|   |-- __init__.py
|   |-- helper/
|   |   |-- __init__.py
|   |   |-- auth.py      # Authorization guards
|   |   |-- enforce.py   # Automatic cross-group ban/unban enforcement
|   |   |-- messaging.py # Safe edit/send wrappers
|   |   |-- targets.py   # resolve_or_complain wrapper
|   |-- admins.py        # /tcpromote, /tcdemote, /tctransfer, /tcpromoterequests
|   |-- affiliate.py     # Group affiliation, /jointc, /detc, /rmtc, my_chat_member
|   |-- appeal.py        # Deep-link appeal flow + Approve/Reject review callbacks
|   |-- ban.py           # /tcban (proof state machine) and /tcunban
|   |-- broadcast.py     # /tcbroadcast
|   |-- checks.py        # /checkme, /baninfo
|   |-- help.py          # /start, /help, /commands entry points
|   |-- links.py         # /tclinks
|   |-- lists.py         # /tcfgroups, /tcstats + text builders for menus
|   |-- maintenance.py   # /leaveall, /cleanup
|   |-- membercache.py   # Per-group member tracking
|   |-- menu.py          # Start menu, interactive help, information, privacy callbacks
|   |-- welcome.py       # Welcome/goodbye in MAIN_GROUP and EXEC_GROUP
|-- utils/
    |-- __init__.py
    |-- auth.py          # is_tc_owner / is_tc_admin / is_authorized
    |-- format.py        # UTC time formatting, user_link, topic_link helpers
    |-- logger.py        # log_to_channel helper
    |-- prefix.py        # Multi-prefix dispatcher for .cmd and !cmd
    |-- targets.py       # Reply / username / numeric-id target resolver
```

---

## MongoDB collections

| Collection            | Description                                                  |
| --------------------- | ------------------------------------------------------------ |
| `federated_groups`    | Active and historical affiliated groups                      |
| `tc_owners`           | Exactly one document - the current federation owner          |
| `tc_admins`           | Federation admins                                            |
| `bans`                | All federation bans with full audit trail                    |
| `promotion_requests`  | Pending / resolved promotion requests                        |
| `pending_joins`       | Groups waiting for bot to be granted admin permissions       |
| `member_cache`        | Per-(chat, user) identity snapshot for log enrichment        |

---

## Important notes

- No emoji anywhere in messages, captions, or button labels.
- Credentials (`BOT_TOKEN`, `MONGODB_URI`) are always loaded from the environment.
- All UTC timestamps are formatted `DD-MM-YYYY | HH:MM`.
- Every log message sent to the log channel contains the exact branding line:
  `TF - Transsion Core Federation` (in stylized Unicode italic form).
- The keep-alive Flask server runs on port `8080` (overridable with `KEEPALIVE_PORT`).
- The bot runs on Linux, macOS, Windows, and Android (Termux) without modification.
