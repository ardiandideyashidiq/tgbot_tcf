# © Copyright 2024 - 2026 Transsion Core
# © Copyright 2024 - 2026 Dizzy
# © Copyright 2026 Aveum Apps

import ast
import os
import socket
import sys

from dataclasses import dataclass
from typing import List, Optional, Tuple
from dotenv import load_dotenv, find_dotenv


## Load environment
load_dotenv(find_dotenv("config.env"))


## Helper parsing functions

def parse_list(raw: str) -> List[str]:
    """
    Convert a string like '["/", "!"]' or '/, !' into a list of strings.
    Returns an empty list for empty input.
    """
    if not raw.strip():
        return []

    try:
        parsed = ast.literal_eval(raw)
        if isinstance(parsed, list):
            return [str(item).strip() for item in parsed]
    except (ValueError, SyntaxError):
        pass

    items = raw.strip("[]").split(",")
    return [item.strip().strip("'\"") for item in items if item.strip()]


def _find_free_port() -> int:
    """Bind to port 0 so the OS assigns a free port."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        return s.getsockname()[1]


def parse_port(port_str: str) -> int:
    """
    Resolve a port string to an integer.
    - 'auto' or empty -> find a free system port.
    - numeric string -> convert to int.
    - invalid -> fall back to auto with a warning.
    """
    if not port_str or port_str.lower() == "auto":
        return _find_free_port()
    try:
        return int(port_str)
    except ValueError:
        print(f"Invalid PORT '{port_str}', using auto.", file=sys.stderr)
        return _find_free_port()


def parse_chat_id(raw: str) -> Tuple[int, Optional[int]]:
    """
    Extract chat_id and optional thread_id.
    Accepts "-1001234567890" or "-1001234567890/12".
    """
    if not raw:
        return 0, None
    if "/" in raw:
        chat_str, thread_str = raw.split("/", 1)
        return int(chat_str), int(thread_str)
    return int(raw), None


def _int_from_env(key: str, default: int) -> int:
    """Get int from env, fallback to default with a warning."""
    try:
        return int(os.getenv(key, str(default)))
    except ValueError:
        print(f"Invalid integer for {key}, using {default}.", file=sys.stderr)
        return default


def _env_list(key: str) -> List[str]:
    """Parse a comma-separated env variable into a list of strings."""
    raw = os.getenv(key, "").strip()
    if not raw:
        return []
    return [name.strip() for name in raw.split(",") if name.strip()]


## Configuration dataclass (immutable)

@dataclass(frozen=True)
class Configs:
    """Immutable container for all bot configuration values."""

    bot_token: str
    owner_id: int
    mongodb_uri: str
    db_name: str
    community_name: str
    prefixes: List[str]
    port: str
    main_group: str
    main_channel: str
    proofs: str
    logs: str
    logs_errors: str
    appeals: str
    proof_timeout_seconds: int
    appeal_timeout_seconds: int
    extend_group: str
    album_debounce_seconds: int
    modules_load: List[str]
    modules_no_load: List[str]

    ## Computed properties

    @property
    def port_int(self) -> int:
        """Resolved integer port for web server and keep‑alive."""
        return parse_port(self.port)

    @property
    def main_group_id(self) -> int:
        return int(self.main_group) if self.main_group else 0

    @property
    def main_channel_id(self) -> int:
        return int(self.main_channel) if self.main_channel else 0

    @property
    def extend_group_id(self) -> int:
        return int(self.extend_group) if self.extend_group else 0

    @property
    def logs_id(self) -> int:
        return int(self.logs) if self.logs else 0

    @property
    def proofs_id(self) -> Tuple[int, Optional[int]]:
        return parse_chat_id(self.proofs)

    @property
    def logs_errors_id(self) -> Tuple[int, Optional[int]]:
        return parse_chat_id(self.logs_errors)

    @property
    def appeals_id(self) -> Tuple[int, Optional[int]]:
        return parse_chat_id(self.appeals)

    ## Factory method

    @staticmethod
    def load(env_file: str = "config.env") -> "Configs":
        """
        Load .env and return an immutable Configs instance.
        Raises RuntimeError if BOT_TOKEN is missing.
        """
        load_dotenv(find_dotenv(env_file))

        token = os.getenv("BOT_TOKEN", "").strip()
        if not token:
            raise RuntimeError("BOT_TOKEN is required but not set.")

        owner_str = os.getenv("OWNER_ID", "0").strip()
        try:
            owner_id = int(owner_str)
        except ValueError:
            print(f"OWNER_ID '{owner_str}' invalid, using 0.", file=sys.stderr)
            owner_id = 0

        raw_prefixes = os.getenv("PREFIXES", '["/", "!", "."]')
        prefixes = parse_list(raw_prefixes)
        if not prefixes:
            prefixes = ["/"]

        return Configs(
            bot_token=token,
            owner_id=owner_id,
            mongodb_uri=os.getenv("MONGODB_URI", "").strip(),
            db_name=os.getenv("DB_NAME", "tcbot").strip(),
            community_name=os.getenv("COMMUNITY_NAME", "Bot").strip(),
            prefixes=prefixes,
            port=os.getenv("PORT", "auto").strip(),
            main_group=os.getenv("MAIN_GROUP", "").strip(),
            main_channel=os.getenv("MAIN_CHANNEL", "").strip(),
            proofs=os.getenv("PROOFS", "").strip(),
            logs=os.getenv("LOGS", "").strip(),
            logs_errors=os.getenv("LOGS_ERRORS", "").strip(),
            appeals=os.getenv("APPEALS", "").strip(),
            proof_timeout_seconds=_int_from_env("PROOF_TIMEOUT_SECONDS", 100),
            appeal_timeout_seconds=_int_from_env("APPEAL_TIMEOUT_SECONDS", 600),
            extend_group=os.getenv("EXTEND_GROUP", "").strip(),
            album_debounce_seconds=_int_from_env("ALBUM_DEBOUNCE_SECONDS", 2),
            modules_load=_env_list("MODULES_LOAD"),
            modules_no_load=_env_list("MODULES_NO_LOAD"),
        )


## Singleton instance
configs = Configs.load()