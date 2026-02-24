"""MCP prompts — reusable task templates for Coda operations."""

from __future__ import annotations

from pathlib import Path
from string import Template
from typing import Literal

from fastmcp.prompts.prompt import Message

from . import mcp
from ._helpers import _load_file

_PROMPTS_DIR = str(Path(__file__).resolve().parent.parent / "resources" / "prompts")


def _load_prompt(filename: str) -> str:
    """Load a prompt markdown file from the prompts directory."""
    return _load_file(_PROMPTS_DIR, filename)


def _render(filename: str, **kwargs: str) -> str:
    """Load a prompt template and substitute variables safely.

    Uses string.Template ($var) instead of str.format({var}) to avoid
    KeyError when parameter values contain curly braces.
    """
    return Template(_load_prompt(filename)).safe_substitute(kwargs)


@mcp.prompt(tags={"coda", "docs"})
def analyze_doc_structure(doc_id: str) -> list[Message]:
    """Analyze a Coda doc's page hierarchy, tables, and organization."""
    text = _render("analyze-doc-structure.md", doc_id=doc_id)
    return [
        Message(role="user", content=text),
        Message(
            role="assistant",
            content=(
                f"I'll analyze the structure of doc {doc_id}. "
                "Let me start by listing its pages and tables."
            ),
        ),
    ]


@mcp.prompt(tags={"coda", "tables"})
def design_table_schema(description: str) -> list[Message]:
    """Design a Coda table schema from a natural language description."""
    text = _render("design-table-schema.md", description=description)
    return [
        Message(role="user", content=text),
        Message(
            role="assistant",
            content=(
                "I'll design a table schema based on that description. "
                "Let me identify the entities and their relationships."
            ),
        ),
    ]


@mcp.prompt(tags={"coda", "migration"})
def migrate_spreadsheet(
    doc_id: str,
    source_format: Literal["csv", "excel", "sheets"] = "csv",
) -> list[Message]:
    """Guide for migrating spreadsheet data into Coda tables."""
    text = _render("migrate-spreadsheet.md", doc_id=doc_id, source_format=source_format)
    return [
        Message(role="user", content=text),
        Message(
            role="assistant",
            content=(
                f"I'll help migrate {source_format} data into doc {doc_id}. "
                "Let me check the target doc's existing tables first."
            ),
        ),
    ]


@mcp.prompt(tags={"coda", "automations"})
def setup_automation(
    doc_id: str,
    trigger_type: Literal["webhook", "button", "time"] = "webhook",
) -> list[Message]:
    """Set up an automation with proper payload design and error handling."""
    text = _render("setup-automation.md", doc_id=doc_id, trigger_type=trigger_type)
    return [
        Message(role="user", content=text),
        Message(
            role="assistant",
            content=(
                f"I'll help set up a {trigger_type}-triggered automation "
                f"in doc {doc_id}. Let me review the doc's current setup."
            ),
        ),
    ]


@mcp.prompt(tags={"coda", "permissions"})
def audit_permissions(doc_id: str) -> list[Message]:
    """Audit sharing and permissions on a Coda doc."""
    text = _render("audit-permissions.md", doc_id=doc_id)
    return [
        Message(role="user", content=text),
        Message(
            role="assistant",
            content=(
                f"I'll audit the permissions for doc {doc_id}. "
                "Let me list the current sharing settings."
            ),
        ),
    ]
