"""Locked read-only: the deployer-set MCP_READ_ONLY switch.

A truthy MCP_READ_ONLY or the per-server CODA_READ_ONLY alias (or --read-only,
which writes the alias) locks the server read-only for the process. The lock hides
every write tool and write-workflow prompt from tools/list and prompts/list, so a
client cannot call or re-enable them; the ``_check_write`` guard stays as defence
in depth. A value fails closed: anything not recognised as falsy locks; a falsy
value never unlocks — it is the default.
"""

from __future__ import annotations

import ast
import logging
import re
from pathlib import Path
from types import SimpleNamespace

import pytest
from click.testing import CliRunner
from fastmcp import Client

from mcp_coda import main
from mcp_coda.config import CodaConfig
from mcp_coda.exceptions import CodaWriteDisabledError
from mcp_coda.servers import _lock_read_only, mcp
from mcp_coda.servers._helpers import _check_write, _err

from .test_tool_contract import WRITE_ROWS

_SERVERS_DIR = Path(__file__).resolve().parents[2] / "src" / "mcp_coda" / "servers"
_SRC_DIR = Path(__file__).resolve().parents[2] / "src"
_CONFIG_LOGGER = "mcp_coda.config"
_LOCK_LOGGER = "mcp_coda.servers"


def _write_decorated_names() -> set[str]:
    """Tool names wrapped by ``@tool_result(write=True)``, read from source — the write
    set by its most direct definition (the read-only guard decorator)."""
    names: set[str] = set()
    for path in _SERVERS_DIR.glob("*.py"):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if not isinstance(node, ast.AsyncFunctionDef):
                continue
            for dec in node.decorator_list:
                if (
                    isinstance(dec, ast.Call)
                    and isinstance(dec.func, ast.Name)
                    and dec.func.id == "tool_result"
                    and any(
                        kw.arg == "write"
                        and isinstance(kw.value, ast.Constant)
                        and kw.value.value is True
                        for kw in dec.keywords
                    )
                ):
                    names.add(node.name)
    return names


