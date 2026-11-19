"""Shared test helpers: temporary git repositories and file writing."""
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

PLUGIN_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(PLUGIN_ROOT, "hooks"))

join = os.path.join

VALID = "---\nname: api\ndescription: Use when changing the HTTP API layer.\n---\n\n# API\n"


def write(root, relpath, text):
    path = join(root, relpath)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(text)
    return path


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


class RepoTestCase(unittest.TestCase):
    def make_repo(self):
        repo = os.path.realpath(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, repo, True)
        subprocess.run(["git", "init", "-q", repo], check=True)
        return repo

    def setUp(self):
        self.repo = self.make_repo()
