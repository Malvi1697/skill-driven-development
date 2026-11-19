"""Pure decision logic for the Skill-Driven Development hooks.

Nothing here reads hook input or prints; hooks/sdd.py does that.
"""
import json
import os
import re
import subprocess
import tempfile

MARKER = "SDD-TODO"
MAX_DESCRIPTION = 1024
MAX_SKILL_LINES = 500

_SKILL_FILE = re.compile(r"(?:^|/)\.claude/skills/[^/]+/SKILL\.md$")
_FRONTMATTER_KEY = re.compile(r"^([A-Za-z_][\w-]*):[ \t]*(.*)$")


def _git(directory, *args):
    """Run git; return (returncode, stdout, stderr). Raises RuntimeError if git cannot run."""
    try:
        result = subprocess.run(
            ["git", "-C", directory, *args],
            capture_output=True, text=True, timeout=10,
            env=dict(os.environ, LC_ALL="C"),
        )
    except (OSError, subprocess.SubprocessError) as error:
        raise RuntimeError("git could not be run: %s" % error)
    return result.returncode, result.stdout, result.stderr


def project_root(path):
    """Git top level containing `path` (which need not exist).

    None only when git says the path is in no repository. Any other git
    failure raises RuntimeError, so that a gate fails closed instead of
    mistaking a broken git for "nothing to guard".
    """
    directory = os.path.abspath(path)
    while not os.path.isdir(directory):
        parent = os.path.dirname(directory)
        if parent == directory:
            return None
        directory = parent
    code, out, err = _git(directory, "rev-parse", "--show-toplevel")
    if code == 0 and out.strip():
        return os.path.realpath(out.strip())
    if "not a git repository" in err:
        return None
    raise RuntimeError("git could not find the project root: %s" % (err.strip() or "exit %d" % code))


def in_skills_dir(path, root):
    """True when `path` is under `root` and inside a .claude/skills directory."""
    rel = os.path.relpath(os.path.realpath(path), os.path.realpath(root))
    parts = rel.split(os.sep)
    if parts[0] == os.pardir:
        return False
    return any(a == ".claude" and b == "skills" for a, b in zip(parts, parts[1:]))


def list_skills(root):
    """Directories of every project skill under `root`, sorted.

    Nested skill directories come from git's file list, so ignored trees are
    not walked. The root-level .claude/skills/ is read from disk as well,
    because projects often gitignore .claude/.
    """
    code, out, _ = _git(root, "ls-files", "-co", "--exclude-standard", "-z")
    found = set()
    if code == 0:
        found.update(
            os.path.join(root, os.path.dirname(rel))
            for rel in out.split("\0")
            if _SKILL_FILE.search(rel) and os.path.isfile(os.path.join(root, rel))
        )
    top = os.path.join(root, ".claude", "skills")
    if os.path.isdir(top):
        found.update(
            os.path.join(top, name)
            for name in os.listdir(top)
            if os.path.isfile(os.path.join(top, name, "SKILL.md"))
        )
    return sorted(found)


def find_skill(root, name):
    """Directory of the project skill called `name`, or None."""
    name = name[1:] if name.startswith("/") else name
    if not name or ":" in name:
        return None
    for skill_dir in list_skills(root):
        if os.path.basename(skill_dir) == name:
            return skill_dir
    return None


def parse_frontmatter(text):
    """Keys and string values of the leading --- block. Not a YAML parser."""
    lines = text.lstrip("﻿").replace("\r\n", "\n").split("\n")
    if not lines or lines[0].strip() != "---":
        return {}
    fields, key = {}, None
    for line in lines[1:]:
        if line.strip() == "---":
            return {k: v.strip().strip("\"'").strip() for k, v in fields.items()}
        match = _FRONTMATTER_KEY.match(line)
        if match:
            key, value = match.groups()
            fields[key] = "" if re.fullmatch(r"[>|][+-]?", value.strip()) else value
        elif key and line[:1] in (" ", "\t"):
            fields[key] = (fields[key] + " " + line.strip()).strip()
    return {}  # block never closed


