# © Copyright 2024 - 2026 Transsion Core
# © Copyright 2024 - 2026 Dizzy
# © Copyright 2026 Aveum Apps
"""Build command filters that match /, !, and . prefixes."""
from __future__ import annotations

import os
import re

from telegram.ext import filters


def _get_prefixes() -> list[str]:
    raw = os.getenv("PREFIXES", "/!.")
    return list(raw.strip())


def build_prefixed_filters(command: str) -> filters.BaseFilter:
    """Return a filter matching <prefix>command in any affiliated group or DM."""
    prefixes = _get_prefixes()
    pattern = r"^[" + re.escape("".join(prefixes)) + r"]" + re.escape(command) + r"(?:@\w+)?(?:\s|$)"
    return filters.Regex(re.compile(pattern, re.IGNORECASE))
