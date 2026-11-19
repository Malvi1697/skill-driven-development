---
name: changing-plugin-docs
description: Use when changing the plugin's own skill under skills/skill-first/, the README, the changelog, or the contributor files (AGENTS.md, CONTRIBUTING.md, SECURITY.md, CODE_OF_CONDUCT.md, .github templates) in this repository.
---

# Changing the plugin's documentation and skill

## Goal

Someone who has never seen the project can install it, understand the rule
and its gaps, and write a good project skill, from these files alone.

## Constraints

- All text is written for this project. Nothing is copied from another
  plugin or skill collection, and none is mentioned by name.
- No personal or internal information: no email addresses, no paths from a
  developer's machine, no company or internal tool names.
- `skills/skill-first/SKILL.md` stays under 500 lines and links each detail
  file directly; detail files do not link to further files and stay at or
  under 100 lines.
- The frontmatter description of a skill has no colon followed by a space.
- Files under `.claude/skills/` in this repository must not contain the
  template marker text, not even as an example. Say "the template marker".
- The README's "Known gaps" section stays truthful. A gap is removed only
  when a test shows it is closed.

## Commands

```
python3 -m unittest discover -s tests -v
claude plugin validate .
```

## Steps

1. If the change is to the plugin's skill or to a contributor file,
   `tests/test_plugin_skill.py` and `tests/test_repo_docs.py` hold the
   structural checks. Add or change the check first when the structure
   changes.
2. Make the change. Describe behaviour as it is, not as planned.
3. If hook behaviour is described, read `hooks/sdd.py` and
   `docs/harness-facts.md` to confirm it; do not describe it from memory.
4. Add a line to `CHANGELOG.md` for anything a user would notice.
5. Run both commands above.
