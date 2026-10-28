import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import dlut_autologin as app


class ConfigurationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.config = self.root / "config.local.json"
        self.cookies = self.root / "cookies.json"
        self.cookies.write_text(json.dumps({"devInfo": "test-device"}), encoding="utf-8")
        self.config.write_text(json.dumps({
            "username": "test-user", "password": "test-password", "cookies_file": "cookies.json"
        }), encoding="utf-8-sig")

    def run_main(self, *arguments):
        with patch("sys.argv", ["dlut_autologin.py", "-i", "172.29.0.100", *arguments]), patch.object(
            app, "login", return_value=(0, "OK")
        ) as login, contextlib.redirect_stdout(io.StringIO()):
            result = app.main()
        self.assertEqual(result, 0)
        return login.call_args.args

    def test_config_credentials_and_relative_cookie_path(self):
        self.assertEqual(self.run_main("--config", str(self.config)), (
            "test-user", "test-password", "172.29.0.100", {"devInfo": "test-device"}
        ))

    def test_explicit_arguments_override_config(self):
        other = self.root / "other.json"
        other.write_text(json.dumps({"devInfo": "override-device"}), encoding="utf-8")
        self.assertEqual(self.run_main(
            "--config", str(self.config), "-u", "override-user", "-p", "override-password",
            "--cookies", str(other)
        ), ("override-user", "override-password", "172.29.0.100", {"devInfo": "override-device"}))

    def test_default_config_resolves_from_script_directory(self):
        with patch.object(app, "__file__", str(self.root / "dlut_autologin.py")):
            self.assertEqual(self.run_main()[0:2], ("test-user", "test-password"))

    def test_no_local_config_preserves_interactive_fallback(self):
        with patch.object(app, "__file__", str(self.root / "empty" / "dlut_autologin.py")):
            self.assertEqual(self.run_main(), (None, None, "172.29.0.100", None))

    def test_invalid_config_rejected_without_exposing_values(self):
        for config in [{"password": ["do-not-log"]}, {"passwrod": "do-not-log"}, ["do-not-log"]]:
            with self.subTest(config=config):
                self.config.write_text(json.dumps(config), encoding="utf-8")
                errors = io.StringIO()
                with patch("sys.argv", ["dlut_autologin.py", "--config", str(self.config)]), patch.object(
                    app, "login"
                ) as login, contextlib.redirect_stderr(errors), self.assertRaises(SystemExit) as raised:
                    app.main()
                self.assertEqual(raised.exception.code, 2)
                self.assertNotIn("do-not-log", errors.getvalue())
                login.assert_not_called()

    def test_missing_explicit_config_rejected_before_login(self):
        with patch("sys.argv", ["dlut_autologin.py", "--config", str(self.root / "missing.json")]), patch.object(
            app, "login"
        ) as login, contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as raised:
            app.main()
        self.assertEqual(raised.exception.code, 2)
        login.assert_not_called()


if __name__ == "__main__":
    unittest.main()
