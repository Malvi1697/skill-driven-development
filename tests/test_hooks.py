import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

from helpers import PLUGIN_ROOT, VALID, RepoTestCase, join, write

SCRIPT = join(PLUGIN_ROOT, "hooks", "sdd.py")


class HookTest(RepoTestCase):
    def setUp(self):
        super().setUp()
        self.data = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.data, True)
        write(self.repo, ".claude/skills/api/SKILL.md", VALID)

    def run_raw(self, stdin, **extra_env):
        env = dict(os.environ, CLAUDE_PLUGIN_DATA=self.data, **extra_env)
        result = subprocess.run(
            [sys.executable, SCRIPT], input=stdin, capture_output=True, text=True, env=env
        )
        return result.returncode, result.stdout, result.stderr

    def send(self, event):
        return self.run_raw(json.dumps(dict({"session_id": "s1", "cwd": self.repo}, **event)))

    def edit(self, path):
        return self.send({"hook_event_name": "PreToolUse", "tool_name": "Edit",
                         "tool_input": {"file_path": path}})

    def bash(self, command, tool_use_id="t1"):
        return self.send({"hook_event_name": "PreToolUse", "tool_name": "Bash", "tool_use_id": tool_use_id,
                         "tool_input": {"command": command}})

    def after_bash(self, tool_use_id="t1", failed=False):
        return self.send({"hook_event_name": "PostToolUseFailure" if failed else "PostToolUse",
                         "tool_name": "Bash", "tool_use_id": tool_use_id, "tool_input": {"command": "x"}})

    def shell(self, action, failed=False):
        """A shell command that does `action`: the hook before it, the action, the hook after it."""
        self.assertEqual(self.bash("some command")[0], 0)
        action()
        return self.after_bash(failed=failed)

    def invoke(self, name):
        return self.send({"hook_event_name": "PostToolUse", "tool_name": "Skill",
                         "tool_input": {"skill": name}})

    def stop(self, active=False):
        return self.send({"hook_event_name": "Stop", "stop_hook_active": active})

    def test_edit_denied_without_skill(self):
        code, out, err = self.edit(join(self.repo, "src/a.py"))
        self.assertEqual(code, 2)
        self.assertIn("no project skill is in use", err)

    def test_relative_path_denied_without_skill(self):
        self.assertEqual(self.edit("src/a.py")[0], 2)

    def test_skill_files_always_editable(self):
        self.assertEqual(self.edit(join(self.repo, ".claude/skills/new/SKILL.md"))[0], 0)

    def test_edit_allowed_after_project_skill(self):
        self.invoke("api")
        self.assertEqual(self.edit(join(self.repo, "src/a.py"))[0], 0)

    def test_plugin_and_unknown_skills_do_not_unlock(self):
        self.invoke("some-plugin:helper")
        self.invoke("missing")
        self.assertEqual(self.edit(join(self.repo, "src/a.py"))[0], 2)

    def test_user_invoked_skill_unlocks(self):
        self.send({"hook_event_name": "UserPromptExpansion", "command_name": "api"})
        self.assertEqual(self.edit(join(self.repo, "src/a.py"))[0], 0)

    def test_notebook_edit_gated(self):
        code, _, _ = self.send({"hook_event_name": "PreToolUse", "tool_name": "NotebookEdit",
                               "tool_input": {"notebook_path": join(self.repo, "n.ipynb")}})
        self.assertEqual(code, 2)

    def test_file_outside_any_repo_not_gated(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(self.edit(join(d, "a.txt"))[0], 0)

    def test_skill_does_not_unlock_other_repo(self):
        other = self.make_repo()
        self.invoke("api")
        self.assertEqual(self.edit(join(other, "a.py"))[0], 2)

    def test_shell_command_is_never_refused_before_it_runs(self):
        for command in ("rm -rf build", "curl -s x > /tmp/out.json", "mkdir -p /tmp/probe", "ls -la",
                        "cat <<EOF\na -> b\nEOF", "[[ $a > $b ]]"):
            self.assertEqual(self.bash(command)[0], 0, command)

    def test_shell_change_without_skill_is_reported_and_blocks_commit(self):
        code, out, _ = self.shell(lambda: write(self.repo, "src/a.py", "x"))
        self.assertEqual(code, 0)
        decision = json.loads(out)
        self.assertEqual(decision["decision"], "block")
        self.assertIn("src/a.py", decision["reason"])
        code, _, err = self.bash("git commit -m x", "t2")
        self.assertEqual(code, 2)
        self.assertIn("src/a.py", err)
        stop = json.loads(self.stop()[1])
        self.assertEqual(stop["decision"], "block")
        self.assertIn("src/a.py", stop["reason"])
        self.invoke("api")
        self.assertEqual(self.bash("git commit -m x", "t3")[0], 0)
        review = json.loads(self.stop()[1])
        self.assertIn("api", review["reason"])
        self.assertNotIn("src/a.py", review["reason"])

    def test_undone_shell_change_no_longer_blocks(self):
        self.shell(lambda: write(self.repo, "src/a.py", "x"))
        self.assertEqual(self.bash("git commit -m x", "t2")[0], 2)
        os.remove(join(self.repo, "src/a.py"))
        self.assertEqual(self.bash("git commit -m x", "t3")[0], 0)
        self.assertEqual(self.stop()[1].strip(), "")

    def test_shell_change_is_reported_after_a_failed_command(self):
        _, out, _ = self.shell(lambda: write(self.repo, "src/a.py", "x"), failed=True)
        output = json.loads(out)["hookSpecificOutput"]
        self.assertEqual(output["hookEventName"], "PostToolUseFailure")
        self.assertIn("src/a.py", output["additionalContext"])

    def test_shell_command_without_changes_is_silent(self):
        self.assertEqual(self.shell(lambda: None)[1].strip(), "")
        self.assertEqual(self.bash("git commit -m x", "t2")[0], 0)

    def test_shell_change_to_skill_files_is_silent(self):
        self.assertEqual(self.shell(lambda: write(self.repo, ".claude/skills/new/SKILL.md", VALID))[1].strip(), "")

    def test_shell_change_with_skill_in_use_asks_for_review(self):
        self.invoke("api")
        self.assertEqual(self.shell(lambda: write(self.repo, "src/a.py", "x"))[1].strip(), "")
        self.assertEqual(json.loads(self.stop()[1])["decision"], "block")

    def test_after_hook_without_a_snapshot_is_silent(self):
        code, out, _ = self.after_bash("never-started")
        self.assertEqual((code, out.strip()), (0, ""))

    def test_skill_with_covers_unlocks_only_its_files(self):
        write(self.repo, ".claude/skills/docs/SKILL.md",
              "---\nname: docs\ndescription: Use when editing docs.\nmetadata:\n  covers: docs/**, *.md\n---\n")
        self.invoke("docs")
        self.assertEqual(self.edit(join(self.repo, "docs/guide.txt"))[0], 0)
        self.assertEqual(self.edit(join(self.repo, "README.md"))[0], 0)
        code, _, err = self.edit(join(self.repo, "src/a.py"))
        self.assertEqual(code, 2)
        self.assertIn("not covered", err)
        self.assertIn("docs", err)
        _, out, _ = self.shell(lambda: write(self.repo, "src/b.py", "x"))
        self.assertIn("src/b.py", json.loads(out)["reason"])
        self.invoke("api")  # no covers: unlocks everything
        self.assertEqual(self.edit(join(self.repo, "src/a.py"))[0], 0)
        self.assertEqual(self.bash("git commit -m x", "t2")[0], 0)

    def test_ignored_nested_skill_unlocks_from_its_directory(self):
        write(self.repo, ".gitignore", ".claude/\n")
        write(self.repo, "pkg/.claude/skills/ui/SKILL.md", VALID.replace("name: api", "name: ui"))
        pkg = join(self.repo, "pkg")
        self.send({"hook_event_name": "PostToolUse", "tool_name": "Skill", "cwd": pkg,
                   "tool_input": {"skill": "ui"}})
        self.assertEqual(self.send({"hook_event_name": "PreToolUse", "tool_name": "Edit", "cwd": pkg,
                                    "tool_input": {"file_path": join(pkg, "src/a.py")}})[0], 0)

    def test_lint_command(self):
        core = join(PLUGIN_ROOT, "hooks", "sdd_core.py")
        ok = subprocess.run([sys.executable, core, "lint", self.repo], capture_output=True, text=True)
        self.assertEqual(ok.returncode, 0, ok.stderr)
        self.assertIn("1 project skill(s) complete", ok.stdout)
        write(self.repo, ".claude/skills/api/SKILL.md", VALID + "SDD-TODO\n")
        bad = subprocess.run([sys.executable, core, "lint", self.repo], capture_output=True, text=True)
        self.assertEqual(bad.returncode, 1)
        self.assertIn(".claude/skills/api: SKILL.md: still contains SDD-TODO", bad.stdout)
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(subprocess.run([sys.executable, core, "lint", d], capture_output=True).returncode, 2)

    def test_commit_denied_while_marker_remains(self):
        write(self.repo, ".claude/skills/api/SKILL.md", VALID + "SDD-TODO\n")
        self.invoke("api")
        code, _, err = self.bash("git commit -m x")
        self.assertEqual(code, 2)
        self.assertIn("api", err)
        self.assertIn("SDD-TODO", err)

    def test_commit_allowed_when_skills_complete(self):
        self.assertEqual(self.bash("git commit -m x")[0], 0)

    def test_stop_blocks_once_after_edit(self):
        self.invoke("api")
        self.edit(join(self.repo, "src/a.py"))
        code, out, _ = self.stop()
        self.assertEqual(code, 0)
        decision = json.loads(out)
        self.assertEqual(decision["decision"], "block")
        self.assertIn("api", decision["reason"])
        self.assertEqual(self.stop()[1].strip(), "")

    def test_stop_silent_without_edits_or_when_active(self):
        self.assertEqual(self.stop()[1].strip(), "")
        self.invoke("api")
        self.edit(join(self.repo, "src/a.py"))
        self.assertEqual(self.stop(active=True)[1].strip(), "")

    def test_stop_lists_remaining_markers(self):
        write(self.repo, ".claude/skills/api/SKILL.md", VALID + "SDD-TODO\n")
        self.invoke("api")
        self.edit(join(self.repo, "src/a.py"))
        reason = json.loads(self.stop()[1])["reason"]
        self.assertIn("(SDD-TODO): api", reason)

    def test_session_start_injects_context_and_creates_directory(self):
        repo = self.make_repo()  # no .claude/skills
        code, out, _ = self.send({"hook_event_name": "SessionStart", "source": "startup", "cwd": repo})
        self.assertTrue(os.path.isdir(join(repo, ".claude/skills")))
        output = json.loads(out)["hookSpecificOutput"]
        self.assertIn("Skill-Driven Development is active", output["additionalContext"])
        self.assertIs(output["reloadSkills"], True)

    def test_session_start_does_not_reload_when_directory_exists(self):
        _, out, _ = self.send({"hook_event_name": "SessionStart", "source": "startup"})
        self.assertNotIn("reloadSkills", json.loads(out)["hookSpecificOutput"])

    def test_session_start_after_compaction_lists_skills(self):
        self.invoke("api")
        _, out, _ = self.send({"hook_event_name": "SessionStart", "source": "compact"})
        self.assertIn("Skills in use before compaction: api",
                      json.loads(out)["hookSpecificOutput"]["additionalContext"])

    def test_nothing_happens_outside_git(self):
        with tempfile.TemporaryDirectory() as d:
            code, out, _ = self.send({"hook_event_name": "SessionStart", "source": "startup", "cwd": d})
            self.assertEqual((code, out.strip()), (0, ""))
            self.assertEqual(os.listdir(d), [])
            self.assertEqual(self.send({"hook_event_name": "PreToolUse", "tool_name": "Bash", "cwd": d,
                                       "tool_input": {"command": "rm x"}})[0], 0)

    def test_gate_fails_closed(self):
        for stdin in ("", "{not json", json.dumps({"hook_event_name": "PreToolUse", "tool_name": "Edit"})):
            code, _, err = self.run_raw(stdin)
            self.assertEqual(code, 2, stdin)
            self.assertIn("the hook failed", err)

    def test_gitignored_skill_unlocks(self):
        write(self.repo, ".gitignore", ".claude/\n")
        self.invoke("api")
        self.assertEqual(self.edit(join(self.repo, "src/a.py"))[0], 0)

    def test_multiline_commit_is_gated(self):
        write(self.repo, ".claude/skills/api/SKILL.md", VALID + "SDD-TODO\n")
        self.assertEqual(self.bash("git add .\ngit commit -m x")[0], 2)

    def test_git_failure_denies_edits_and_commits_but_never_other_commands(self):
        def event(tool, tool_input):
            return json.dumps({"hook_event_name": "PreToolUse", "session_id": "s1", "cwd": self.repo,
                               "tool_name": tool, "tool_input": tool_input})
        broken = {"PATH": "/nonexistent"}
        code, _, err = self.run_raw(event("Write", {"file_path": join(self.repo, "a.py")}), **broken)
        self.assertEqual(code, 2)
        self.assertIn("the hook failed", err)
        self.assertEqual(self.run_raw(event("Bash", {"command": "git commit -m x"}), **broken)[0], 2)
        self.assertEqual(self.run_raw(event("Bash", {"command": "rm x"}), **broken)[0], 0)
        self.assertEqual(self.run_raw(event("Bash", {"command": "ls -la"}), **broken)[0], 0)

    def test_other_events_never_block_on_bad_input(self):
        code, out, _ = self.run_raw(json.dumps({"hook_event_name": "Stop"}))  # no session_id, no cwd
        self.assertEqual((code, out.strip()), (0, ""))

    def test_hooks_json_registers_events(self):
        with open(join(PLUGIN_ROOT, "hooks/hooks.json"), encoding="utf-8") as f:
            cfg = json.load(f)["hooks"]
        self.assertEqual(sorted(cfg), ["PostToolUse", "PostToolUseFailure", "PreToolUse", "SessionStart",
                                       "Stop", "UserPromptExpansion"])
        self.assertEqual(cfg["PreToolUse"][0]["matcher"], "Edit|Write|NotebookEdit|Bash")
        self.assertEqual(cfg["PostToolUse"][0]["matcher"], "Skill|Bash")
        self.assertEqual(cfg["PostToolUseFailure"][0]["matcher"], "Bash")


if __name__ == "__main__":
    unittest.main()
