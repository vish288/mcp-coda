"""Tests for MCP resources."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from mcp_coda.config import CodaConfig
from mcp_coda.servers.resources import (
    _RESOURCES_DIR,
    _load,
    coda_api_patterns_rules,
    coda_automations_rules,
    coda_doc_structure_rules,
    coda_permissions_rules,
    coda_table_design_rules,
    folder_organization_guide,
    formula_controls_guide,
    page_content_guide,
    publishing_analytics_guide,
    row_operations_guide,
)
from mcp_coda.servers.resources import (
    doc_schema_resource as _doc_schema_resource,
)
from mcp_coda.servers.resources import (
    docs_resource as _docs_resource,
)


def _unwrap_resource(obj):
    """Extract raw async function from a FunctionResource or plain function.

    FunctionResource.fn is the without_injected_parameters wrapper (strips ctx).
    The original function is in the wrapper's closure. For resources with extra
    params, the closure contains a ValidateCallWrapper that needs further unwrap.
    """
    if not hasattr(obj, "fn"):
        return obj
    closure_fn = obj.fn.__closure__[0].cell_contents
    if hasattr(closure_fn, "__self__"):
        return closure_fn.__self__.function.__closure__[0].cell_contents
    return closure_fn


docs_resource = _unwrap_resource(_docs_resource)
doc_schema_resource = _unwrap_resource(_doc_schema_resource)


def _make_ctx(client_mock: AsyncMock) -> MagicMock:
    ctx = MagicMock()
    ctx.request_context.lifespan_context = {
        "config": CodaConfig(token="tok"),
        "client": client_mock,
    }
    return ctx


class TestDocsResource:
    async def test_returns_doc_list(self) -> None:
        client = AsyncMock()
        client.get = AsyncMock(
            return_value={
                "items": [
                    {
                        "id": "d1",
                        "name": "My Doc",
                        "owner": "user@example.com",
                        "browserLink": "https://coda.io/d/d1",
                        "updatedAt": "2024-01-01",
                    }
                ]
            }
        )
        ctx = _make_ctx(client)
        result = json.loads(await docs_resource(ctx))
        assert len(result) == 1
        assert result[0]["id"] == "d1"
        assert result[0]["name"] == "My Doc"

    async def test_error_handling(self) -> None:
        client = AsyncMock()
        client.get = AsyncMock(side_effect=Exception("connection failed"))
        ctx = _make_ctx(client)
        result = json.loads(await docs_resource(ctx))
        assert "error" in result


class TestDocSchemaResource:
    async def test_returns_schema(self) -> None:
        client = AsyncMock()
        client.get = AsyncMock(
            side_effect=[
                {"items": [{"id": "t1", "name": "Tasks", "tableType": "table", "rowCount": 10}]},
                {
                    "items": [
                        {
                            "id": "c1",
                            "name": "Status",
                            "format": {"type": "select"},
                            "calculated": False,
                            "display": True,
                        }
                    ]
                },
            ]
        )
        ctx = _make_ctx(client)
        result = json.loads(await doc_schema_resource("d1", ctx))
        assert len(result) == 1
        assert result[0]["name"] == "Tasks"
        assert result[0]["columns"][0]["name"] == "Status"
        assert result[0]["columns"][0]["type"] == "select"

    async def test_error_handling(self) -> None:
        client = AsyncMock()
        client.get = AsyncMock(side_effect=Exception("not found"))
        ctx = _make_ctx(client)
        result = json.loads(await doc_schema_resource("bad_id", ctx))
        assert "error" in result


# ════════════════════════════════════════════════════════════════════
# Static resources
# ════════════════════════════════════════════════════════════════════


class TestLoadHelper:
    def test_loads_existing_file(self) -> None:
        content = _load("coda-api-patterns.md")
        assert "Rate Limits" in content
        assert len(content) > 100

    def test_rejects_path_traversal_slash(self) -> None:
        with pytest.raises(ValueError, match="Invalid filename"):
            _load("../pyproject.toml")

    def test_rejects_path_traversal_backslash(self) -> None:
        with pytest.raises(ValueError, match="Invalid filename"):
            _load("..\\pyproject.toml")

    def test_rejects_dotdot(self) -> None:
        with pytest.raises(ValueError, match="Invalid filename"):
            _load("..")

    def test_missing_file_raises(self) -> None:
        with pytest.raises(FileNotFoundError):
            _load("nonexistent.md")


class TestResourcesDir:
    def test_resources_dir_exists(self) -> None:
        assert Path(_RESOURCES_DIR).is_dir()

    def test_all_resource_files_exist(self) -> None:
        expected = [
            "coda-doc-structure.md",
            "coda-table-design.md",
            "coda-permissions.md",
            "coda-automations.md",
            "coda-api-patterns.md",
            "row-operations.md",
            "page-content.md",
            "formula-controls.md",
            "publishing-analytics.md",
            "folder-organization.md",
        ]
        for filename in expected:
            assert (Path(_RESOURCES_DIR) / filename).is_file(), f"Missing: {filename}"


_STATIC_RESOURCES = [
    ("coda_doc_structure_rules", coda_doc_structure_rules, "Doc Structure"),
    ("coda_table_design_rules", coda_table_design_rules, "Table Design"),
    ("coda_permissions_rules", coda_permissions_rules, "Permission Model"),
    ("coda_automations_rules", coda_automations_rules, "Automation Patterns"),
    ("coda_api_patterns_rules", coda_api_patterns_rules, "API Best Practices"),
    ("row_operations_guide", row_operations_guide, "Row Operations"),
    ("page_content_guide", page_content_guide, "Page Content"),
    ("formula_controls_guide", formula_controls_guide, "Formulas"),
    ("publishing_analytics_guide", publishing_analytics_guide, "Publishing"),
    ("folder_organization_guide", folder_organization_guide, "Folder Organization"),
]


class TestStaticResources:
    @pytest.mark.parametrize(
        "name,func,keyword",
        _STATIC_RESOURCES,
        ids=[r[0] for r in _STATIC_RESOURCES],
    )
    def test_returns_markdown_with_expected_content(
        self, name: str, func: object, keyword: str
    ) -> None:
        result = func()
        assert isinstance(result, str)
        assert len(result) > 200
        assert keyword in result
