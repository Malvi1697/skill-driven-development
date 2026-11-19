import os
import subprocess

from helpers import VALID, RepoTestCase, join, write
from sdd_core import changed_paths, snapshot


class SnapshotTest(RepoTestCase):
    def setUp(self):
        super().setUp()
        write(self.repo, "tracked.txt", "one\n")
        subprocess.run(["git", "-C", self.repo, "add", "-A"], check=True)
        subprocess.run(["git", "-C", self.repo, "-c", "user.email=t@example.invalid", "-c", "user.name=t",
                        "commit", "-q", "-m", "init"], check=True)

    def changed(self, action):
        before = snapshot(self.repo)
        action()
        return changed_paths(before, snapshot(self.repo))

    def test_no_change(self):
        self.assertEqual(self.changed(lambda: None), [])

    def test_modified_tracked_file(self):
        self.assertEqual(self.changed(lambda: write(self.repo, "tracked.txt", "one two\n")), ["tracked.txt"])

    def test_modified_again_while_already_dirty(self):
        write(self.repo, "tracked.txt", "one two\n")
        self.assertEqual(self.changed(lambda: write(self.repo, "tracked.txt", "one two three\n")), ["tracked.txt"])

    def test_new_untracked_file_in_new_directory(self):
        self.assertEqual(self.changed(lambda: write(self.repo, "src/new/a.py", "x")), ["src/new/a.py"])

    def test_deleted_file(self):
        self.assertEqual(self.changed(lambda: os.remove(join(self.repo, "tracked.txt"))), ["tracked.txt"])

    def test_staging_is_not_a_change(self):
        write(self.repo, "tracked.txt", "one two\n")
        self.assertEqual(self.changed(
            lambda: subprocess.run(["git", "-C", self.repo, "add", "-A"], check=True)), [])

    def test_committing_is_not_a_change(self):
        write(self.repo, "tracked.txt", "one two\n")
        self.assertEqual(self.changed(lambda: subprocess.run(
            ["git", "-C", self.repo, "-c", "user.email=t@example.invalid", "-c", "user.name=t",
             "commit", "-q", "-am", "x"], check=True)), [])

    def test_skill_files_are_left_out(self):
        self.assertEqual(self.changed(lambda: write(self.repo, ".claude/skills/api/SKILL.md", VALID)), [])
        self.assertEqual(self.changed(lambda: write(self.repo, "pkg/.claude/skills/ui/SKILL.md", VALID)), [])

    def test_ignored_files_are_left_out(self):
        write(self.repo, ".gitignore", "build/\n")
        self.assertEqual(self.changed(lambda: write(self.repo, "build/out.bin", "x")), [])

    def test_file_name_with_spaces_and_unicode(self):
        self.assertEqual(self.changed(lambda: write(self.repo, "docs/můj soubor.md", "x")), ["docs/můj soubor.md"])
