---
name: changing-hooks
description: Use when changing anything under hooks/ or its tests in this repository. Covers the gates, the skill lint, session state, shell command patterns, hook messages and hook registration.
---

# Changing the hooks

## Goal

The hooks keep one promise: no project file changes without a project skill
in use, and no agent commit while a project skill is unfinished. A change
here is good when that promise still holds and a test proves the new
behaviour.

## Constraints

- Python 3 standard library only.
- Gates fail closed: an error in a `PreToolUse` path must refuse the tool
  call with a message, never let it through.
- Reading must stay free: a read-only shell command must never be refused.
- Writes under `.claude/skills/` through the file tools are always allowed.
- Outside a git repository the hooks do nothing and create nothing.
- Messages shown to Claude are constants at the top of `hooks/sdd.py`. Tests
  match on parts of them; change both together.

## Commands

```
python3 -m unittest discover -s tests -v
claude plugin validate .
```

## Steps

1. Write the failing test first and watch it fail.
   - Decisions without input or output go in `hooks/sdd_core.py`, tested in
     `tests/test_core_*.py`.
   - Reading the event and answering it goes in `hooks/sdd.py`, tested in
     `tests/test_hooks.py` by running the script with JSON on stdin.
2. Make it pass with the smallest change.
3. For a new shell write pattern, add the command to `WRITES` in
   `tests/test_core_bash.py` and a look-alike read-only command to `READS`.
4. If the change depends on a hook's input or output format, check it
   against a running Claude Code and record what you saw in
   `docs/harness-facts.md`. The documentation alone is not enough.
5. If behaviour visible to users changed, update the README and
   `CHANGELOG.md` with the `changing-plugin-docs` skill.
6. Run both commands above.

## Known traps

- A session's state is keyed by `session_id`, and subagents share the
  session's id.
- Project roots and paths are compared after resolving symlinks. Compare
  resolved paths in tests too.
- Headless Claude Code cannot write under `.claude/`, so an end-to-end check
  that creates a skill has to be done in an interactive session.
