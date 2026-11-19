# Skill-Driven Development

A Claude Code plugin for skill-first development.

Test-driven development says: write the test, then the code.
Skill-driven development (S-DD) says: **have the skill, then do the work.**
The agent never develops without written instructions for the kind of work it is doing.

> **Status: design phase.** The repository currently holds the plugin manifest
> and the rules below. The hooks and the skill that enforce them are not
> implemented yet, so installing the plugin does nothing so far.

## The loop

1. **Find** the project skill for this kind of work.
2. **None exists?** Create a base skill from a template (goal, constraints,
   commands) and start using it straight away.
3. **Exists but falls short?** Improve it.
4. **Work** through the skill, filling it in as you learn.
5. **Finish** only when every skill you used is complete: no template
   leftovers, and reviewed for anything worth adding.

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

## Install

```
/plugin install skill-driven-development --marketplace Malvi1697/skill-driven-development
```

## Scope

The first version targets Claude Code only. The plugin has no dependency on
any other plugin or skill collection.

## License

[MIT](LICENSE)
