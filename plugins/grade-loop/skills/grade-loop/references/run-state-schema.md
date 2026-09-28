# Grade-loop run state (schema 1)

Use pr-delivery's canonical [loop-run-state.md](../../../../pr-delivery/skills/pr-delivery/references/loop-run-state.md)
for fields, transitions, archive handling, and cleanup gates. Resolve that file
from the installed pr-delivery skill when installed separately.

Grade's `scripts/run_state.py` is a thin wrapper over the shared CLI. It selects
immutable `workflow: grade-loop` automatically; all other commands and arguments
are identical. Initialize before creating resources:

```bash
python3 <grade-loop-dir>/scripts/run_state.py init \
  --path <external-state.json> --run-id <unique-kebab-case-id> \
  --repo-root <stable-absolute-root> --target-branch <branch> \
  --current-sha <full-target-sha> --max-passes 2 \
  [--target-remote <remote-name>] \
  [--companion-repo <stable-companion-root>]
```

The default allows the initial delivery and one follow-up. Grade requires each
audit to reference a report-kind archive and nonempty history-kind archives.
Persist actionable planning before implementation and implementation before
entering delivery. The post-delivery grade supplies the post audit; completion
requires no major actionable findings, verified delivery, preserved artifacts,
and live restoration of the original Git inventory. Budget exhaustion with
remaining findings uses deferred status after the same cleanup gate. Blocked
runs retain their reason and unfinished work and remain resumable.

Nested invocations use their caller's helper, state, and ownership contract.
Never recapture a baseline on resume or replace it with remaining resources.
