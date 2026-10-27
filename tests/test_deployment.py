from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class DeploymentTests(unittest.TestCase):
    def test_aliyun_script_protects_migrated_state(self):
        script = (
            ROOT / "scripts" / "deploy-aliyun.sh"
        ).read_text(encoding="utf-8")

        self.assertIn(
            "ALLOW_EMPTY_EVENTIDE_DATA:-0",
            script,
        )
        self.assertIn(
            "$DATA_DIR/eventide_state.json",
            script,
        )

    def test_aliyun_script_uses_internal_service_network(self):
        script = (
            ROOT / "scripts" / "deploy-aliyun.sh"
        ).read_text(encoding="utf-8")

        self.assertIn(
            "EMOTION_BASE_URL=http://emotion:3000",
            script,
        )
        self.assertIn(
            "OB_BASE_URL=http://ombre-brain:8000",
            script,
        )
        self.assertIn(
            "EVENTIDE_LEGACY_PUBLIC_HOST=eventidemcp.zeabur.app",
            script,
        )

    def test_aliyun_script_validates_proxy_and_health(self):
        script = (
            ROOT / "scripts" / "deploy-aliyun.sh"
        ).read_text(encoding="utf-8")

        self.assertIn("CADDY_BACKUP", script)
        self.assertIn("caddy validate", script)
        self.assertIn("caddy reload", script)
        self.assertIn("State.Health.Status", script)


if __name__ == "__main__":
    unittest.main()
