import unittest
from unittest.mock import patch
from urllib.error import HTTPError

import integrations


class IntegrationTests(unittest.TestCase):
    def test_default_integrations_use_aliyun_domains(self):
        self.assertEqual(
            integrations.EMOTION_BASE_URL,
            "https://emotion.xunzhou.space",
        )
        self.assertEqual(
            integrations.OB_BASE_URL,
            "https://ombre.xunzhou.space",
        )

    def test_fetch_text_preserves_http_status_for_protocol_fallbacks(self):
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

        self.assertEqual(result, {
            "ok": False,
            "text": "",
            "status_code": 410,
            "error": "HTTP 410",
        })

    def test_get_ombre_dream_reads_automatic_candidate_feed(self):
        with (
            patch.object(integrations, "OB_HOOK_TOKEN", "secret"),
            patch.object(
                integrations,
                "fetch_text",
                return_value={"ok": True, "text": "最近一次梦境"},
            ) as fetch,
        ):
            result = integrations.get_ombre_dream()

        self.assertEqual(result, {
            "ok": True,
            "text": "最近一次梦境",
            "mode": "legacy_hook",
            "endpoint": "dream-hook",
        })
        fetch.assert_called_once_with(
            f"{integrations.OB_BASE_URL}/dream-hook",
            headers={"X-Ombre-Hook-Token": "secret"},
        )

    def test_get_ombre_dream_accepts_removed_hook_as_on_demand_mode(self):
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

        self.assertTrue(result["ok"])
        self.assertEqual(result["text"], "")
        self.assertEqual(result["mode"], "on_demand_mcp")
        self.assertEqual(result["endpoint"], "OB dream tool")
        self.assertIn("按需梦境整理", result["message"])

    def test_ombre_dashboard_distinguishes_empty_cache_from_connection_error(self):
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

        self.assertTrue(result["ok"])
        self.assertTrue(result["memory_connected"])
        self.assertTrue(result["dream_connected"])
        self.assertEqual(result["dream_mode"], "legacy_hook")
        self.assertEqual(result["dream"], "")
        self.assertEqual(result["errors"], [])

    def test_ombre_dashboard_treats_removed_hook_as_supported_on_demand_mode(self):
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

        self.assertTrue(result["dream_connected"])
        self.assertEqual(result["dream_mode"], "on_demand_mcp")
        self.assertEqual(result["dream_endpoint"], "OB dream tool")
        self.assertEqual(result["dream_message"], "需要时按需整理")
        self.assertEqual(result["errors"], [])

    def test_ombre_dashboard_reports_real_dream_hook_error(self):
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

        self.assertTrue(result["memory_connected"])
        self.assertFalse(result["dream_connected"])
        self.assertEqual(result["dream_mode"], "unavailable")
        self.assertEqual(result["errors"], ["HTTP 500"])
