---
name: skill-first
description: Use before changing any file in a project, however small the change. Explains the skill-first loop, which is to find the project skill for this kind of work, create a base skill from the template when none fits, work through it, and review it when the work is done.
---

# Skill first

In this project no file is changed without a project skill for that kind of
work. A project skill is a directory under `.claude/skills/` with a
`SKILL.md`. Hooks enforce the rule: a change is refused until a project skill
has been invoked in this session.

There is no exemption for small changes. A one-word fix goes through a skill
too. Reading, searching and answering questions need no skill.

## The loop

1. **Find.** Look at the project skills on offer and pick the one for this
   kind of work: "changing the API layer", "writing database migrations",
   "editing the docs". The match is on the kind of work, not on the task.
2. **None fits: create a base skill.** Open [template.md](template.md), copy
   the template into `.claude/skills/<name>/SKILL.md`, and fill in the goal,
   constraints and commands from what you already know: the request, the
   repository, the project's instructions. Then invoke the new skill with
   the Skill tool. Read [writing-skills.md](writing-skills.md) first.
3. **One fits but falls short: improve it.** Add what is missing before you
   rely on it. Read [writing-skills.md](writing-skills.md) first.
4. **Invoke the skill, then work through it.** Follow what it says. When you
   learn something the skill should have told you, such as a command, a
   constraint or a step that went wrong, write it into the skill while it is
   fresh.
5. **Review at the end of the turn.** For each skill you used, either add
   what this work taught, or say plainly that its content was enough. A
   skill that was enough stays unchanged.
6. **Finish the skill before committing.** Every `SDD-TODO` must be replaced
   with real content, or its section removed. A commit or push is refused
   while any project skill still contains one.

## When things do not go as described

- **Writing under `.claude/skills/` asks for permission.** That directory is
  protected by Claude Code, so the user is asked to approve the write. Tell
  them they can allow edits to the project's `.claude` folder for the
  session.
- **The Skill tool does not know a skill you just created.** Ask the user to
  run `/reload-skills`, then invoke it again.
- **After the conversation is compacted,** invoke the skills you were using
  again; their text may no longer be in context.
- **A shell command changed files and you are told no skill covers them.**
  Shell commands are checked by what they changed, after they ran. Invoke
  the skill for that work, then check the changes against it, or undo them.
  Until then, commit, push and the end of the turn are held back.
- **A file is "not covered by the skills in use".** The skills you invoked
  declare which files they cover and this file is not among them. Invoke the
  skill for this kind of work, or create one.

## Which file to open

- [writing-skills.md](writing-skills.md): open before creating a skill or
  changing one. How to scope it, describe it and lay it out.
- [template.md](template.md): open when creating a skill. The base skill to
  copy.
