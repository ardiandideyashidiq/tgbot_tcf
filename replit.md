# TCF Federation Bot

Telegram federation management bot for **Transsion Core Federation (TCF)**.
Runs via `python -m tcbot`.

## Stack

- Python 3.11
- python-telegram-bot 22.5 (async)
- Motor (async MongoDB driver)
- Flask (keep-alive on port 5000)
- python-dotenv

## Project Structure

```
tcbot/
  config.py            – singleton config loader (parses config.env)
  alive.py             – Flask keep-alive, daemon thread
  __main__.py          – entry point, auto-discovers modules, starts polling
  database/
    mongos.py          – MongoDB connection
    admins_db.py       – owners and admins
    bans_db.py         – federation bans
    groups_db.py       – affiliated groups and pending joins
    users_db.py        – user cache
    queues_db.py       – promotion request queue
    warns_db.py        – per-group warnings
    kicks_db.py        – kick log
    mutes_db.py        – mute log
  modules/
    banning.py         – /tcban, /fban (ConversationHandler with album support)
    unbanning.py       – /tcunban, /funban
    appealing.py       – /appeal DM flow + staff review callbacks
    checking.py        – /checkme, /baninfo
    admins.py          – /tcpromote, /tcdemote, /tctransfer, /tcpromoterequests
    connecting.py      – bot added event, /jointc, join_decision callbacks
    disconnecting.py   – /detc, /rmtc
    groups.py          – /tcfgroups
    stats.py           – /tcstats
    broadcasting.py    – /tcbroadcast
    maintenance.py     – /leaveall, /cleanup
    links.py           – /tclinks
    greeting.py        – welcome/goodbye + auto-ban on join
    start.py           – /start, /help (auto-discover __module_name__ + __help_text__)
    helper/
      decorators.py    – @owner_only, @staff_only
      extraction.py    – resolve ban target from reply/mention/ID
      formatter.py     – HTML helpers
      keyboards.py     – InlineKeyboardMarkup builders
      parse_editmsg.py – safe message edit
      parse_link.py    – t.me/c/... link builder
      parse_logmsg.py  – all log message composers
      workflows/
        ban_flow.py       – ban ConversationHandler
        appeal_flow.py    – appeal ConversationHandler
        unban_flow.py     – unban execution
        connected_flow.py – group join/leave flow
        warning_flow.py   – warn + auto-ban
        muting_flow.py    – mute/unmute
  utils/
    prefixes.py        – build_prefixed_filters() for /, !, . prefixes
    logger.py          – logging setup
    timedate_format.py – datetime formatting
    chat_status.py     – admin status helpers
    chat_permissions.py – ChatPermissions presets
```

## Module System

Every module file can export:
- `__module_name__` – display name (shown in /help menu)
- `__help_text__` – help description (HTML, shown per module)
- `__handlers__` – list of telegram Handler objects

`start.py` auto-discovers all modules and builds a dynamic /help menu.
Modules without `__module_name__` are loaded but not shown in help.

## Configuration

All config is read from `config.env`. See `config.env.example` for the format.
Key vars: `BOT_TOKEN`, `MONGODB_URI`, `DB_NAME`, `OWNER_ID`, `MAIN_GROUP`,
`LOGS`, `PROOFS`, `APPEALS`, `EXEC_GROUP`, `COMMUNITY_NAME`.

## Important Rules

- No JavaScript/TypeScript/Node files
- No single Python file over 600 lines
- Copyright notice on every Python file
- Comment style: `## single line comment` (no docstring walls)
- Friendly but formal tone
