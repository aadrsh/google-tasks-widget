import pytest
from mcp_server import validate_account, get_accounts

def test_validate_account_valid(monkeypatch):
    monkeypatch.setattr("mcp_server.list_accounts", lambda: ["work", "personal"])
    # Should complete without error
    validate_account("work")

def test_validate_account_path_traversal(monkeypatch):
    monkeypatch.setattr("mcp_server.list_accounts", lambda: ["work", "personal"])
    with pytest.raises(ValueError, match="is not configured or authenticated"):
        validate_account("../../../etc/passwd")

def test_validate_account_nonexistent(monkeypatch):
    monkeypatch.setattr("mcp_server.list_accounts", lambda: ["work", "personal"])
    with pytest.raises(ValueError, match="is not configured or authenticated"):
        validate_account("hacker_account")

def test_get_accounts_tool(monkeypatch):
    monkeypatch.setattr("mcp_server.list_accounts", lambda: ["work", "personal"])
    res = get_accounts()
    assert '"work"' in res
    assert '"personal"' in res
