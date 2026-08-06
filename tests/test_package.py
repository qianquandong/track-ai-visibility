import json
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SKILL_ROOT = REPO_ROOT / "skills" / "track-ai-visibility"


class PackageLayoutTest(unittest.TestCase):
    def test_required_skill_files_exist(self) -> None:
        for relative_path in (
            "SKILL.md",
            "agents/openai.yaml",
            "references/data-schema.md",
            "references/research-method.md",
            "scripts/visibility_store.py",
        ):
            self.assertTrue((SKILL_ROOT / relative_path).is_file(), relative_path)

    def test_skill_frontmatter(self) -> None:
        skill = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        self.assertTrue(skill.startswith("---\n"))
        self.assertIn("\nname: track-ai-visibility\n", skill)
        self.assertIn("\ndescription:", skill)

    def test_claude_manifests_reference_the_root_plugin(self) -> None:
        plugin = json.loads((REPO_ROOT / ".claude-plugin" / "plugin.json").read_text())
        marketplace = json.loads((REPO_ROOT / ".claude-plugin" / "marketplace.json").read_text())
        self.assertEqual(plugin["name"], "track-ai-visibility")
        self.assertEqual(marketplace["plugins"][0]["name"], plugin["name"])
        self.assertEqual(marketplace["plugins"][0]["source"], ".")


if __name__ == "__main__":
    unittest.main()
