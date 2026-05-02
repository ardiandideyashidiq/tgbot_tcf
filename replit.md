# TCF Telegram Bot

## Overview

A Telegram bot for the Transsion Core Federation (TCF) community. Manages federation-wide bans, appeals, group affiliations, admin promotions, and moderation.

## Architecture

- **Language:** Python 3.11
- **Bot framework:** python-telegram-bot 22.5 (polling mode)
- **Database:** MongoDB (via motor, async)
- **Web server:** Flask (keep-alive / health-check on port 5000)
- **Entry point:** `python3 -m tcbot`

## Key Modules

- `tcbot/__init__.py` — Config singleton (`cfg` and `configs`), loaded from environment variables (with config.env as fallback)
- `tcbot/__main__.py` — Entry point: sets up logging, starts Flask keepalive, discovers handlers, starts polling
- `tcbot/alive.py` — Flask keep-alive server running on port 5000
- `tcbot/database/` — MongoDB helpers (admins, bans, groups, users, warns, etc.)
- `tcbot/modules/` — Auto-discovered bot command modules (ban, appeal, connect, etc.)
- `tcbot/utils/` — Logging formatter, prefix builder, time utilities

## Configuration

Secrets are stored in Replit Secrets (environment variables). Non-sensitive config is in `.replit` env vars:

- `BOT_TOKEN` — Telegram bot token (**Replit Secret**)
- `MONGODB_URI` — MongoDB connection string (**Replit Secret**)
- `OWNER_ID` — Initial owner Telegram user ID (env var)
- `DB_NAME` — MongoDB database name (env var, default: "tcbot")
- `MAIN_GROUP` — Main Telegram group/forum chat ID (env var)
- `PORT` — Web server port, set to 5000 for Replit (env var)

The `config.env` file is kept as a local fallback only and is excluded from version control via `.gitignore`.

## Deployment

- Workflow: `python3 -m tcbot`
- Port 5000 exposed as the health-check / keep-alive endpoint
- Deployment target: **autoscale**, run command: `python3 -m tcbot`
