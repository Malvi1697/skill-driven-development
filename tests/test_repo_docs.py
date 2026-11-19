import os
import re
import subprocess
import unittest

from helpers import PLUGIN_ROOT, join, read
from sdd_core import lint_skill, list_skills


class RepoDocsTest(unittest.TestCase):
    def test_contributor_files_exist(self):
        for name in ("AGENTS.md", "CLAUDE.md", "CONTRIBUTING.md", "CODE_OF_CONDUCT.md", "SECURITY.md",
                     "CHANGELOG.md", ".github/PULL_REQUEST_TEMPLATE.md",
                     ".github/ISSUE_TEMPLATE/bug_report.md", ".github/ISSUE_TEMPLATE/feature_request.md",
                     ".github/ISSUE_TEMPLATE/config.yml"):
            self.assertTrue(os.path.isfile(join(PLUGIN_ROOT, name)), name)

    def test_claude_md_imports_agents_md(self):
        self.assertEqual(read(join(PLUGIN_ROOT, "CLAUDE.md")).strip(), "@AGENTS.md")

    def test_agents_md_sections(self):
        text = read(join(PLUGIN_ROOT, "AGENTS.md"))
        for heading in ("What this project is", "If you are an AI agent", "How work is done here",
                        "Commands", "Rules that do not bend", "What will not be accepted", "Pull requests"):
            self.assertIn("## " + heading, text)
        self.assertIn("python3 -m unittest discover -s tests -v", text)

    def test_project_skills_are_complete(self):
        names = [os.path.basename(d) for d in list_skills(PLUGIN_ROOT)]
        self.assertEqual(names, ["changing-hooks", "changing-plugin-docs"])
        for d in list_skills(PLUGIN_ROOT):
            self.assertEqual(lint_skill(d), [], d)

    def test_no_personal_or_internal_information(self):
        out = subprocess.run(["git", "ls-files", "-co", "--exclude-standard"], cwd=PLUGIN_ROOT,
                             capture_output=True, text=True).stdout.split()
        pattern = re.compile(r"/Users/|/Volumes/|[\w.+-]+@[\w-]+\.[\w.]+")
        for rel in out:
            if rel.startswith("tests/"):
                continue
            text = read(join(PLUGIN_ROOT, rel))
            self.assertIsNone(pattern.search(text), rel)


if __name__ == "__main__":
    unittest.main()
