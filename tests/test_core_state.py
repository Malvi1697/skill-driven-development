import os
import shutil
import tempfile
import unittest

from helpers import join
from sdd_core import add_skill, cleanup_old, load_state, save_snapshot, save_state, take_snapshot, unlocked

EMPTY = {"skills": [], "edits_since_review": False, "unskilled": {}}


class StateTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.dir)

    def test_missing_is_empty(self):
        self.assertEqual(load_state(self.dir, "s1"), EMPTY)

    def test_round_trip(self):
        st = load_state(self.dir, "s1")
        add_skill(st, "/r", "api")
        add_skill(st, "/r", "api")
        st["edits_since_review"] = True
        save_state(self.dir, "s1", st)
        self.assertEqual(
            load_state(self.dir, "s1"),
            {"skills": [{"root": "/r", "name": "api"}], "edits_since_review": True, "unskilled": {}},
        )

    def test_unskilled_round_trip_and_validation(self):
        st = load_state(self.dir, "s1")
        st["unskilled"] = {"/r": ["a.py", "b.py"]}
        save_state(self.dir, "s1", st)
        self.assertEqual(load_state(self.dir, "s1")["unskilled"], {"/r": ["a.py", "b.py"]})
        with open(join(self.dir, "sessions", "s1.json"), "w") as f:
            f.write('{"skills": [], "unskilled": {"/r": "oops", "/q": ["ok", 5]}}')
        self.assertEqual(load_state(self.dir, "s1")["unskilled"], {"/q": ["ok"]})

    def test_snapshot_is_stored_once_per_tool_call(self):
        save_snapshot(self.dir, "s1", "toolu_1", {"root": "/r", "files": {"a": [1, 2]}})
        self.assertEqual(take_snapshot(self.dir, "s1", "toolu_1"), {"root": "/r", "files": {"a": [1, 2]}})
        self.assertIsNone(take_snapshot(self.dir, "s1", "toolu_1"))
        self.assertIsNone(take_snapshot(self.dir, "s1", "../../evil"))

    def test_old_files_are_cleaned_up(self):
        save_state(self.dir, "old", dict(EMPTY))
        save_state(self.dir, "new", dict(EMPTY))
        old = join(self.dir, "sessions", "old.json")
        os.utime(old, (0, 0))
        cleanup_old(self.dir)
        self.assertEqual(os.listdir(join(self.dir, "sessions")), ["new.json"])
        cleanup_old(join(self.dir, "missing"))  # no directory: no error

    def test_corrupt_and_empty_files_are_empty_state(self):
        os.makedirs(join(self.dir, "sessions"))
        for content in ("", "{not json", "[]", '{"skills": 5}'):
            with open(join(self.dir, "sessions", "s1.json"), "w") as f:
                f.write(content)
            self.assertEqual(load_state(self.dir, "s1"), EMPTY, content)

    def test_session_id_cannot_escape_directory(self):
        save_state(self.dir, "../../evil", dict(EMPTY))
        self.assertEqual(os.listdir(self.dir), ["sessions"])
        self.assertEqual(len(os.listdir(join(self.dir, "sessions"))), 1)

    def test_no_temp_files_left(self):
        save_state(self.dir, "s1", dict(EMPTY))
        self.assertEqual(os.listdir(join(self.dir, "sessions")), ["s1.json"])

    def test_unlocked_is_per_root(self):
        st = load_state(self.dir, "s1")
        add_skill(st, "/a", "api")
        self.assertTrue(unlocked(st, "/a"))
        self.assertFalse(unlocked(st, "/b"))


if __name__ == "__main__":
    unittest.main()
