"""Tests for MCP prompts."""

from __future__ import annotations

import pytest

from mcp_coda.servers.prompts import (
    _PROMPTS_DIR,
    _load_prompt,
    analyze_doc_structure,
    audit_permissions,
    design_table_schema,
    migrate_spreadsheet,
    setup_automation,
)


def _unwrap_prompt(obj):
    """Extract raw function from a FastMCP prompt wrapper."""
    if hasattr(obj, "fn"):
        return obj.fn
    return obj


def _text(message) -> str:
    """Extract text string from a Message's content (str or TextContent)."""
    c = message.content
    if isinstance(c, str):
        return c
    # TextContent or similar — has a .text attribute
    return c.text


analyze_doc_structure_fn = _unwrap_prompt(analyze_doc_structure)
design_table_schema_fn = _unwrap_prompt(design_table_schema)
migrate_spreadsheet_fn = _unwrap_prompt(migrate_spreadsheet)
setup_automation_fn = _unwrap_prompt(setup_automation)
audit_permissions_fn = _unwrap_prompt(audit_permissions)


class TestLoadPrompt:
    def test_loads_existing_prompt(self) -> None:
        content = _load_prompt("analyze-doc-structure.md")
        assert "Analyze" in content
        assert len(content) > 50

    def test_rejects_path_traversal(self) -> None:
        with pytest.raises(ValueError, match="Invalid prompt filename"):
            _load_prompt("../../pyproject.toml")

    def test_rejects_backslash(self) -> None:
        with pytest.raises(ValueError, match="Invalid prompt filename"):
            _load_prompt("..\\..\\pyproject.toml")

    def test_missing_file_raises(self) -> None:
        with pytest.raises(FileNotFoundError):
            _load_prompt("nonexistent.md")


class TestPromptsDir:
    def test_prompts_dir_exists(self) -> None:
        assert _PROMPTS_DIR.is_dir()

    def test_all_prompt_files_exist(self) -> None:
        expected = [
            "analyze-doc-structure.md",
            "design-table-schema.md",
            "migrate-spreadsheet.md",
            "setup-automation.md",
            "audit-permissions.md",
        ]
        for filename in expected:
            assert (_PROMPTS_DIR / filename).is_file(), f"Missing: {filename}"


class TestAnalyzeDocStructure:
    def test_returns_messages(self) -> None:
        messages = analyze_doc_structure_fn(doc_id="doc123")
        assert len(messages) == 2
        assert messages[0].role == "user"
        assert messages[1].role == "assistant"

    def test_interpolates_doc_id(self) -> None:
        messages = analyze_doc_structure_fn(doc_id="myDoc42")
        assert "myDoc42" in _text(messages[0])


class TestDesignTableSchema:
    def test_returns_messages(self) -> None:
        messages = design_table_schema_fn(description="A task tracker with projects")
        assert len(messages) == 2
        assert messages[0].role == "user"
        assert messages[1].role == "assistant"

    def test_interpolates_description(self) -> None:
        messages = design_table_schema_fn(description="inventory management system")
        assert "inventory management system" in _text(messages[0])


class TestMigrateSpreadsheet:
    def test_returns_messages_default_format(self) -> None:
        messages = migrate_spreadsheet_fn(doc_id="doc1")
        assert len(messages) == 2
        assert "csv" in _text(messages[0])

    def test_respects_source_format(self) -> None:
        messages = migrate_spreadsheet_fn(doc_id="doc1", source_format="excel")
        assert "excel" in _text(messages[0])
        assert "excel" in _text(messages[1])


class TestSetupAutomation:
    def test_returns_messages_default_trigger(self) -> None:
        messages = setup_automation_fn(doc_id="doc1")
        assert len(messages) == 2
        assert "webhook" in _text(messages[0])

    def test_respects_trigger_type(self) -> None:
        messages = setup_automation_fn(doc_id="doc1", trigger_type="button")
        assert "button" in _text(messages[0])
        assert "button" in _text(messages[1])


class TestAuditPermissions:
    def test_returns_messages(self) -> None:
        messages = audit_permissions_fn(doc_id="docABC")
        assert len(messages) == 2
        assert messages[0].role == "user"
        assert messages[1].role == "assistant"

    def test_interpolates_doc_id(self) -> None:
        messages = audit_permissions_fn(doc_id="docXYZ")
        assert "docXYZ" in _text(messages[0])
