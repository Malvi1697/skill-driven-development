import re
import tempfile
import unittest

from helpers import PLUGIN_ROOT, join, read, write
from sdd_core import MARKER, lint_skill, parse_frontmatter

SKILL = join(PLUGIN_ROOT, "skills/skill-first")


class PluginSkillTest(unittest.TestCase):
    def test_frontmatter(self):
        fm = parse_frontmatter(read(join(SKILL, "SKILL.md")))
        self.assertEqual(fm["name"], "skill-first")
        self.assertTrue(0 < len(fm["description"]) <= 1024)
        self.assertNotIn(": ", fm["description"])  # would break real YAML parsers

    def test_size_limits(self):
        self.assertLess(len(read(join(SKILL, "SKILL.md")).splitlines()), 500)
        for name in ("writing-skills.md", "template.md"):
            self.assertLessEqual(len(read(join(SKILL, name)).splitlines()), 100)

    def test_skill_md_links_both_files_and_references_are_one_level_deep(self):
        body = read(join(SKILL, "SKILL.md"))
        self.assertIn("writing-skills.md", body)
        self.assertIn("template.md", body)
        for name in ("writing-skills.md", "template.md"):
            self.assertEqual(re.findall(r"\]\(([^)]+\.md)\)", read(join(SKILL, name))), [])

    def test_template_block_is_an_incomplete_skill_that_becomes_valid_when_filled(self):
        block = re.search(r"```(?:markdown|md)?\n(.*?)```", read(join(SKILL, "template.md")), re.S).group(1)
        for section in ("## Goal", "## Constraints", "## Commands", "## Steps", "## References"):
            self.assertIn(section, block)
        with tempfile.TemporaryDirectory() as d:
            write(d, "x/SKILL.md", block)
            self.assertTrue(any(MARKER in p for p in lint_skill(join(d, "x"))))
            filled = block.replace(MARKER, "filled in")
            filled = re.sub(r"(?m)^name:.*$", "name: x", filled)
            filled = re.sub(r"(?m)^description:.*$", "description: Use when doing x.", filled)
            write(d, "x/SKILL.md", filled)
            self.assertEqual(lint_skill(join(d, "x")), [])


if __name__ == "__main__":
    unittest.main()
