# Harness facts

Behaviour of Claude Code that the hooks rely on and that the documentation
does not state outright. Observed with Claude Code 2.1.327 by logging hook
input from a headless session, unless marked "from the docs".

1. **Skill name in hook input.** When Claude invokes a skill, `PreToolUse`
   and `PostToolUse` fire with `tool_name` `Skill` and the name in
   `tool_input.skill`. For a project skill the value is the bare directory
   name (`demo`), with no leading slash.
2. **Subagents share the session.** Tool calls made inside a subagent carry
   the same `session_id` as the main session, plus `agent_id` and
   `agent_type`. A skill invoked in the main session therefore unlocks its
   subagents, and the other way round.
3. **Start reason.** `SessionStart` input has a `source` field. Observed:
   `startup`. From the docs: `startup`, `resume`, `clear`, `compact`
   ("Auto or manual compaction"), `fork`.
4. **Skills directory created by the hook.** Not observed. From the docs:
   skill discovery normally runs before `SessionStart` hooks finish, and a
   hook that adds skill directories should return `reloadSkills: true`. The
   hook does that whenever it creates `.claude/skills/`.

5. **Shell commands.** `PostToolUse` fires after a Bash call that exited
   normally and `PostToolUseFailure` after one that failed; both carry the
   same `tool_use_id` as the `PreToolUse` event for that call (from the
   docs). Observed: a file changed through `tee` with no skill in use was
   recorded by the hook after the command, and the `Stop` hook then held
   the turn back with the list of changed files. From the docs:
   `PostToolUse` can return `decision: "block"` with a `reason`, which is
   added next to the tool result; `PostToolUseFailure` can only return
   `additionalContext`.
6. **Skill listing budget.** From the docs: skill descriptions share a
   budget of 1% of the model's context window; when it overflows, the
   descriptions of the least-invoked skills are dropped.
7. **Skills invoked by the user.** From the docs, not observed: typing
   `/skill-name` does not fire `PreToolUse` for the `Skill` tool; it fires
   `UserPromptExpansion` with the name in `command_name`.

One more fact that shapes how the plugin feels in use, from the docs and
observed: `.claude/` is a protected path. Writes to `.claude/skills/` are
prompted in the `default` and `acceptEdits` permission modes even when an
allow rule or a hook approves them, and are denied in `dontAsk` mode and in
headless runs. The prompt offers to allow edits to the project's `.claude`
folder for the rest of the session.
