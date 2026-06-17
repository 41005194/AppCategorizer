import io
import contextlib
import unittest
from unittest import mock

from appcategorizer import cli


class DummyStatus:
    def __init__(self):
        self.messages = []

    def update(self, msg: str) -> None:
        self.messages.append(msg)


class DummyConsole:
    def __init__(self):
        self.status_obj = DummyStatus()

    @contextlib.contextmanager
    def status(self, *args, **kwargs):
        yield self.status_obj


class CliTests(unittest.TestCase):
    def test_main_sync_updates_status_and_prints_category_to_stdout(self):
        class FakeCategorizer:
            def __init__(self, on_progress=None):
                self.on_progress = on_progress

            async def resolve_and_classify(self, app_name, **kwargs):
                assert app_name == "Firefox"
                if self.on_progress:
                    self.on_progress("ignored progress")
                return "Internet Browsers"

        stdout = io.StringIO()
        console = DummyConsole()
        with (
            mock.patch.object(cli, "Categorizer", FakeCategorizer),
            mock.patch.object(cli, "setup_logger", lambda verbose: None),
            mock.patch.object(cli, "console", console),
            mock.patch("sys.stdout", new=stdout),
        ):
            cli.main_sync(["Firefox"])

        self.assertEqual(stdout.getvalue(), "Internet Browsers\n")
        self.assertEqual(console.status_obj.messages, ["[bold cyan]ignored progress"])

    def test_main_sync_forwards_cloud_llm_arguments(self):
        captured = {}

        class FakeCategorizer:
            def __init__(self, on_progress=None):
                self.on_progress = on_progress

            async def resolve_and_classify(self, app_name, **kwargs):
                captured["app_name"] = app_name
                captured.update(kwargs)
                return "Productivity Tools"

        stdout = io.StringIO()
        console = DummyConsole()
        with (
            mock.patch.object(cli, "Categorizer", FakeCategorizer),
            mock.patch.object(cli, "setup_logger", lambda verbose: None),
            mock.patch.object(cli, "console", console),
            mock.patch("sys.stdout", new=stdout),
        ):
            cli.main_sync(
                [
                    "Slack",
                    "--mode", "cloud_llm",
                    "--llm-provider", "openai",
                    "--llm-model", "gpt-4o",
                    "--api-key", "sk-test",
                    "--local-model", "custom-model",
                ]
            )

        self.assertEqual(stdout.getvalue(), "Productivity Tools\n")
        self.assertEqual(captured["app_name"], "Slack")
        self.assertEqual(captured["analysis_mode"], "cloud_llm")
        self.assertEqual(captured["llm_provider"], "openai")
        self.assertEqual(captured["llm_model"], "gpt-4o")
        self.assertEqual(captured["llm_api_key"], "sk-test")
        self.assertEqual(captured["local_model_name"], "custom-model")


if __name__ == "__main__":
    unittest.main()
