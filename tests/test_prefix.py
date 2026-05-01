# © Copyright 2024 - 2026 Transsion Core
# © Copyright 2024 - 2026 Dizzy
# © Copyright 2026 Aveum Apps
"""Tests for the multi-prefix dispatcher in :mod:`tgbot_tcf.utils.prefix`."""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from tcbot.utils import prefixes


@pytest.fixture(autouse=True)
def _clear_registry() -> None:
    prefixes._REGISTRY.clear()


def test_alt_re_accepts_dot_and_bang_prefixes() -> None:
    assert prefixes._ALT_RE.match(".cban target reason here")
    assert prefixes._ALT_RE.match("!cban")
    assert prefixes._ALT_RE.match(".cban@MyBot 1 spam")


def test_alt_re_rejects_slash_prefix() -> None:
    assert prefixes._ALT_RE.match("/cban target") is None


def test_alt_re_rejects_invalid_command_names() -> None:
    assert prefixes._ALT_RE.match(".1bad") is None
    assert prefixes._ALT_RE.match("..nested") is None


async def test_dispatch_routes_to_registered_callback() -> None:
    seen: dict[str, object] = {}

    async def cb(update, context) -> None:
        seen["update"] = update
        seen["args"] = list(context.args)

    prefixes.register_command("cban", cb)
    update = SimpleNamespace(effective_message=SimpleNamespace(text=".cban 42 spam"))
    context = SimpleNamespace(args=[])
    await prefixes.dispatch_alt_prefix(update, context)
    assert seen["args"] == ["42", "spam"]


async def test_dispatch_lowercases_command_name() -> None:
    called: list[str] = []

    async def cb(update, context) -> None:
        called.append("hit")

    prefixes.register_command("cban", cb)
    update = SimpleNamespace(effective_message=SimpleNamespace(text="!CBAN"))
    context = SimpleNamespace(args=[])
    await prefixes.dispatch_alt_prefix(update, context)
    assert called == ["hit"]


async def test_dispatch_handles_unknown_command_silently() -> None:
    update = SimpleNamespace(effective_message=SimpleNamespace(text=".unknown"))
    context = SimpleNamespace(args=[])
    await prefixes.dispatch_alt_prefix(update, context)


async def test_dispatch_ignores_messages_without_text() -> None:
    update = SimpleNamespace(effective_message=SimpleNamespace(text=None))
    context = SimpleNamespace(args=[])
    await prefixes.dispatch_alt_prefix(update, context)


async def test_dispatch_swallows_callback_exceptions() -> None:
    async def cb(update, context) -> None:
        raise RuntimeError("boom")

    prefixes.register_command("crash", cb)
    update = SimpleNamespace(effective_message=SimpleNamespace(text=".crash"))
    context = SimpleNamespace(args=[])
    # No exception should leak.
    await prefixes.dispatch_alt_prefix(update, context)
