# Replit Environment — TCF Bot

## Workflow

- **Name:** `Start application`
- **Command:** `python3 -m tcbot`
- Restart after any code or dependency change.

## Port

Flask keepalive runs on port `5000` (configurable via `PORT` in `config.env`).
The bot itself uses long polling — no webhook, no extra port needed.

## Environment Variables

All secrets live in `config.env` (gitignored). Never hardcode values.
See `config.env.example` for the full list of required keys.

Key variables:
| Variable | Description |
|---|---|
| `BOT_TOKEN` | Telegram bot token |
| `OWNER_ID` | Telegram user ID of the federation owner |
| `MONGODB_URI` | MongoDB connection string |
| `DB_NAME` | MongoDB database name (default: `tcbot`) |
| `LOGS` | Log channel chat ID (optionally `chat_id/thread_id`) |
| `PROOFS` | Proof channel chat ID |
| `APPEALS` | Appeal channel chat ID |
| `PROOF_TIMEOUT_SECONDS` | ConversationHandler timeout for ban proof step |
| `APPEAL_TIMEOUT_SECONDS` | ConversationHandler timeout for appeal flow |

## Dependencies

Managed via `pyproject.toml` + `uv.lock`. Install with:
```
pip install -r requirements.txt
```

Core deps: `python-telegram-bot[all]==22.5`, `motor`, `flask`, `python-dotenv`, `apscheduler`

## MongoDB

Motor (async) client. Connection is established in `tcbot/database/mongos.py` via `connect()`,
called during bot startup in `__main__.py`. The client is a module-level singleton.

## Logs

Structured log format: `[HH:MM] [DD-MM-YYYY] | <community_name> | <L> - <module>:<line> - <msg>`

Log level: `INFO` by default. Set `logging.DEBUG` in `utils/logger.py` for verbose output.
Third-party loggers (httpx, telegram, motor, pymongo) are capped at WARNING.
