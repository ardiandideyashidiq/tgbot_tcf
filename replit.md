# Transsion Core Federation (TCF) Telegram Bot

Production Telegram bot that manages a federation of Telegram groups. It handles affiliation, centralized banning with proof uploads, an admin hierarchy, an appeal flow, broadcast, ban sync, and detailed channel logging.

## Stack

- Python 3.11
- python-telegram-bot 22.5 (async, polling) with JobQueue
- MongoDB via `motor` (database: `tcf_bot`)
- Flask for a small keep-alive server

## Layout

```
tgbot_tcf/
├── __main__.py          # Entry point: builds the Application and registers handlers
├── config.py            # Constants, env loading, branding, hardcoded chat/topic IDs
├── keepalive.py         # Tiny Flask app on port 8000 (KEEPALIVE_PORT to override)
├── db/
│   └── mongo.py         # Motor client + collections + index init
├── utils/
│   ├── auth.py          # is_fed_owner / is_fed_admin / is_authorized helpers
│   ├── format.py        # UTC time formatting, HTML link builders, topic links
│   ├── logger.py        # log_to_channel helper (HTML, optional inline keyboard)
│   └── targets.py       # Reply / @username / numeric-id target resolver
└── handlers/
    ├── affiliate.py     # Group affiliation, /joinfed, /defed, /rmfed, my_chat_member
    ├── admins.py        # /cpromote /cdemote /transferowner
    ├── ban.py           # /cban (with proof-collection state machine) and /cunban
    ├── appeal.py        # Deep-link appeal flow + admin Approve/Reject
    ├── broadcast.py     # /broadcast
    ├── sync.py          # /syncban
    ├── checks.py        # /checkme, /baninfo
    ├── lists.py         # /fedgroups, /fedstats, /fedchannels
    ├── help.py          # /help, /start, /about
    └── maintenance.py   # /leaveall, /cleanup
```

## Required secrets

- `BOT_TOKEN` – Telegram bot token
- `MONGODB_URI` – MongoDB connection string

## Notes

- All commands have at least three aliases (e.g. `/cban`, `/comban`, `/fban`).
- All log messages sent to `LOG_CHANNEL` include the branded line `𝘛𝘊𝘍 - 𝘛𝘳𝘢𝘯𝘴𝘴𝘪𝘰𝘯 𝘊𝘰𝘳𝘦 𝘍𝘦𝘥𝘦𝘳𝘢𝘵𝘪𝘰𝘯`.
- Timestamps are UTC and formatted `DD-MM-YYYY | HH:MM`.
- The keep-alive Flask server uses port **8000** (not 8080) because port 8080 is already in use by another artifact in this workspace. Override with `KEEPALIVE_PORT` if needed.
- Run locally with `python -m tgbot_tcf`. The `TCF Bot` workflow does this automatically.

## Hardcoded Telegram IDs

See `tgbot_tcf/config.py`:

- `LOG_CHANNEL = -1003941141635`
- `MAIN_GROUP   = -1003872207988` (forum)
- `PROOF_TOPIC  = 67`
- `APPEAL_TOPIC = 12`
- `APPEAL_DISCUSSION_TOPIC = 11`
