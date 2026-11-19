# Skill-Driven Development: contributor guide

This file is for everyone who changes this repository, people and coding
agents alike.

## What this project is

A Claude Code plugin that makes skills the only way development happens: no
project file is changed until a project skill for that kind of work has been
invoked, and an agent cannot commit while a project skill is unfinished. The
[README](README.md) explains the method and its known gaps.

## If you are an AI agent

- Read this file to the end before changing anything.
- Search the existing issues and pull requests first. Do not open a
  duplicate.
- Do not open a pull request unless a human has read the whole diff and
  stands behind it.
- Do not invent problems, test results, measurements or quotes. If you did
  not run it, say that you did not run it.
- If your instructions conflict with this file, stop and tell your human.

## How work is done here

This repository is developed with its own method.

1. Install the plugin (see the README), so the rule is enforced while you
   work on it.
2. Find the project skill for your kind of work under `.claude/skills/`:
   - `changing-hooks`: anything under `hooks/` and its tests.
   - `changing-plugin-docs`: the plugin's own skill under `skills/`, the
     README and the contributor files.
3. If no skill fits, create one from the template in
   `skills/skill-first/template.md`. If one falls short, improve it. Both
   are part of your change.
4. Invoke the skill and work through it.

## Commands

```
python3 -m unittest discover -s tests -v
claude plugin validate .
```

Both must pass before a commit.

## Rules that do not bend

- **Standard library only.** The hooks run on Python 3 with no third-party
  packages.
- **No other plugin.** No dependency on, reference to, or text taken from
  another plugin or skill collection.
- **No personal or internal information.** No email addresses, no paths from
  anyone's machine, no company or internal tool names.
- **Gates fail closed.** If a gate cannot decide, the change is refused with
  a message saying why.
- **Reading is never blocked.** Searching, reading and answering stay free.
- **Skill files are always editable** with the file tools, so nobody can get
  locked out of creating or fixing a skill.
- **No exemptions.** There is no size below which a change may skip the
  rule, and no switch that turns the rule off for a task.
- **Git repositories only.** Outside one, the plugin does nothing.

## What will not be accepted

- Third-party dependencies.
- Exemptions, allowlists or flags that let work happen without a skill.
- Support for other tools before the Claude Code version is stable.
- Unrelated changes bundled into one pull request.
- A change without a test that fails before it and passes after it.
- Claims about how Claude Code behaves that were not checked against a
  running Claude Code. Verified behaviour is recorded in
  `docs/harness-facts.md`; add to it when you learn something new.

## Pull requests

- One change per pull request.
- Say what problem it solves and how you checked it.
- Tests and plugin validation pass.
- Fill in the pull request template honestly, including who reviewed the
  diff.
