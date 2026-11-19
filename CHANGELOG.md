# Changelog

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [0.2.0] - 2026-11-19

### Changed

- Shell commands are no longer refused for what their text looks like. The
  repository is compared before and after each command. Changes with no
  skill covering them are reported to Claude and hold back commit, push and
  the end of the turn until a skill is invoked or the change is undone.
  This catches formatters, package managers and scripts, and ends refusals
  of harmless commands such as a redirect into a temporary directory.

### Added

- `metadata.covers` in a skill's frontmatter limits the skill to the files
  matching its glob patterns.
- `python3 hooks/sdd_core.py lint [directory]` checks that every project
  skill is complete, for use in a pre-commit hook or in CI.
- Skills in a git-ignored nested `.claude/skills/` are found when the
  session works in or below that directory.
- Session files older than 30 days are removed at session start.

## [0.1.0] - 2026-11-19

### Added

- Edit gate: file changes inside a git repository are refused until a
  project skill has been invoked in the session. Files under
  `.claude/skills/` are always editable.
- Shell gate: shell commands that match known ways of writing files are held
  to the same rule.
- Commit gate: `git commit` and `git push` are refused while any project
  skill is incomplete.
- End-of-turn review: after a turn that changed files, Claude is asked once
  to review the skills it used.
- Skill lint: frontmatter, description length, file length and leftover
  template markers.
- The `skill-first` skill with the loop, the rules for writing project
  skills and the base skill template.
- Session context at startup and after compaction.
