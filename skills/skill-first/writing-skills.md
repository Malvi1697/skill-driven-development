# Writing a project skill

## One skill per kind of work

A skill covers a kind of work that comes back: changing the API layer,
adding a database migration, writing end-to-end tests, editing user-facing
copy. It does not cover one task or one ticket.

Before creating a skill, ask whether an existing one already covers this
kind of work:

- It does, but something is missing: extend that skill.
- The work is a clearly different activity, with its own commands,
  constraints and ways of going wrong: create a new skill.
- You are unsure: extend. A few distinct skills are found reliably; many
  similar ones are not, and every skill's description costs context in every
  session.

A skill that would fit any change ("general development", "small edits",
"misc") is too broad. It tells the next session nothing and exists only to
get past the rule. Name the actual kind of work instead.

## Name and description

- `name`: lowercase words joined by hyphens, naming the work
  (`changing-api-layer`, `writing-migrations`). At most 64 characters.
- `description`: what kind of work the skill is for and when it applies, in
  the words someone would use when asking for that work. At most 1,024
  characters. Start with "Use when". Avoid a colon followed by a space
  inside it; it breaks the frontmatter.

The description is all that is visible before the skill is invoked. If it
does not say when the skill applies, the skill will not be found.

## A skill is a signpost

`SKILL.md` is read in full every time the skill is invoked, so keep it short:

- the goal, the constraints and the commands
- the steps in the order they are done
- one line per detail file, saying when to open it

Put anything long or only sometimes needed into its own `.md` file next to
`SKILL.md`: a checklist for one sub-case, a reference table, worked
examples, known pitfalls. Those files are read only when the signpost sends
the reader there.

Limits:

- `SKILL.md` stays under 500 lines.
- Detail files are linked directly from `SKILL.md`. A detail file does not
  link on to another file.
- A detail file longer than 100 lines starts with a table of contents.

Each link needs its "when": "open `migrations-rollback` notes before
writing a down migration" works; a bare list of files does not.

## What belongs in a skill

- Commands that are specific to this project and this work.
- Constraints someone new would break: what must not be touched, what must
  stay compatible, what has to be run before and after.
- The order of steps when the order matters.
- Mistakes that were actually made, and how to avoid them.

## What does not

- Details of one task: ticket numbers, the bug being fixed today.
- General knowledge the model already has, such as how a language or a
  common tool works.
- Anything already stated in the project's own instructions; point to it
  instead of repeating it.
- Guesses about what might be needed. Write what the work has shown.

## Keeping a skill honest

Change the skill when the work proves it wrong or incomplete, in the same
session. If a step in the skill no longer matches the project, fix or remove
it; a stale instruction is worse than a missing one.