def _clear_read_only(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("MCP_READ_ONLY", raising=False)
    monkeypatch.delenv("CODA_READ_ONLY", raising=False)


@pytest.fixture
def lock_mcp():
    """Lock the shared ``mcp`` in-process, yielding the ``_lock_read_only`` caller.

    Restores visibility (truncate the appended transforms) and instructions afterwards so
    the module-level ``mcp`` is clean for other tests — the lock keys its idempotency off
    the restored instructions sentence, so there is no separate flag to reset.
    """
    tx = len(mcp._transforms)
    instructions = mcp.instructions

    def lock(**kwargs) -> object:
        _lock_read_only(mcp, **kwargs)
        return mcp

    try:
        yield lock
    finally:
        del mcp._transforms[tx:]
        mcp.instructions = instructions


# ── config: OR semantics, fail-closed ─────────────────────────────────


def test_mcp_read_only_env_locks(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_read_only(monkeypatch)
    monkeypatch.setenv("MCP_READ_ONLY", "true")
    assert CodaConfig.from_env().read_only is True


# (value, expected read_only) — stripped and case-insensitive; anything not falsy locks.
_RO_VALUES = [
    ("true", True),
    ("1", True),
    ("yes", True),
    ("on", True),
    ("TRUE", True),
    ("  true  ", True),  # stripped
    ("false", False),
    ("0", False),
    ("no", False),
    ("off", False),
    ("", False),  # explicitly empty is the default
    ("  ", False),  # whitespace strips to empty
    ("maybe", True),  # unrecognised non-empty fails closed to locked
    ("2", True),
    ("enabled", True),
]


@pytest.mark.parametrize(
    ("value", "expected"), _RO_VALUES, ids=[v[0] or "empty" for v in _RO_VALUES]
)
def test_read_only_value_table(monkeypatch: pytest.MonkeyPatch, value: str, expected: bool) -> None:
    _clear_read_only(monkeypatch)
    monkeypatch.setenv("MCP_READ_ONLY", value)
    assert CodaConfig.from_env().read_only is expected


def test_unrecognised_value_fails_closed(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """An unrecognised value locks and warns, naming the source and the value."""
    _clear_read_only(monkeypatch)
    monkeypatch.setenv("MCP_READ_ONLY", "maybe")
    with caplog.at_level(logging.WARNING, logger=_CONFIG_LOGGER):
        config = CodaConfig.from_env()
    assert config.read_only is True
    assert any(
        "unrecognised" in r.message and "MCP_READ_ONLY" in r.message and "maybe" in r.message
        for r in caplog.records
    )


def test_alias_false_cannot_unlock(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    _clear_read_only(monkeypatch)
    monkeypatch.setenv("MCP_READ_ONLY", "true")
    monkeypatch.setenv("CODA_READ_ONLY", "false")
    with caplog.at_level(logging.WARNING, logger=_CONFIG_LOGGER):
        config = CodaConfig.from_env()
    assert config.read_only is True
    assert any("CODA_READ_ONLY" in r.message for r in caplog.records)


def test_mcp_false_cannot_unlock_alias(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    _clear_read_only(monkeypatch)
    monkeypatch.setenv("CODA_READ_ONLY", "true")
    monkeypatch.setenv("MCP_READ_ONLY", "false")
    with caplog.at_level(logging.WARNING, logger=_CONFIG_LOGGER):
        config = CodaConfig.from_env()
    assert config.read_only is True
    assert any("MCP_READ_ONLY" in r.message for r in caplog.records)


def test_no_falsy_warning_when_unlocked(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    _clear_read_only(monkeypatch)
    monkeypatch.setenv("MCP_READ_ONLY", "false")
    with caplog.at_level(logging.WARNING, logger=_CONFIG_LOGGER):
        config = CodaConfig.from_env()
    assert config.read_only is False
    assert caplog.records == []


def test_no_read_only_flag_rejected() -> None:
    """`--no-read-only` does not exist (plain is_flag); click rejects it, exit 2."""
    result = CliRunner().invoke(main, ["--no-read-only"])
    assert result.exit_code == 2
    assert "no such option" in result.output.lower()


# ── lock: real lifespan boot ──────────────────────────────────────────


async def test_real_lifespan_boot_locks(monkeypatch: pytest.MonkeyPatch) -> None:
    """The real lifespan (not the conftest-swapped one) locks when MCP_READ_ONLY=true.

    Booting through a real Client runs ``lifespan`` → ``_lock_read_only``: every write tool
    is absent from the listing and the instructions gain the locked sentence. Snapshot and
    restore ``mcp._transforms`` + ``instructions`` so the boot does not leak the lock into
    later tests that share the module-level ``mcp``.
    """
    monkeypatch.setenv("CODA_API_TOKEN", "test-token")
    monkeypatch.delenv("CODA_READ_ONLY", raising=False)
    monkeypatch.setenv("MCP_READ_ONLY", "true")
    tx = len(mcp._transforms)
    instructions = mcp.instructions
    try:
        async with Client(mcp) as client:
            visible = {t.name for t in await client.list_tools()}
            assert not (visible & _write_decorated_names())
            assert "locked read-only" in (mcp.instructions or "")
    finally:
        del mcp._transforms[tx:]
        mcp.instructions = instructions


# ── lock: hide write tools / prompts ──────────────────────────────────


async def test_locked_lists_no_write_tools(
    readonly_client: tuple[object, object],
) -> None:
    client, _router = readonly_client
    tools = await client.list_tools()
    assert all(t.annotations is None or t.annotations.read_only_hint is not False for t in tools)
    assert not ({t.name for t in tools} & _write_decorated_names())


async def test_hidden_set_equals_write_tag_set_equals_decorator_set(
    readonly_client: tuple[object, object],
) -> None:
    # ``mcp._list_tools()`` is the raw registry (visibility transforms apply only at the
    # client/protocol layer): it gives the universe and the tags; the locked client gives
    # what survives the hide.
    all_tools = await mcp._list_tools()
    tag_set = {t.name for t in all_tools if "write" in t.tags}
    read_only_hint_false = {
        t.name
        for t in all_tools
        if t.annotations is not None and t.annotations.read_only_hint is False
    }
    decorator_set = _write_decorated_names()
    assert tag_set == decorator_set == read_only_hint_false

    client, _router = readonly_client
    visible = {t.name for t in await client.list_tools()}
    hidden = {t.name for t in all_tools} - visible
    assert hidden == tag_set


async def test_locked_hides_write_workflow_prompts(
    readonly_client: tuple[object, object],
) -> None:
    client, _router = readonly_client
    names = {p.name for p in await client.list_prompts()}
    assert "migrate_spreadsheet" not in names
    assert "setup_automation" not in names
    # Read-only workflows stay. audit_permissions only *reads* permissions
    # (coda_list_permissions) and recommends changes, so it is not a write prompt.
    assert "analyze_doc_structure" in names
    assert "design_table_schema" in names
    assert "audit_permissions" in names


async def test_call_hidden_write_tool_is_unknown_tool(
    readonly_client: tuple[object, object],
) -> None:
    client, _router = readonly_client
    result = await client.call_tool("coda_create_doc", {"title": "x"}, raise_on_error=False)
    assert result.is_error is True
    assert "unknown tool" in result.content[0].text.lower()


# ── lock: decorator guard (defence in depth) ──────────────────────────


@pytest.mark.parametrize("row", WRITE_ROWS, ids=[r[0] for r in WRITE_ROWS])
async def test_decorator_guard_refuses_every_write_tool(row: tuple[object, ...]) -> None:
    """Defence in depth: even reaching a hidden write tool's ``fn`` directly (a cached
    client list, a future untagged tool) refuses before any mutation. Call the registered
    ``tool.fn`` — the ``@tool_result(write=True)`` wrapper — with a stub ctx carrying a
    read-only config and assert the refusal envelope and its deployer-owned hint.
    """
    name, args, *_ = row
    tool = {t.name: t for t in await mcp._list_tools()}[name]
    ctx = SimpleNamespace(lifespan_context={"config": CodaConfig(token="t", read_only=True)})

    result = await tool.fn(ctx, **args)

    assert result.is_error is True
    body = result.content[0].text
    assert "read-only" in body
    assert "deployer" in body.lower()


def test_check_write_raises_and_hint_names_read_only() -> None:
    """The guard's two halves directly: ``_check_write`` raises under a read-only config and
    ``_err`` renders the deployer-owned hint naming the env var family. (The parametrized
    test proves the wired path.)"""
    ctx = SimpleNamespace(lifespan_context={"config": CodaConfig(token="t", read_only=True)})
    with pytest.raises(CodaWriteDisabledError):
        _check_write(ctx)
    detail = _err(CodaWriteDisabledError())
    assert "read-only" in detail["hint"]
    assert "deployer" in detail["hint"].lower()
    assert "CODA_READ_ONLY" in detail["error"]


def test_locked_instructions_and_log(lock_mcp, caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.INFO, logger=_LOCK_LOGGER):
        server = lock_mcp(sources=["MCP_READ_ONLY"])
    assert "locked read-only" in (server.instructions or "")
    assert any("LOCKED" in r.message and "MCP_READ_ONLY" in r.message for r in caplog.records)


def test_lock_is_idempotent(lock_mcp) -> None:
    """A re-entered lifespan (tests) must not stack transforms or re-append the suffix."""
    server = lock_mcp(sources=["MCP_READ_ONLY"])
    tx_after_first = len(server._transforms)
    instructions_after_first = server.instructions
    lock_mcp(sources=["MCP_READ_ONLY"])
    assert len(server._transforms) == tx_after_first
    assert server.instructions == instructions_after_first


def test_src_has_no_runtime_toggle_or_unlock() -> None:
    """``src/`` must not re-enable components, mutate the transform list, or clear the lock
    after config is final: no ``.enable(``, ``enable_components``, ``disable_components``,
    ``reset_visibility``, ``add_transform(``, ``._transforms`` write, or ``read_only =
    False``. The lock is one ``disable`` at boot and nothing undoes it.
    """
    banned = (
        r"\.enable\(",
        r"enable_components\(",
        r"disable_components\(",
        r"reset_visibility\(",
        r"add_transform\(",
        r"\._transforms",
        r"read_only\s*=\s*False",
    )
    for path in _SRC_DIR.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        for pattern in banned:
            assert not re.search(pattern, text), f"{pattern} found in {path}"
