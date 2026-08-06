import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "skills" / "track-ai-visibility" / "scripts" / "visibility_store.py"


class VisibilityStoreTest(unittest.TestCase):
    def run_store(self, root: Path, *arguments: str) -> dict:
        command = [sys.executable, str(SCRIPT), *arguments, "--root", str(root)]
        result = subprocess.run(command, check=True, capture_output=True, text=True)
        return json.loads(result.stdout)

    def test_end_to_end_local_workflow(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)

            initialized = self.run_store(
                root,
                "init",
                "--brand",
                "Example Brand",
                "--domain",
                "example.com",
                "--project",
                "Visibility test",
                "--prompt",
                "best workflow newsletter",
            )
            self.assertEqual(initialized["status"], "initialized")

            self.run_store(root, "add-prompts", "--prompt", "workflow newsletter alternatives")

            observations = root / "observations.json"
            observations.write_text(
                json.dumps(
                    [
                        {
                            "prompt_text": "best workflow newsletter",
                            "surface": "test-surface",
                            "brand_mentioned": True,
                            "brand_position": 1,
                            "competitors": [{"name": "Competitor", "position": 2}],
                            "citations": [{"url": "https://example.com/guide"}],
                        }
                    ]
                ),
                encoding="utf-8",
            )
            imported = self.run_store(
                root,
                "import",
                "--kind",
                "observations",
                "--file",
                str(observations),
            )
            self.assertEqual(imported["imported"], 1)

            summary = self.run_store(root, "summary", "--days", "30")
            self.assertEqual(summary["coverage"]["active_prompts"], 2)
            self.assertEqual(summary["coverage"]["covered_prompts"], 1)
            self.assertEqual(summary["visibility"]["visibility_rate_pct"], 100.0)
            self.assertEqual(summary["visibility"]["citation_rate_pct"], 100.0)

            prepared = self.run_store(
                root,
                "prepare-task",
                "--kind",
                "content",
                "--title",
                "Draft comparison page",
            )
            token = prepared["confirmation_token"]
            confirmed = self.run_store(root, "confirm-task", "--token", token)
            repeated = self.run_store(root, "confirm-task", "--token", token)
            self.assertEqual(confirmed["status"], "confirmed")
            self.assertEqual(repeated["status"], "already_confirmed")

            validation = self.run_store(root, "validate")
            self.assertTrue(validation["valid"])


if __name__ == "__main__":
    unittest.main()
