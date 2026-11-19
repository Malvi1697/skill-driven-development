#!/usr/bin/env python3
"""Hook entry point for Skill-Driven Development.

Reads one hook event as JSON on stdin and dispatches on hook_event_name.
Exit 2 with a reason on stderr denies a tool call. Exit 0 with JSON on stdout
carries a Stop block or SessionStart context. Exit 0 with no output means no
decision.
"""
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import sdd_core as core  # noqa: E402

SESSION_CONTEXT = (
    "Skill-Driven Development is active in this repository. No file may be changed unless a "
    "project skill (.claude/skills/) for this kind of work has been invoked in this session. "
    "Before any change, follow skill-driven-development:skill-first: find the project skill, "
    "or create a base skill from the template, and invoke it."
)
COMPACT_CONTEXT = "Skills in use before compaction: {names}. Invoke them again before continuing."
DENY_NO_SKILL = (
    "Skill-Driven Development: no project skill is in use for {root}. Before changing files, "
    "invoke the project skill for this kind of work with the Skill tool. If none fits, follow "
    "skill-driven-development:skill-first to create a base skill in .claude/skills/ from the "
    "template, then invoke it. Files under .claude/skills/ can be edited with the file tools "
    "at any time."
)
DENY_COMMIT = "Skill-Driven Development: commit and push are blocked until these skills are complete:\n{problems}"
REVIEW = (
    "Skill-Driven Development: files were changed in this turn. Go through each skill you used "
    "({names}): add what this work taught that the skill did not say, or state that its content "
    "was enough. Remaining template markers (SDD-TODO): {markers}. Skills with markers cannot "
    "be committed."
)
DENY_CRASH = "Skill-Driven Development: the hook failed ({error}), so the change is blocked. Fix or disable the plugin."

FILE_TOOLS = {"Edit": "file_path", "Write": "file_path", "NotebookEdit": "notebook_path"}


class Deny(Exception):
    """Raised by a handler to block the tool call with a message for Claude."""


class Session:
    def __init__(self, event):
        self.data_dir = os.environ.get("CLAUDE_PLUGIN_DATA") or os.path.join(
            tempfile.gettempdir(), "skill-driven-development"
        )
        self.session_id = event.get("session_id") or "unknown"
        self.state = core.load_state(self.data_dir, self.session_id)

    def save(self):
        core.save_state(self.data_dir, self.session_id, self.state)

    def mark_edit(self):
        if not self.state["edits_since_review"]:
            self.state["edits_since_review"] = True
            self.save()


def session_start(event):
    root = core.project_root(event["cwd"])
    if root is None:
        return None
    output = {"hookEventName": "SessionStart", "additionalContext": SESSION_CONTEXT}
    skills_dir = os.path.join(root, ".claude", "skills")
    if not os.path.isdir(skills_dir):
        os.makedirs(skills_dir, exist_ok=True)
        output["reloadSkills"] = True
    if event.get("source") == "compact":
        names = [s["name"] for s in Session(event).state["skills"] if s["root"] == root]
        if names:
            output["additionalContext"] += "\n" + COMPACT_CONTEXT.format(names=", ".join(names))
    return {"hookSpecificOutput": output}


def record_skill(event, name):
    root = core.project_root(event["cwd"])
    if root is None or not isinstance(name, str):
        return None
    skill_dir = core.find_skill(root, name)
    if skill_dir:
        session = Session(event)
        core.add_skill(session.state, root, os.path.basename(skill_dir))
        session.save()
    return None


def gate_file(event):
    path = event["tool_input"][FILE_TOOLS[event["tool_name"]]]
    path = os.path.join(event["cwd"], path)  # no effect on an absolute path
    root = core.project_root(path)
    if root is None or core.in_skills_dir(path, root):
        return None
    session = Session(event)
    if not core.unlocked(session.state, root):
        raise Deny(DENY_NO_SKILL.format(root=root))
    session.mark_edit()
    return None


def gate_bash(event):
    command = event["tool_input"]["command"]
    publishes = core.is_commit_or_push(command)
    writes = core.is_write_command(command)
    if not publishes and not writes:
        return None  # reading is decided without git, so it can never be blocked
    root = core.project_root(event["cwd"])
    if root is None:
        return None
    if publishes:
        problems = [
            "- %s: %s" % (os.path.basename(skill_dir), problem)
            for skill_dir in core.list_skills(root)
            for problem in core.lint_skill(skill_dir)
        ]
        if problems:
            raise Deny(DENY_COMMIT.format(problems="\n".join(problems)))
    if writes:
        session = Session(event)
        if not core.unlocked(session.state, root):
            raise Deny(DENY_NO_SKILL.format(root=root))
        session.mark_edit()
    return None


def stop(event):
    session = Session(event)
    if not session.state["edits_since_review"] or event.get("stop_hook_active"):
        return None
    session.state["edits_since_review"] = False
    session.save()
    skills = session.state["skills"]
    with_markers = []
    for skill in skills:
        skill_dir = core.find_skill(skill["root"], skill["name"])
        if skill_dir and any(core.MARKER in p for p in core.lint_skill(skill_dir)):
            with_markers.append(skill["name"])
    reason = REVIEW.format(
        names=", ".join(s["name"] for s in skills),
        markers=", ".join(with_markers) or "none",
    )
    return {"decision": "block", "reason": reason}


def dispatch(event):
    name = event.get("hook_event_name")
    tool = event.get("tool_name")
    if name == "SessionStart":
        return session_start(event)
    if name == "PostToolUse" and tool == "Skill":
        return record_skill(event, event["tool_input"].get("skill"))
    if name == "UserPromptExpansion":
        return record_skill(event, event.get("command_name"))
    if name == "PreToolUse" and tool in FILE_TOOLS:
        return gate_file(event)
    if name == "PreToolUse" and tool == "Bash":
        return gate_bash(event)
    if name == "Stop":
        return stop(event)
    return None


def main():
    is_gate = True  # until the event says otherwise, fail closed
    try:
        event = json.loads(sys.stdin.read())
        is_gate = event.get("hook_event_name") == "PreToolUse"
        output = dispatch(event)
    except Deny as denial:
        print(str(denial), file=sys.stderr)
        return 2
    except Exception as error:  # noqa: BLE001 - any failure must fail closed on a gate
        if is_gate:
            print(DENY_CRASH.format(error="%s: %s" % (type(error).__name__, error)), file=sys.stderr)
            return 2
        return 0
    if output is not None:
        print(json.dumps(output))
    return 0


if __name__ == "__main__":
    sys.exit(main())
