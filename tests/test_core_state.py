import os
import shutil
import tempfile
import unittest

from helpers import join
from sdd_core import add_skill, load_state, save_state, unlocked

EMPTY = {"skills": [], "edits_since_review": False}


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
            {"skills": [{"root": "/r", "name": "api"}], "edits_since_review": True},
        )

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
