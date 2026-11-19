import os
import tempfile
import unittest

from helpers import VALID, RepoTestCase, join, write
from sdd_core import find_skill, in_skills_dir, lint_skill, list_skills, project_root


class ProjectRootTest(RepoTestCase):
    def test_root_of_existing_file(self):
        write(self.repo, "src/a.py", "x")
        self.assertEqual(project_root(join(self.repo, "src/a.py")), self.repo)

    def test_root_of_file_in_missing_directories(self):
        self.assertEqual(project_root(join(self.repo, "new/deep/dir/a.py")), self.repo)

    def test_none_outside_git(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertIsNone(project_root(join(d, "a.py")))

    def test_git_failure_is_an_error_not_no_repository(self):
        saved = os.environ["PATH"]
        os.environ["PATH"] = "/nonexistent"
        self.addCleanup(os.environ.__setitem__, "PATH", saved)
        with self.assertRaises(RuntimeError):
            project_root(join(self.repo, "a.py"))

    def test_inside_dot_git_is_an_error(self):
        with self.assertRaises(RuntimeError):
            project_root(join(self.repo, ".git/hooks/pre-commit"))

    def test_root_through_symlink(self):
        link = self.repo + "-link"
        os.symlink(self.repo, link)
        self.addCleanup(os.remove, link)
        self.assertEqual(project_root(join(link, "a.py")), self.repo)


class SkillsDirTest(RepoTestCase):
    def test_inside(self):
        self.assertTrue(in_skills_dir(join(self.repo, ".claude/skills/x/SKILL.md"), self.repo))

    def test_nested_inside(self):
        self.assertTrue(in_skills_dir(join(self.repo, "pkg/.claude/skills/x/notes.md"), self.repo))

    def test_outside(self):
        self.assertFalse(in_skills_dir(join(self.repo, "src/skills/x.md"), self.repo))
        self.assertFalse(in_skills_dir(join(self.repo, ".claude/settings.json"), self.repo))

    def test_inside_through_symlink(self):
        link = self.repo + "-link"
        os.symlink(self.repo, link)
        self.addCleanup(os.remove, link)
        self.assertTrue(in_skills_dir(join(link, ".claude/skills/x/SKILL.md"), self.repo))


class SkillDiscoveryTest(RepoTestCase):
    def test_lists_root_and_nested_untracked_skills(self):
        write(self.repo, ".claude/skills/api/SKILL.md", VALID)
        write(self.repo, "pkg/.claude/skills/ui/SKILL.md", VALID)
        write(self.repo, ".claude/skills/empty/notes.md", "x")  # no SKILL.md
        self.assertEqual(
            list_skills(self.repo),
            [join(self.repo, ".claude/skills/api"), join(self.repo, "pkg/.claude/skills/ui")],
        )

    def test_ignored_tree_not_listed(self):
        write(self.repo, ".gitignore", "node_modules/\n")
        write(self.repo, "node_modules/p/.claude/skills/x/SKILL.md", VALID)
        self.assertEqual(list_skills(self.repo), [])

    def test_gitignored_claude_directory_is_still_listed(self):
        write(self.repo, ".gitignore", ".claude/\n")
        write(self.repo, ".claude/skills/api/SKILL.md", VALID)
        self.assertEqual(list_skills(self.repo), [join(self.repo, ".claude/skills/api")])
        self.assertEqual(find_skill(self.repo, "api"), join(self.repo, ".claude/skills/api"))

    def test_find_skill(self):
        write(self.repo, ".claude/skills/api/SKILL.md", VALID)
        self.assertEqual(find_skill(self.repo, "api"), join(self.repo, ".claude/skills/api"))
        self.assertEqual(find_skill(self.repo, "/api"), join(self.repo, ".claude/skills/api"))
        self.assertIsNone(find_skill(self.repo, "other"))
        self.assertIsNone(find_skill(self.repo, "plugin:api"))


class LintTest(RepoTestCase):
    def lint(self, text, extra=None):
        write(self.repo, ".claude/skills/api/SKILL.md", text)
        for name, body in (extra or {}).items():
            write(self.repo, ".claude/skills/api/" + name, body)
        return lint_skill(join(self.repo, ".claude/skills/api"))

    def test_valid_passes(self):
        self.assertEqual(self.lint(VALID), [])

    def test_missing_frontmatter(self):
        self.assertTrue(self.lint("# API\n"))

    def test_empty_description(self):
        self.assertTrue(self.lint("---\nname: api\ndescription:\n---\n"))

    def test_description_too_long(self):
        self.assertTrue(self.lint("---\nname: api\ndescription: " + "x" * 1025 + "\n---\n"))
        self.assertEqual(self.lint("---\nname: api\ndescription: " + "x" * 1024 + "\n---\n"), [])

    def test_too_many_lines(self):
        self.assertTrue(self.lint(VALID + "line\n" * 500))

    def test_marker_in_skill_md(self):
        problems = self.lint(VALID + "## Steps\nSDD-TODO\n")
        self.assertTrue(any("SDD-TODO" in p for p in problems))

    def test_marker_in_reference_file(self):
        problems = self.lint(VALID, {"detail.md": "SDD-TODO"})
        self.assertTrue(any("detail.md" in p for p in problems))

    def test_frontmatter_variants_pass(self):
        self.assertEqual(self.lint(VALID.replace("\n", "\r\n")), [])
        self.assertEqual(self.lint("﻿" + VALID), [])
        self.assertEqual(self.lint('---\nname: api\ndescription: "Use when changing the API."\n---\n'), [])
        self.assertEqual(self.lint("---\nname: api\ndescription: >\n  Use when changing\n  the API.\n---\n"), [])


if __name__ == "__main__":
    unittest.main()
