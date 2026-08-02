from unittest.mock import patch
from urllib.error import HTTPError

import integrations


def test_fetch_text_preserves_http_status_for_protocol_fallbacks():
    with patch.object(
        integrations,
        "urlopen",
        side_effect=HTTPError(
            "https://example.test/dream-hook",
            410,
            "Gone",
            {},
            None,
        ),
    ):
        result = integrations.fetch_text(
            "https://example.test/dream-hook"
        )

    assert result == {
        "ok": False,
        "text": "",
        "status_code": 410,
        "error": "HTTP 410",
    }


def test_get_ombre_dream_reads_automatic_candidate_feed():
    with (
        patch.object(integrations, "OB_HOOK_TOKEN", "secret"),
        patch.object(
            integrations,
            "fetch_text",
            return_value={"ok": True, "text": "最近一次梦境"},
        ) as fetch,
    ):
        result = integrations.get_ombre_dream()

    assert result == {
        "ok": True,
        "text": "最近一次梦境",
        "mode": "legacy_hook",
        "endpoint": "dream-hook",
    }
    fetch.assert_called_once_with(
        f"{integrations.OB_BASE_URL}/dream-hook",
        headers={"X-Ombre-Hook-Token": "secret"},
    )


def test_get_ombre_dream_accepts_removed_hook_as_on_demand_mode():
    with (
        patch.object(integrations, "OB_HOOK_TOKEN", "secret"),
        patch.object(
            integrations,
            "fetch_text",
            return_value={
                "ok": False,
                "text": "",
                "status_code": 404,
                "error": "HTTP 404",
            },
        ),
    ):
        result = integrations.get_ombre_dream()

    assert result["ok"] is True
    assert result["text"] == ""
    assert result["mode"] == "on_demand_mcp"
    assert result["endpoint"] == "OB dream tool"
    assert "按需梦境整理" in result["message"]


def test_ombre_dashboard_distinguishes_empty_cache_from_connection_error():
    with (
        patch.object(
            integrations,
            "get_ombre_breath",
            return_value={"ok": True, "text": "浮现记忆"},
        ),
        patch.object(
            integrations,
            "get_ombre_dream",
            return_value={"ok": True, "text": ""},
        ),
    ):
        result = integrations.get_ombre_dashboard()

    assert result["ok"] is True
    assert result["memory_connected"] is True
    assert result["dream_connected"] is True
    assert result["dream_mode"] == "legacy_hook"
    assert result["dream"] == ""
    assert result["errors"] == []


def test_ombre_dashboard_treats_removed_hook_as_supported_on_demand_mode():
    with (
        patch.object(
            integrations,
            "get_ombre_breath",
            return_value={"ok": True, "text": "浮现记忆"},
        ),
        patch.object(
            integrations,
            "get_ombre_dream",
            return_value={
                "ok": True,
                "text": "",
                "mode": "on_demand_mcp",
                "endpoint": "OB dream tool",
                "message": "需要时按需整理",
            },
        ),
    ):
        result = integrations.get_ombre_dashboard()

    assert result["dream_connected"] is True
    assert result["dream_mode"] == "on_demand_mcp"
    assert result["dream_endpoint"] == "OB dream tool"
    assert result["dream_message"] == "需要时按需整理"
    assert result["errors"] == []


def test_ombre_dashboard_reports_real_dream_hook_error():
    with (
        patch.object(
            integrations,
            "get_ombre_breath",
            return_value={"ok": True, "text": "浮现记忆"},
        ),
        patch.object(
            integrations,
            "get_ombre_dream",
            return_value={"ok": False, "text": "", "error": "HTTP 500"},
        ),
    ):
        result = integrations.get_ombre_dashboard()

    assert result["memory_connected"] is True
    assert result["dream_connected"] is False
    assert result["dream_mode"] == "unavailable"
    assert result["errors"] == ["HTTP 500"]
