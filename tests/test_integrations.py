from unittest.mock import patch

import integrations


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

    assert result == {"ok": True, "text": "最近一次梦境"}
    fetch.assert_called_once_with(
        f"{integrations.OB_BASE_URL}/dream-hook",
        headers={"X-Ombre-Hook-Token": "secret"},
    )


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
    assert result["dream"] == ""
    assert result["errors"] == []


def test_ombre_dashboard_reports_dream_hook_error():
    with (
        patch.object(
            integrations,
            "get_ombre_breath",
            return_value={"ok": True, "text": "浮现记忆"},
        ),
        patch.object(
            integrations,
            "get_ombre_dream",
            return_value={"ok": False, "text": "", "error": "HTTP 404"},
        ),
    ):
        result = integrations.get_ombre_dashboard()

    assert result["memory_connected"] is True
    assert result["dream_connected"] is False
    assert result["errors"] == ["HTTP 404"]
