import unittest

import helpers  # noqa: F401  (puts hooks/ on sys.path)
from sdd_core import is_commit_or_push, is_write_command


class BashTest(unittest.TestCase):
    WRITES = [
        "echo hi > out.txt", "echo hi >> out.txt", "cat a | tee b", "sed -i 's/a/b/' f",
        "sed -i.bak 's/a/b/' f", "perl -pi -e 's/a/b/' f", "rm -rf build", "mv a b", "cp a b",
        "mkdir -p src/x", "touch f", "cd src && rm a", "ls; touch f", "git apply p.diff",
        "git rm f", "git mv a b", "git restore f", "git clean -fd", "truncate -s 0 f",
        "ln -s a b", "chmod +x run.sh", "patch -p1 < p.diff",
        "cd a\nrm x", "FOO=1 rm x", "sudo rm x", "if true; then rm x; fi", "for f in *; do rm $f; done",
        "/bin/rm x", "{ rm x; }", "ls | xargs rm", "ls | xargs -n1 rm", "env A=1 touch f",
    ]
    READS = [
        "ls -la", "cat f", "grep rm notes.txt", "grep -r 'mv ' src", 'echo "a > b"', "echo 'x >> y'",
        "pytest 2>&1", "make test > /dev/null", "cmd 2> /dev/null", "cmd &> /dev/null",
        "git log --oneline | head", "git status", "git diff", "sed -n '1,5p' f",
        "python3 -m unittest", "find . -name '*.py'", "diff <(sort a) <(sort b)", "wc -l < f",
    ]

    def test_writes(self):
        for c in self.WRITES:
            self.assertTrue(is_write_command(c), c)

    def test_reads(self):
        for c in self.READS:
            self.assertFalse(is_write_command(c), c)

    def test_commit_or_push(self):
        for c in ("git commit -m x", "git push", "git -C sub commit -m x", "cd a && git push origin main",
                  "git add .\ngit commit -m x", "GIT_EDITOR=true git commit", "/usr/bin/git push",
                  "git -c user.name=x commit -m y", "git --no-pager commit"):
            self.assertTrue(is_commit_or_push(c), c)
        for c in ("git status", "git log", "echo commit", "git --no-pager log --grep commit",
                  "git commit-graph write", "git log\necho push"):
            self.assertFalse(is_commit_or_push(c), c)


if __name__ == "__main__":
    unittest.main()
