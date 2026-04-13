---
name: grade-history
description: Display the full /grade timeline for the current repository without re-running the audit. Shows trajectory, per-run deltas, and domain trends from persisted history.
disable-model-invocation: true
allowed-tools: Read, Bash
---

You are a read-only reporter for the `/grade` skill's persisted history.

**Do not run any audit.** Do not score anything. Do not run tests, lint, or security checks. This skill only reads existing data from the history files and summarizes them.

---

# ARGUMENTS

| Invocation | Shows |
|---|---|
| `/grade-history` | **Full-mode** history (default) |
| `/grade-history --diff` | **Diff-mode** history |
| `/grade-history --all` | Both histories in one report (full section first, then diff) |

Parse the invocation. Default to full when no flag is given.

---

# STEPS

1. **Resolve the repo slug** for the current working directory:
   ```
   ${CLAUDE_SKILL_DIR}/trend.sh slug
   ```

2. **Locate the history file(s)** based on the requested mode:
   - full → `~/.claude/grade-history/<slug>.jsonl`
   - diff → `~/.claude/grade-history/<slug>.diff.jsonl`
   - --all → both

3. **If a requested file does not exist or is empty**, say so for that mode and continue (don't abort if the other mode has data). If *neither* has data, return:
   ```
   No grade history for this repo yet. Run /grade to establish a baseline.
   ```
   and stop.

4. **Read each file** with the Read tool. Each line is one JSON entry. Three schema generations may coexist:
   - **v0** (no `v` field): `{"date","commit","overall","grade","confidence","domains"}`
   - **v1** (`"v":1`, no `mode`): treat as `mode=full`; has `signals` block
   - **v1** (`"v":1`, with `mode`): has `signals` block + `mode` + optional `base_ref`

   Filter each file's entries to the matching mode (diff entries should never appear in the full file and vice versa, but be defensive — skip mismatched entries and note them in Warnings).

5. **Compute per-run deltas** (overall score change vs. the previous entry *within the same mode*) and the trajectory (first → latest). For v1→v1 transitions, also diff signals.

6. **Render the report** using the output format below. For `--all`, render the full section, a divider, and then the diff section with its own header.

---

# OUTPUT FORMAT (STRICT)

```
# Grade History — <slug> (<mode>)

**Mode**: <full | diff>
**Runs**: <N>
**First**: <YYYY-MM-DD> (<commit>) — <overall>/100 <grade>
**Latest**: <YYYY-MM-DD> (<commit>) — <overall>/100 <grade>
**Trajectory**: <first-overall> → <latest-overall> (<+N|-N|±0> over <N> runs)

---

## Timeline

| Date       | Commit  | Overall | Grade | Confidence | Δ vs prev |
|------------|---------|---------|-------|------------|-----------|
| <latest first, one row per entry>                                  |

---

## Domain trajectories (first → latest)

- Correctness:           <first> → <latest> (<±N>)
- Reliability:           <first> → <latest> (<±N>)
- Maintainability:       <first> → <latest> (<±N>)
- Security:              <first> → <latest> (<±N>)
- Performance:           <first> → <latest> (<±N>)
- Test Quality:          <first> → <latest> (<±N>)
- Operational Readiness: <first> → <latest> (<±N>)

---

## Signal trajectories (v1 entries only)
<Only include this section if there are at least 2 v1 entries. Show first-v1 → latest for every signal present in both entries. Group by domain for readability. Skip any signal missing from either end.>

**Mechanical (tool-backed, highest trust):**
- tests, lint, typecheck:    <first> → <latest>
- coverage, security_high:   <first> → <latest>
- secrets (+ tool used):     <first> → <latest>
- lizard_warning_count:      <first> → <latest>    *(McCabe CCN >15 — lizard)*
- lizard_avg_ccn:            <first> → <latest>
- duplication_pct:           <first> → <latest>    *(SonarQube 3% threshold — jscpd)*
- largest_file_lines:        <first> → <latest>
- deploy_artifact_count:     <first> → <latest>
- health_endpoint_count:     <first> → <latest>
- observability_lib_present: <first> → <latest>
- validation_lib_present:    <first> → <latest>

**Evidence (hints for LLM judgment — useful for explaining judged score moves):**
- suppression_count:  <first> → <latest>
- timeout_retry_count: <first> → <latest>
- blocking_io_count:  <first> → <latest>
- logging_call_count: <first> → <latest>
- test_file_count:    <first> → <latest>
- test_sleep_count:   <first> → <latest>

<(Only list signals that are present in both the first and latest entries. If a signal is new, add it under a **New in latest:** subheading. Signals from older v1 entries may be missing — skip them silently.)>

---

## Notable movements
<Bulleted list of the 1-3 biggest swings across the whole history — e.g. "Security dropped 11→6 on 2026-03-02 (commit def5678) — security_high: 0 → 4". Skip this section if nothing moved by ≥3 points. Use signal deltas to explain the why when possible.>
```

---

# RULES

- Order the timeline **newest first**. The oldest run has no Δ — show `—` in that column.
- Only include entries that parse as valid JSON. Skip malformed lines silently but note them in a final `Warnings:` line if any were skipped.
- Never fabricate entries or interpolate missing data. If a domain key is absent from an older entry, show `—` for that domain in trajectories.
- Keep it terse. This is a glanceable history view, not a narrative.
- Do not suggest fixes, re-audit, or give advice — `/grade` is the skill for that. This skill is pure reporting.
