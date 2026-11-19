"""Pure decision logic for the Skill-Driven Development hooks.

Nothing here reads hook input; hooks/sdd.py does that. The file has no
imports from the rest of the plugin, so it can be copied into a project and
run on its own to check skills in a pre-commit hook or in CI:

    python3 sdd_core.py lint [directory]
"""
import fnmatch
import json
import os
import re
import subprocess
import sys
import tempfile
import time

MARKER = "SDD-TODO"
MAX_DESCRIPTION = 1024
MAX_SKILL_LINES = 500

_SKILL_FILE = re.compile(r"(?:^|/)\.claude/skills/[^/]+/SKILL\.md$")
_FRONTMATTER_KEY = re.compile(r"^([A-Za-z_][\w-]*):[ \t]*(.*)$")


# --- git and paths ----------------------------------------------------------

def _git(directory, *args):
    """Run git; return (returncode, stdout, stderr). Raises RuntimeError if git cannot run."""
    try:
        result = subprocess.run(
            ["git", "-C", directory, *args],
            capture_output=True, timeout=10,
            encoding="utf-8", errors="replace",
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


# --- skills -----------------------------------------------------------------

def _skills_in(directory):
    top = os.path.join(directory, ".claude", "skills")
    if not os.path.isdir(top):
        return []
    return [
        os.path.join(top, name)
        for name in os.listdir(top)
        if os.path.isfile(os.path.join(top, name, "SKILL.md"))
    ]


def list_skills(root, near=None):
    """Directories of every project skill under `root`, sorted.

    Three sources, because projects often gitignore .claude/: git's file
    list (finds nested skill directories without walking ignored trees), the
    root-level .claude/skills/ read from disk, and, when `near` is given,
    the .claude/skills/ of every directory from `near` up to the root.
    """
    code, out, _ = _git(root, "ls-files", "-co", "--exclude-standard", "-z")
    found = set()
    if code == 0:
        found.update(
            os.path.join(root, os.path.dirname(rel))
            for rel in out.split("\0")
            if _SKILL_FILE.search(rel) and os.path.isfile(os.path.join(root, rel))
        )
    found.update(_skills_in(root))
    if near:
        directory = os.path.realpath(near)
        while directory != root and directory.startswith(root + os.sep):
            found.update(_skills_in(directory))
            directory = os.path.dirname(directory)
    return sorted(found)


def find_skill(root, name, near=None):
    """Directory of the project skill called `name`, or None."""
    name = name[1:] if name.startswith("/") else name
    if not name or ":" in name:
        return None
    for skill_dir in list_skills(root, near):
        if os.path.basename(skill_dir) == name:
            return skill_dir
    return None


def parse_frontmatter(text):
    """Keys and string values of the leading --- block. Not a YAML parser.

    Handles `key: value`, a value continued on indented lines, and one level
    of nesting, returned as `parent.child`.
    """
    lines = text.lstrip("\ufeff").replace("\r\n", "\n").split("\n")
    if not lines or lines[0].strip() != "---":
        return {}
    fields, key, nested = {}, None, False
    for line in lines[1:]:
        if line.strip() == "---":
            return {k: v.strip().strip("\"'").strip() for k, v in fields.items()}
        match = _FRONTMATTER_KEY.match(line)
        if match:
            key, value = match.groups()
            block = re.fullmatch(r"[>|][+-]?", value.strip())
            fields[key] = "" if block else value
            nested = not block and not value.strip()
        elif key and line[:1] in (" ", "\t"):
            child = _FRONTMATTER_KEY.match(line.strip()) if nested else None
            if child:
                fields[key + "." + child.group(1)] = child.group(2)
            else:
                fields[key] = (fields[key] + " " + line.strip()).strip()
    return {}  # block never closed


def _read_frontmatter(skill_dir):
    try:
        with open(os.path.join(skill_dir, "SKILL.md"), encoding="utf-8", errors="replace") as f:
            return parse_frontmatter(f.read())
    except OSError:
        return {}


def covers(skill_dir):
    """Glob patterns the skill limits itself to (metadata.covers), or None for no limit."""
    value = _read_frontmatter(skill_dir).get("metadata.covers", "")
    patterns = [p.strip().strip("\"'").strip() for p in value.strip("[]").split(",")]
    patterns = [p for p in patterns if p]
    return patterns or None


def path_matches(relpath, patterns):
    """True when the repository-relative path matches one of the patterns.

    `*` and `**` match across directories; a pattern naming a directory
    matches everything below it.
    """
    for pattern in patterns:
        pattern = pattern.rstrip("/")
        if fnmatch.fnmatchcase(relpath, pattern):
            return True
        if relpath == pattern or relpath.startswith(pattern + "/"):
            return True
    return False


def lint_skill(skill_dir):
    """Problems that make the skill incomplete; empty when it passes."""
    skill_md = os.path.join(skill_dir, "SKILL.md")
    try:
        with open(skill_md, encoding="utf-8", errors="replace") as f:
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
                with open(path, encoding="utf-8", errors="replace") as f:
                    content = f.read()
            except OSError:
                continue
            if MARKER in content:
                problems.append(
                    "%s: still contains %s" % (os.path.relpath(path, skill_dir), MARKER)
                )
    return problems


# --- session state ----------------------------------------------------------

def _safe(value):
    return re.sub(r"[^A-Za-z0-9_-]", "", str(value))


def _state_path(data_dir, session_id):
    return os.path.join(data_dir, "sessions", (_safe(session_id) or "unknown") + ".json")


def _write_json(path, data):
    """Write atomically, so parallel hook processes never see half a file."""
    directory = os.path.dirname(path)
    os.makedirs(directory, exist_ok=True)
    handle, temp = tempfile.mkstemp(dir=directory, prefix=".tmp-")
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as f:
            json.dump(data, f)
        os.replace(temp, path)
    except BaseException:
        if os.path.exists(temp):
            os.remove(temp)
        raise


def load_state(data_dir, session_id):
    """Session state; anything missing or unreadable is the empty state.

    skills: project skills invoked in the session, as root plus name.
    edits_since_review: a covered change happened since the last review.
    unskilled: per root, files changed with no skill covering them.
    """
    empty = {"skills": [], "edits_since_review": False, "unskilled": {}}
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
    unskilled = {}
    raw = data.get("unskilled")
    if isinstance(raw, dict):
        for root, paths in raw.items():
            if isinstance(paths, list):
                kept = [p for p in paths if isinstance(p, str)]
                if kept:
                    unskilled[root] = kept
    return {
        "skills": skills,
        "edits_since_review": data.get("edits_since_review") is True,
        "unskilled": unskilled,
    }


def save_state(data_dir, session_id, state):
    _write_json(_state_path(data_dir, session_id), state)


def add_skill(state, root, name):
    entry = {"root": root, "name": name}
    if entry not in state["skills"]:
        state["skills"].append(entry)


def unlocked(state, root):
    """True when a skill of this project has been invoked in the session."""
    return any(skill["root"] == root for skill in state["skills"])


def covered(state, root, relpath, near=None):
    """True when an invoked skill of this project covers the file.

    A skill without metadata.covers covers every file in its project.
    """
    for skill in state["skills"]:
        if skill["root"] != root:
            continue
        skill_dir = find_skill(root, skill["name"], near)
        patterns = covers(skill_dir) if skill_dir else None
        if patterns is None or path_matches(relpath, patterns):
            return True
    return False


def cleanup_old(data_dir, days=30):
    """Remove session files not touched for `days`."""
    directory = os.path.join(data_dir, "sessions")
    try:
        names = os.listdir(directory)
    except OSError:
        return
    limit = time.time() - days * 86400
    for name in names:
        path = os.path.join(directory, name)
        try:
            if os.path.getmtime(path) < limit:
                os.remove(path)
        except OSError:
            pass


# --- repository snapshots ---------------------------------------------------
# A shell command is not parsed to guess what it writes. The state of the
# repository is recorded before the command and compared after it.

def snapshot(root):
    """Files git reports as changed or untracked, each with [mtime_ns, size] or None if missing.

    Skill files are left out; they may always be changed. Ignored files are
    not listed by git, so they are left out too.
    """
    code, out, err = _git(root, "status", "--porcelain=v1", "-z", "--untracked-files=all", "--no-renames")
    if code != 0:
        raise RuntimeError("git status failed: %s" % (err.strip() or "exit %d" % code))
    files = {}
    for entry in out.split("\0"):
        path = entry[3:]
        if not path or "/.claude/skills/" in "/" + path:
            continue
        try:
            info = os.lstat(os.path.join(root, path))
            files[path] = [info.st_mtime_ns, info.st_size]
        except OSError:
            files[path] = None
    return files


def changed_paths(before, after):
    """Paths whose content state differs between two snapshots of one repository.

    A path that left the list (committed, stashed, restored) is not a change:
    staging and committing do not alter file contents.
    """
    missing = object()
    return sorted(path for path, state in after.items() if before.get(path, missing) != state)


def _snapshot_path(data_dir, session_id, tool_use_id):
    name = "%s.snap-%s.json" % (_safe(session_id) or "unknown", _safe(tool_use_id))
    return os.path.join(data_dir, "sessions", name)


def save_snapshot(data_dir, session_id, tool_use_id, data):
    _write_json(_snapshot_path(data_dir, session_id, tool_use_id), data)


def take_snapshot(data_dir, session_id, tool_use_id):
    """Load and remove the snapshot stored for one tool call; None if there is none."""
    path = _snapshot_path(data_dir, session_id, tool_use_id)
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        os.remove(path)
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


# --- shell commands ---------------------------------------------------------
# Deliberate shortcut: commit and push are recognised by pattern, not by
# parsing the shell. An unusual spelling (a git alias, a command built inside
# quotes or $(...)) is not recognised. Upgrade path: a real tokenizer.

_QUOTED = re.compile(r"'[^']*'|\"(?:\\.|[^\"\\])*\"")
# A command position: start of text or line, after ; & | ( { !, or after a
# shell keyword; then optional VAR=value assignments and wrapper commands,
# then an optional path in front of the command name.
_START = (
    r"(?:^|[;&|({!\n]|\b(?:then|do|else)\s)\s*"
    r"(?:(?:[A-Za-z_]\w*=\S*|(?:sudo|time|env|command|exec|nohup|xargs)(?:[ \t]+-\S+)*)[ \t]+)*"
    r"(?:[^\s;&|(){}]*/)?"
)
_GIT_PUBLISH = re.compile(
    _START + r"git\b(?:[ \t]+(?:-[Cc][ \t]+\S+|-\S+))*[ \t]+(?:commit|push)(?![\w-])"
)


def is_commit_or_push(command):
    return bool(_GIT_PUBLISH.search(_QUOTED.sub("''", command)))


# --- command line -----------------------------------------------------------

def main(argv):
    if len(argv) < 2 or argv[1] != "lint" or len(argv) > 3:
        print("usage: python3 sdd_core.py lint [directory]", file=sys.stderr)
        return 2
    start = argv[2] if len(argv) == 3 else os.getcwd()
    try:
        root = project_root(start)
    except RuntimeError as error:
        print(str(error), file=sys.stderr)
        return 2
    if root is None:
        print("not a git repository: %s" % start, file=sys.stderr)
        return 2
    skills = list_skills(root, start)
    failed = 0
    for skill_dir in skills:
        for problem in lint_skill(skill_dir):
            failed += 1
            print("%s: %s" % (os.path.relpath(skill_dir, root), problem))
    if failed:
        return 1
    print("%d project skill(s) complete" % len(skills))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