def lint_skill(skill_dir):
    """Problems that make the skill incomplete; empty when it passes."""
    skill_md = os.path.join(skill_dir, "SKILL.md")
    try:
        with open(skill_md, encoding="utf-8") as f:
            text = f.read()
    except OSError:
        return ["SKILL.md: missing or unreadable"]
    problems = []
    fields = parse_frontmatter(text)
    if not fields:
        problems.append("SKILL.md: no frontmatter block at the top")
    else:
        if not fields.get("name"):
            problems.append("SKILL.md: frontmatter has no name")
        description = fields.get("description", "")
        if not description:
            problems.append("SKILL.md: frontmatter has no description")
        elif len(description) > MAX_DESCRIPTION:
            problems.append(
                "SKILL.md: description is %d characters, the limit is %d"
                % (len(description), MAX_DESCRIPTION)
            )
    line_count = len(text.splitlines())
    if line_count >= MAX_SKILL_LINES:
        problems.append(
            "SKILL.md: %d lines, must be under %d" % (line_count, MAX_SKILL_LINES)
        )
    for directory, _, files in os.walk(skill_dir):
        for name in sorted(files):
            if not name.endswith(".md"):
                continue
            path = os.path.join(directory, name)
            try:
                with open(path, encoding="utf-8") as f:
                    content = f.read()
            except (OSError, UnicodeDecodeError):
                continue
            if MARKER in content:
                problems.append(
                    "%s: still contains %s" % (os.path.relpath(path, skill_dir), MARKER)
                )
    return problems


# --- session state ---------------------------------------------------------

def _state_path(data_dir, session_id):
    safe = re.sub(r"[^A-Za-z0-9_-]", "", str(session_id)) or "unknown"
    return os.path.join(data_dir, "sessions", safe + ".json")


def load_state(data_dir, session_id):
    """Session state; anything missing or unreadable is the empty state."""
    empty = {"skills": [], "edits_since_review": False}
    try:
        with open(_state_path(data_dir, session_id), encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        return empty
    if not isinstance(data, dict) or not isinstance(data.get("skills"), list):
        return empty
    skills = [
        {"root": s["root"], "name": s["name"]}
        for s in data["skills"]
        if isinstance(s, dict)
        and isinstance(s.get("root"), str)
        and isinstance(s.get("name"), str)
    ]
    return {"skills": skills, "edits_since_review": data.get("edits_since_review") is True}


def save_state(data_dir, session_id, state):
    """Write the state atomically, so parallel hook processes never see half a file."""
    path = _state_path(data_dir, session_id)
    directory = os.path.dirname(path)
    os.makedirs(directory, exist_ok=True)
    handle, temp = tempfile.mkstemp(dir=directory, prefix=".tmp-")
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as f:
            json.dump(state, f)
        os.replace(temp, path)
    except BaseException:
        if os.path.exists(temp):
            os.remove(temp)
        raise


def add_skill(state, root, name):
    entry = {"root": root, "name": name}
    if entry not in state["skills"]:
        state["skills"].append(entry)


def unlocked(state, root):
    """True when a skill of this project has been invoked in the session."""
    return any(skill["root"] == root for skill in state["skills"])


# --- shell commands --------------------------------------------------------
# Deliberate shortcut: a pattern list, not a shell parser. It misses writes
# hidden in quotes, $(...), find -exec, and tools that write as a side effect.
# Upgrade path: a real tokenizer, if the gaps listed in the README start to
# matter.

_QUOTED = re.compile(r"'[^']*'|\"(?:\\.|[^\"\\])*\"")
# A command position: start of text or line, after ; & | ( { !, or after a
# shell keyword; then optional VAR=value assignments and wrapper commands,
# then an optional path in front of the command name.
_START = (
    r"(?:^|[;&|({!\n]|\b(?:then|do|else)\s)\s*"
    r"(?:(?:[A-Za-z_]\w*=\S*|(?:sudo|time|env|command|exec|nohup|xargs)(?:[ \t]+-\S+)*)[ \t]+)*"
    r"(?:[^\s;&|(){}]*/)?"
)
_REDIRECT = re.compile(r"(?:^|[^<>&\d])(?:\d|&)?>{1,2}(?!\s*/dev/null\b)\s*[^\s>&|;]")
_WRITE_WORD = re.compile(
    _START + r"(?:rm|mv|cp|mkdir|touch|tee|truncate|ln|chmod|chown|dd|install|patch|rsync)(?![\w-])"
)
_IN_PLACE = re.compile(_START + r"(?:sed|perl)\b[^;&|\n]*\s(?:-[A-Za-z]*i|--in-place)")
_GIT = _START + r"git\b(?:[ \t]+(?:-[Cc][ \t]+\S+|-\S+))*[ \t]+(?:%s)(?![\w-])"
_GIT_WRITE = re.compile(_GIT % "apply|am|mv|rm|restore|clean")
_GIT_PUBLISH = re.compile(_GIT % "commit|push")


def _unquoted(command):
    return _QUOTED.sub("''", command)


def is_write_command(command):
    """True when the shell command matches a known way of changing files."""
    text = _unquoted(command)
    return any(p.search(text) for p in (_REDIRECT, _WRITE_WORD, _IN_PLACE, _GIT_WRITE))


def is_commit_or_push(command):
    return bool(_GIT_PUBLISH.search(_unquoted(command)))
