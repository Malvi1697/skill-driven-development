# Changelog

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

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
