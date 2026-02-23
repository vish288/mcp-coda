"""Tests for Pydantic response models."""

from __future__ import annotations

from mcp_coda.models.base import MutationStatus, PaginatedResponse
from mcp_coda.models.docs import Doc, DocSize
from mcp_coda.models.folders import Folder
from mcp_coda.models.formulas import Formula
from mcp_coda.models.pages import Page, PageContent
from mcp_coda.models.permissions import AclSettings, Permission, Principal, SharingMetadata
from mcp_coda.models.rows import Row
from mcp_coda.models.tables import Column, Table


class TestPaginatedResponse:
    def test_defaults(self) -> None:
        resp = PaginatedResponse[dict]()
        assert resp.items == []
        assert resp.has_more is False
        assert resp.next_cursor is None
        assert resp.total_count == 0

    def test_with_data(self) -> None:
        resp = PaginatedResponse[str](
            items=["a", "b"], has_more=True, next_cursor="cur2", total_count=2
        )
        assert len(resp.items) == 2
        assert resp.has_more is True


class TestMutationStatus:
    def test_from_api(self) -> None:
        ms = MutationStatus.model_validate(
            {"completed": True, "requestId": "req1", "warning": None}
        )
        assert ms.completed is True
        assert ms.request_id == "req1"


class TestDoc:
    def test_minimal(self) -> None:
        doc = Doc(id="d1")
        assert doc.id == "d1"
        assert doc.type == "doc"

    def test_full(self) -> None:
        doc = Doc.model_validate(
            {
                "id": "d1",
                "name": "My Doc",
                "browserLink": "https://coda.io/d/d1",
                "owner": "user@example.com",
                "docSize": {"totalRowCount": 100, "pageCount": 5},
            }
        )
        assert doc.browser_link == "https://coda.io/d/d1"
        assert doc.doc_size is not None
        assert doc.doc_size.total_row_count == 100


class TestDocSize:
    def test_defaults(self) -> None:
        ds = DocSize()
        assert ds.total_row_count == 0
        assert ds.over_api_size_limit is False


class TestPage:
    def test_from_api(self) -> None:
        page = Page.model_validate(
            {"id": "p1", "name": "Home", "browserLink": "https://coda.io/d/d1/Home"}
        )
        assert page.name == "Home"
        assert page.browser_link is not None


class TestPageContent:
    def test_defaults(self) -> None:
        pc = PageContent()
        assert pc.content == ""
        assert pc.content_format == "html"


class TestTable:
    def test_from_api(self) -> None:
        t = Table.model_validate(
            {"id": "t1", "name": "Tasks", "rowCount": 42, "tableType": "table"}
        )
        assert t.row_count == 42
        assert t.table_type == "table"


class TestColumn:
    def test_from_api(self) -> None:
        c = Column.model_validate(
            {"id": "c1", "name": "Status", "display": True, "calculated": False}
        )
        assert c.display is True


class TestRow:
    def test_from_api(self) -> None:
        r = Row.model_validate({"id": "r1", "name": "Row 1", "values": {"Status": "Active"}})
        assert r.values["Status"] == "Active"


class TestFormula:
    def test_from_api(self) -> None:
        f = Formula.model_validate({"id": "f1", "name": "Total", "value": 42})
        assert f.value == 42


class TestPermission:
    def test_from_api(self) -> None:
        p = Permission.model_validate(
            {
                "id": "perm1",
                "principal": {"type": "email", "email": "user@example.com"},
                "access": "write",
            }
        )
        assert p.principal is not None
        assert p.principal.email == "user@example.com"


class TestPrincipal:
    def test_email(self) -> None:
        p = Principal(type="email", email="user@example.com")
        assert p.email == "user@example.com"

    def test_domain(self) -> None:
        p = Principal(type="domain", domain="example.com")
        assert p.domain == "example.com"


class TestSharingMetadata:
    def test_from_api(self) -> None:
        sm = SharingMetadata.model_validate({"canShare": True, "canShareWithOrg": False})
        assert sm.can_share is True


class TestAclSettings:
    def test_from_api(self) -> None:
        acl = AclSettings.model_validate(
            {"allowEditorsToChangePermissions": True, "allowCopying": False}
        )
        assert acl.allow_editors_to_change_permissions is True
        assert acl.allow_copying is False


class TestFolder:
    def test_from_api(self) -> None:
        f = Folder.model_validate({"id": "fl1", "name": "Projects", "parentFolderId": "fl0"})
        assert f.parent_folder_id == "fl0"
