import unittest

import helpers  # noqa: F401  (puts hooks/ on sys.path)
from sdd_core import is_commit_or_push


class CommitOrPushTest(unittest.TestCase):
    def test_commit_or_push(self):
        for c in ("git commit -m x", "git push", "git -C sub commit -m x", "cd a && git push origin main",
                  "git add .\ngit commit -m x", "GIT_EDITOR=true git commit", "/usr/bin/git push",
                  "git -c user.name=x commit -m y", "git --no-pager commit", "sudo git push",
                  "if true; then git commit -m x; fi"):
            self.assertTrue(is_commit_or_push(c), c)
        for c in ("git status", "git log", "echo commit", "git --no-pager log --grep commit",
                  "git commit-graph write", "git log\necho push", 'echo "git commit"'):
            self.assertFalse(is_commit_or_push(c), c)


if __name__ == "__main__":
    unittest.main()
