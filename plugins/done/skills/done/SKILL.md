---
name: "done"
description: "Capture completed Codex work as an Obsidian note. Use when the user invokes `$done`, asks to wrap up, record what was accomplished, write the session to Obsidian, preserve decisions/verification/follow-ups, or turn the current completed task into durable personal knowledge."
---

# Done

## Workflow

1. Gather the evidence for this session before writing:
   - Conversation context and the user's stated goal.
   - `git status --short`, `git diff --stat`, and relevant `git diff -- <file>` output when a git repo is available.
   - Task docs such as `tasks/todo.md` and `tasks/lessons.md` when they exist.
   - Verification commands, test results, screenshots, logs, PR links, or clear notes that verification was not run.

2. Write only what is true from evidence. Do not claim tests passed, files changed, PRs opened, or decisions made unless the session or local state proves it. If work is incomplete, title and summarize it as incomplete.

3. Use this compact note shape unless the user asked for another format:

```markdown
# <Project or Area> - <Outcome>

## Tags
#done #codex

## Summary
<2-4 sentences describing the finished outcome and why it matters.>

## Completed
- <Concrete change or deliverable.>

## Verification
- `<command or check>` - <result>.

## Decisions
- <Decision and rationale, or "None recorded.">

## Changed Files
- `<path>` - <brief role in the work.>

## Follow-ups
- <Next action, or "None required.">
```

4. Prefer destination defaults in this order:
   - Vault: `$OBSIDIAN_VAULT` when set.
   - Vault: `/home/nekoguntai/obsidian/riannom` when it exists.
   - Otherwise ask for the vault path.
   - Note directory: `$DONE_OBSIDIAN_DIR` when set, else `AI maintained documentation/Skills/Sessions`.

5. Write the note with the bundled script. For a plugin install, `${CLAUDE_SKILL_DIR}` resolves to the skill directory. For a standalone Codex install, fall back to `$HOME/.codex/skills/done`:

```bash
skill_dir="${CLAUDE_SKILL_DIR:-$HOME/.codex/skills/done}"
python3 "$skill_dir/scripts/write_obsidian_done.py" \
  --title "<short descriptive title>" \
  --project "<project or area>" \
  --index "AI maintained documentation/Skills/_Index.md" \
  < /tmp/done-note.md
```

The script creates parent directories, uses a dated filename, refuses to overwrite existing notes by default, and prints the written path. Omit `--index` unless updating a related index is useful and low-risk.

6. After writing, tell the user the Obsidian note path and summarize the verification used. Keep the final response shorter than the note.

## Script Notes

- Use `--vault <path>` to override the vault.
- Use `--note-dir <relative/path>` to override the note folder inside the vault.
- Use `--date YYYY-MM-DD` for deterministic backfills.
- Use `--content-file <path>` instead of stdin when the note already exists as a file.
- Use `--overwrite` only when the user explicitly wants to replace an existing note.
