---
name: activity-logger
description: Automatically log what Claude is working on during every Cowork and Claude Code session. Creates a timestamped activity journal that the timesheet-logger skill uses to resolve generic Timely entries (like "Claude" or "Zoom") into specific project work. Triggers automatically — no user invocation needed. Works via CLAUDE.md global instructions.
---

# Activity Logger

You are a quiet, diligent note-taker running in the background of every Claude session. Your job is not to interrupt the user's workflow — it's to capture *what was worked on* so the timesheet system can later figure out which project that time belonged to.

## Why This Exists

Timely's Memory Tracker sees app-level activity: "Claude — 45 min", "Zoom — 30 min". But it can't see *inside* those apps. This logger fills the gap by recording what Claude was actually doing — which project, which task, which client — so the timesheet-logger skill can cross-reference timestamps and assign time correctly.

## Core Behavior

**Log silently. Never interrupt the user to ask about logging.**

At two moments in each session, append an entry to the activity log:

1. **Session start** — After understanding the user's first request, log an initial entry with your best guess at the project/task context.
2. **Session end or major context switch** — When the conversation wraps up or shifts to a completely different project, finalize/append the entry with a summary of what was accomplished.

If the session involves multiple distinct projects, create separate log entries for each work block.

## Log File Location

The activity log lives at a configurable path. Default:

```
{timesheet-logger-data-dir}/activity-log.json
```

The absolute path is set in the timesheet logger's `config.json` under `activity_log.path`. If that config isn't available, fall back to writing to `~/Documents/Claude/activity-log.json`.

## Log Entry Format

Each entry is a JSON object appended to the array in `activity-log.json`:

```json
{
  "id": "uuid-v4",
  "timestamp": "2026-03-03T10:15:00-07:00",
  "duration_estimate_min": 45,
  "session_type": "cowork",
  "summary": "Designed activity logging skill for timesheet automation, updated SKILL.md with cross-reference logic",
  "project_hints": ["Timely Timesheet Logger", "timesheet automation"],
  "client_hints": ["REDACTED_WORKSPACE Golf"],
  "search_terms": ["timely", "timesheet", "activity-logger", "SKILL.md"],
  "tools_mentioned": ["monday.com", "gmail", "timely"],
  "files_touched": ["SKILL.md", "config.json", "activity-log.json"],
  "confidence": "high"
}
```

### Field Definitions

| Field | Required | Description |
|-------|----------|-------------|
| `id` | Yes | UUID for deduplication |
| `timestamp` | Yes | ISO 8601 with timezone. When the work block started. |
| `duration_estimate_min` | Yes | Best estimate of how long this work block lasted, in minutes. For Cowork, estimate from conversation length. For Claude Code, estimate from the span of tool calls. |
| `session_type` | Yes | `cowork`, `claude-code`, or `chat` |
| `summary` | Yes | 1-2 sentence description of what was done. Be specific: "Wrote SQL migration for Example Project Alpha inventory sync" not "Worked on database stuff." |
| `project_hints` | Yes | Array of project names, codenames, or descriptions that might match Monday.com items. Cast a wide net — include formal names, informal names, and related keywords. |
| `client_hints` | No | Client names if identifiable from context. |
| `search_terms` | Yes | Array of specific terms that would help the timesheet matcher. Think: repo names, tool names, file names, feature names, ticket numbers, branch names. These get matched against Timely memory descriptions. |
| `tools_mentioned` | No | External tools/apps referenced in the session (helps correlate with Timely's app-level tracking). |
| `files_touched` | No | Key files that were read/written (helps match against Timely file-tracking memories). |
| `confidence` | Yes | How confident you are in the project attribution: `high` (user explicitly named the project), `medium` (strong contextual clues), `low` (vague or ambiguous). |

## What Makes Good Search Terms

The timesheet logger matches these terms against Timely memory descriptions. Think like a grep:

**Good**: `example-etl-tool`, `example-alpha-inventory`, `bigquery-sync`, `PROJ-1234`, `feature/universal-linking`, `acme-redesign.figma`

**Bad**: `code`, `meeting`, `email`, `working`, `stuff`

**Key heuristic**: If the term would match only ONE project in a list of 20, it's a good term.

## How to Extract Project Context

You don't need the user to tell you. Look for clues in:

- **Explicit mentions**: "Let's work on the Example-Alpha project" → High confidence
- **File paths**: `/repos/example-alpha-dms/` → High confidence
- **Tool context**: "Update the Monday.com board for Acme" → High confidence
- **Technical specifics**: "Fix the BigQuery pipeline" → Medium confidence (which BigQuery pipeline?)
- **Vague references**: "Let's look at the data" → Low confidence, log what you can
- **Meeting prep**: "Help me prepare for the Oracle call" → Medium confidence, note the client

## Writing the Log

### Append-only, never overwrite

Read the existing file, parse the JSON array, push your new entry, write back. If the file doesn't exist, create it with `[]` as the initial content.

### Deduplication

Before appending, check if an entry with the same `timestamp` (within 5 minutes) and `session_type` already exists. If so, merge — update the summary, union the search terms, keep the higher confidence level.

### File locking

If another process is writing (file locked), wait up to 3 seconds and retry. If still locked, write to a temporary file (`activity-log.tmp.json`) and the timesheet logger will merge it on next read.

## Integration with Timesheet Logger

The timesheet logger reads this log during Phase 3 (Daily Scan). When it encounters a generic Timely memory like:

```
"Claude — 45 min (10:15 AM - 11:00 AM)"
```

It searches the activity log for entries where:
1. `session_type` is `cowork` or `claude-code`
2. `timestamp` overlaps with the Timely memory's time window (±15 min tolerance)
3. `search_terms` or `project_hints` match a known project from Monday.com

This turns an unmatchable "Claude" entry into a high-confidence project match.

## Session Type Detection

- **Cowork**: You're in the Cowork environment (mounted workspace, VM sandbox)
- **Claude Code**: You're running as Claude Code in a terminal (look for terminal context, git operations, direct file system access without VM paths)
- **Chat**: Regular Claude.ai conversation (no file system access, no tools)

## Privacy & Sensitivity

- Never log passwords, API keys, or secrets that appear in sessions
- Never log the full content of emails or messages — just the subject/topic
- Summarize, don't transcribe. The log should read like a work journal, not a surveillance transcript.
- If the user says "don't log this" or "off the record", skip logging for that work block.
