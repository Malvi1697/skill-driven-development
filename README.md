# Skill-Driven Development

A Claude Code plugin for skill-first development.

Test-driven development says: write the test, then the code.
Skill-driven development (S-DD) says: **have the skill, then do the work.**
The agent never changes a project without written instructions for the kind
of work it is doing, and those instructions stay in the repository for the
next session.

## The loop

1. **Find** the project skill for this kind of work.
2. **None exists?** Create a base skill from a template (goal, constraints,
   commands) and start using it straight away.
3. **Exists but falls short?** Improve it.
4. **Work** through the skill, filling it in as you learn.
5. **Review** every skill you used when the turn ends: add what the work
   taught, or confirm the skill was enough.
6. **Commit** only when no skill has template leftovers.

## Rules

- **Always.** There is no exemption for small changes. A typo fix goes
  through a skill too.
- **Skills cover a kind of work, not a single task.** A project should end up
  with a small set of distinct skills, not one per ticket.
- **Skills are signposts.** `SKILL.md` stays short and links to detailed
  `.md` files next to it, which are read only when needed. Links go one level
  deep.
- **Skills live in the project**, in `.claude/skills/`, and are committed
  with the code.
- **Hooks enforce it.** The rule is checked by the plugin's hooks, not left
  to the agent's goodwill.

## What the plugin does

| When | What happens |
|---|---|
| A session starts in a git repository | Claude is told the rule. `.claude/skills/` is created if missing. |
| Claude tries to change a file and no project skill has been invoked in the session | The change is refused, with instructions to find or create a skill. |
| Claude changes a file under `.claude/skills/` | Always allowed, so a skill can always be created or fixed. |
| Claude runs a shell command that writes files, with no skill in use | Refused in the same way. |
| A turn that changed files ends | Claude is asked once to review the skills it used. |
| Claude runs `git commit` or `git push` while a project skill is unfinished | Refused, naming the skill and what is missing. |

A skill is unfinished when it has no name or description, its description is
over 1,024 characters, its `SKILL.md` has 500 lines or more, or any of its
`.md` files still contains the template marker `SDD-TODO`.

Reading, searching and answering questions are never blocked. Outside a git
repository the plugin does nothing. If Python 3 or git cannot be run, changes
are refused rather than let through.

## Install

This repository is its own marketplace. In a Claude Code session, add it
and install the plugin from it:

```
/plugin marketplace add Malvi1697/skill-driven-development
/plugin install skill-driven-development@skill-driven-development
```

On Claude Code 2.1.275 or later the two steps can be one:

```
/plugin install skill-driven-development --marketplace Malvi1697/skill-driven-development
```

From a shell, the same commands start with `claude plugin` instead of
`/plugin`.

Requirements: Claude Code, Python 3 and git. The hooks use the Python
standard library only.

The rule applies in every git repository where the plugin is enabled. To
limit it to some projects, enable the plugin in those projects' settings
instead of for your user.

## Good to know

- **Claude Code asks before writing under `.claude/`.** That folder is
  protected, so the first time a skill is created or edited you are asked to
  approve. Choose the option that allows edits to the project's `.claude`
  folder for the session. Headless runs (`claude -p`) cannot create or edit
  skills for the same reason.
- **A skill created in a brand-new `.claude/skills/` folder** may need
  `/reload-skills` once before it can be invoked.
- **Keep the set of skills small.** Skill descriptions share a listing
  budget of 1% of the context window. When it overflows, Claude Code drops
  the descriptions of the least-used skills, and they stop being found.

## Known gaps

- Any invoked project skill unlocks changes, whether or not it fits the
  work. Picking the right one is up to the skill descriptions.
- Shell commands are checked against a pattern list, not parsed. Some ways
  of writing files through the shell are not caught, and neither are tools
  that write files as a side effect, such as formatters and package
  managers. The same list recognises `git commit` and `git push`, so an
  unusual way of invoking them can slip past the commit gate.
- The shell check does not look at where a command writes. With no skill in
  use, a shell write to a temporary directory is refused as well when the
  session is inside a git repository.
- Skills in a nested `.claude/skills/` directory are only seen if git does
  not ignore them. The one at the repository root is always seen.
- Commits made by hand outside Claude Code are not checked.
- The plugin cannot stop someone who disables hooks or the plugin.

## Development

```
python3 -m unittest discover -s tests -v
claude plugin validate .
```

Contributing: read [AGENTS.md](AGENTS.md). It holds the rules for people and
coding agents alike. This repository is developed with its own method.

## Scope

This version targets Claude Code only. The plugin has no dependency on any
other plugin or skill collection.

## License

[MIT](LICENSE)
