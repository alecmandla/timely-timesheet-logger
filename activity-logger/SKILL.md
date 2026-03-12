---
name: activity-logger
description: Automatically log what Claude is working on during every Cowork and Claude Code session. Creates a timestamped activity journal that the timesheet-logger skill uses to resolve generic Timely entries (like "Claude" or "Zoom") into specific project work. Works via CLAUDE.md global instructions that run a single bash command at session start.
---

# Activity Logger

You are a quiet, diligent note-taker. Your job is to capture *what was worked on* so the timesheet system can later figure out which project that time belonged to.

## Why This Exists

Timely's Memory Tracker sees app-level activity: "Claude — 45 min", "Zoom — 30 min". But it can't see *inside* those apps. This logger fills the gap by recording what Claude was actually doing — which project, which task, which client — so the timesheet-logger skill can cross-reference timestamps and assign time correctly.

## How It Works

The logging happens via CLAUDE.md instructions placed at two levels:
- `~/.claude/CLAUDE.md` — picked up by every Claude Code session
- `/Users/REDACTED_USERNAME/Documents/REDACTED_WORKSPACE/CLAUDE.md` — picked up by Cowork sessions rooted in REDACTED_WORKSPACE

Both instruct Claude to run a single `echo >>` bash command before doing anything else, appending one line to the activity log.

## Log Format

Plain text, one line per entry, pipe-delimited:

```
YYYY-MM-DD HH:MM | session_type | summary | projects | search_terms
```

Fields:
- **timestamp** — when the work block started
- **session_type** — `cowork` or `claude-code`
- **summary** — 1-sentence description of what was done
- **projects** — comma-separated project names or codenames
- **search_terms** — comma-separated specific keywords (repo names, tool names, client names, ticket IDs, file names)

Example lines:
```
2026-03-04 14:30 | cowork | Building activity logger for timesheet automation | Timely Timesheet Logger | timely,timesheet,activity-logger,SKILL.md
2026-03-04 15:45 | claude-code | Debugging BigQuery pipeline for example inventory sync | Example Project Alpha | bigquery,example-alpha,inventory-sync,etl
2026-03-04 16:20 | cowork | Reviewing Monday.com board structure for Acme project | Acme Website Redesign | acme,monday,board-structure
```

## Log File Location

```
/Users/REDACTED_USERNAME/Documents/REDACTED_WORKSPACE/Cowork_Skills/update_timesheet/timely-timesheet-logger/data/activity-log.txt
```

This is a plain text file. Each `echo >>` appends a new line. No JSON parsing, no file locking, no complexity.

## What Makes Good Search Terms

The timesheet logger matches these terms against Timely memory descriptions. Think like a grep:

**Good**: `example-etl-tool`, `example-alpha-dms`, `PROJ-1234`, `feature/universal-linking`, `acme-redesign.figma`
**Bad**: `code`, `meeting`, `email`, `working`, `stuff`

**Key heuristic**: If the term would match only ONE project in a list of 20, it's a good term.

## Integration with Timesheet Logger

The timesheet logger reads this log during Phase 3.5 (Activity Log Cross-Reference). When it encounters a generic Timely memory like "Claude — 45 min (10:15 AM - 11:00 AM)", it:

1. Parses the activity log for lines where the timestamp overlaps (±15 min)
2. Matches the search_terms against the project registry from Monday.com
3. Assigns the Timely entry to the matched project

See [references/activity-log-integration.md](../references/activity-log-integration.md) for the full algorithm.

## Privacy

- Never log passwords, API keys, or secrets
- Summarize, don't transcribe — the log reads like a work journal, not a surveillance transcript
- If the user says "don't log this" or "off the record", skip that work block
