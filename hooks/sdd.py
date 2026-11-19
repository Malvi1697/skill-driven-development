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
DENY_NOT_COVERED = (
    "Skill-Driven Development: {path} is not covered by the skills in use ({names}); each of "
    "them declares the files it covers. Invoke the project skill for this kind of work, or "
    "create one, before changing this file."
)
DENY_COMMIT = "Skill-Driven Development: commit and push are blocked until these skills are complete:\n{problems}"
DENY_COMMIT_UNSKILLED = (
    "Skill-Driven Development: commit and push are blocked because files were changed with no "
    "project skill covering them: {paths}. Invoke the project skill for this kind of work first."
)
SHELL_CHANGE = (
    "Skill-Driven Development: this command changed files with no project skill covering them: "
    "{paths}. Invoke the project skill for this kind of work now (create a base skill from the "
    "template if none fits), then check these changes against it. Commit and push stay blocked "
    "until then."
)
STOP_UNSKILLED = (
    "Skill-Driven Development: files were changed with no project skill covering them: {paths}. "
    "Before finishing, invoke the project skill for this kind of work (create a base skill from "
    "the template if none fits) and check these changes against it, or undo them."
)
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


def listed(paths, limit=10):
    shown = ", ".join(paths[:limit])
    return shown if len(paths) <= limit else "%s and %d more" % (shown, len(paths) - limit)


def skill_names(state, root=None):
    names = []
    for skill in state["skills"]:
        if (root is None or skill["root"] == root) and skill["name"] not in names:
            names.append(skill["name"])
    return names


def refresh_pending(session):
    """Drop files that are no longer changed (undone, or committed by hand) from the pending list."""
    state, dirty = session.state, False
    for root in list(state["unskilled"]):
        try:
            current = core.snapshot(root)
        except RuntimeError:
            continue  # cannot tell: keep them pending
        still = [p for p in state["unskilled"][root] if p in current]
        if len(still) != len(state["unskilled"][root]):
            dirty = True
            if still:
                state["unskilled"][root] = still
            else:
                del state["unskilled"][root]
    if dirty:
        session.save()


def session_start(event):
    root = core.project_root(event["cwd"])
    if root is None:
        return None
    session = Session(event)
    core.cleanup_old(session.data_dir)
    output = {"hookEventName": "SessionStart", "additionalContext": SESSION_CONTEXT}
    skills_dir = os.path.join(root, ".claude", "skills")
    if not os.path.isdir(skills_dir):
        os.makedirs(skills_dir, exist_ok=True)
        output["reloadSkills"] = True
    if event.get("source") == "compact":
        names = skill_names(session.state, root)
        if names:
            output["additionalContext"] += "\n" + COMPACT_CONTEXT.format(names=", ".join(names))
    return {"hookSpecificOutput": output}


def record_skill(event, name):
    cwd = event["cwd"]
    root = core.project_root(cwd)
    if root is None or not isinstance(name, str):
        return None
    skill_dir = core.find_skill(root, name, cwd)
    if not skill_dir:
        return None
    session = Session(event)
    state = session.state
    core.add_skill(state, root, os.path.basename(skill_dir))
    pending = state["unskilled"].get(root, [])
    still = [p for p in pending if not core.covered(state, root, p, cwd)]
    if len(still) < len(pending):
        state["edits_since_review"] = True  # earlier shell changes are now this skill's work
    if still:
        state["unskilled"][root] = still
    else:
        state["unskilled"].pop(root, None)
    session.save()
    return None


def gate_file(event):
    path = event["tool_input"][FILE_TOOLS[event["tool_name"]]]
    path = os.path.join(event["cwd"], path)  # no effect on an absolute path
    root = core.project_root(path)
    if root is None or core.in_skills_dir(path, root):
        return None
    session = Session(event)
    relpath = os.path.relpath(os.path.realpath(path), root)
    if core.covered(session.state, root, relpath, event["cwd"]):
        session.mark_edit()
        return None
    names = skill_names(session.state, root)
    if names:
        raise Deny(DENY_NOT_COVERED.format(path=relpath, names=", ".join(names)))
    raise Deny(DENY_NO_SKILL.format(root=root))


def before_bash(event):
    """Gate commit and push; record the repository state so after_bash can see what changed.

    Nothing else is refused here: what a shell command writes is judged by
    its effect, after it ran, not guessed from its text.
    """
    command = event["tool_input"]["command"]
    cwd = event["cwd"]
    publishes = core.is_commit_or_push(command)
    try:
        root = core.project_root(cwd)
    except RuntimeError:
        if publishes:
            raise  # fail closed: a commit must not slip through a broken git
        return None  # any other command stays free
    if root is None:
        return None
    session = Session(event)
    if publishes:
        problems = [
            "- %s: %s" % (os.path.basename(skill_dir), problem)
            for skill_dir in core.list_skills(root, cwd)
            for problem in core.lint_skill(skill_dir)
        ]
        if problems:
            raise Deny(DENY_COMMIT.format(problems="\n".join(problems)))
        refresh_pending(session)
        pending = session.state["unskilled"].get(root)
        if pending:
            raise Deny(DENY_COMMIT_UNSKILLED.format(paths=listed(pending)))
    tool_use_id = event.get("tool_use_id")
    if tool_use_id:
        try:
            core.save_snapshot(session.data_dir, session.session_id, tool_use_id,
                               {"root": root, "files": core.snapshot(root)})
        except Exception:  # noqa: BLE001 - a snapshot problem must never refuse a command
            pass
    return None


def after_bash(event):
    tool_use_id = event.get("tool_use_id")
    if not tool_use_id:
        return None
    session = Session(event)
    saved = core.take_snapshot(session.data_dir, session.session_id, tool_use_id)
    if not saved or not isinstance(saved.get("root"), str) or not isinstance(saved.get("files"), dict):
        return None
    root, state = saved["root"], session.state
    changed = core.changed_paths(saved["files"], core.snapshot(root))
    if not changed:
        return None
    uncovered = [p for p in changed if not core.covered(state, root, p, event.get("cwd"))]
    if len(uncovered) < len(changed):
        state["edits_since_review"] = True
    if uncovered:
        pending = state["unskilled"].setdefault(root, [])
        pending.extend(p for p in uncovered if p not in pending)
    session.save()
    if not uncovered:
        return None
    reason = SHELL_CHANGE.format(paths=listed(uncovered))
    if event["hook_event_name"] == "PostToolUseFailure":
        return {"hookSpecificOutput": {"hookEventName": "PostToolUseFailure", "additionalContext": reason}}
    return {"decision": "block", "reason": reason}


def stop(event):
    if event.get("stop_hook_active"):
        return None
    session = Session(event)
    refresh_pending(session)
    state = session.state
    pending = [p for paths in state["unskilled"].values() for p in paths]
    if pending:
        return {"decision": "block", "reason": STOP_UNSKILLED.format(paths=listed(pending))}
    if not state["edits_since_review"]:
        return None
    state["edits_since_review"] = False
    session.save()
    with_markers = []
    for skill in state["skills"]:
        skill_dir = core.find_skill(skill["root"], skill["name"], event.get("cwd"))
        if skill_dir and skill["name"] not in with_markers \
                and any(core.MARKER in p for p in core.lint_skill(skill_dir)):
            with_markers.append(skill["name"])
    reason = REVIEW.format(
        names=", ".join(skill_names(state)),
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
        return before_bash(event)
    if name in ("PostToolUse", "PostToolUseFailure") and tool == "Bash":
        return after_bash(event)
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
