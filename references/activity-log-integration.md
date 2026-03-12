# Activity Log Integration

## Overview

The activity log is a plain text file written by Claude sessions (Cowork, Claude Code) that records what was being worked on with timestamps. The timesheet logger uses this to resolve generic Timely memory entries like "Claude — 45 min" or "Zoom — 30 min" into specific project matches.

## File Location

Configured in `config.json` under `activity_log.path`. Default: `data/activity-log.txt` (relative to the skill's root directory).

## Log Format

One line per entry, pipe-delimited:

```
YYYY-MM-DD HH:MM | session_type | summary | projects | search_terms
```

Example:
```
2026-03-04 14:30 | cowork | Building activity logger for timesheet automation | Timely Timesheet Logger | timely,timesheet,activity-logger,SKILL.md
2026-03-04 15:45 | claude-code | Debugging BigQuery pipeline for inventory sync | Example Project Alpha | bigquery,example-alpha,inventory-sync,etl
```

## Parsing

Split each line on ` | ` (space-pipe-space) to get 5 fields:
1. `timestamp` — parse as `YYYY-MM-DD HH:MM`
2. `session_type` — `cowork` or `claude-code`
3. `summary` — free text description
4. `projects` — comma-separated project names
5. `search_terms` — comma-separated keywords

## How It Works in Phase 3.5

During the daily scan, after the standard search-term matching pass, run a **second pass** for any unmatched entries that have generic app names.

### Generic App Detection

An entry is "generic" if its description matches ONLY an application name with no project-specific text:
- `Claude` / `Claude.ai` / `Anthropic`
- `Zoom` / `Google Meet` / `Microsoft Teams`
- `Terminal` / `iTerm` / `Warp`
- `VS Code` / `Cursor` / `Vim`

### Cross-Reference Algorithm

For each generic Timely entry:

1. **Extract the time window** from the Timely memory (start time, end time)
2. **Parse the activity log** and find lines where the timestamp falls within the Timely memory's time window (±`config.activity_log.time_tolerance_min` minutes, default 15)
3. **Filter by session type**:
   - "Claude" Timely entries → match `cowork` or `claude-code` log lines
   - "Terminal"/"VS Code" entries → match `claude-code` log lines
   - "Zoom"/"Meet" entries → skip to Calendar fallback (see below)
4. **Match search_terms** from the activity log line against the project registry (search terms from Monday.com)
5. **If a project match is found**, assign the Timely entry to that project

### Confidence Levels

- **High**: Activity log search_terms contain a unique term that maps to exactly one project
- **Medium**: Activity log projects field names a project directly, but no search term match
- **Low**: Only a partial or ambiguous match

### Zoom/Meeting Entries (Calendar Fallback)

For generic "Zoom" or "Meet" entries, the activity log won't help (Claude wasn't in the meeting). Instead:

1. Query Google Calendar for the time window
2. Match the meeting title against project search terms
3. If Fireflies is connected, scan transcript keywords

### Multiple Matches

If the time window overlaps multiple activity log entries for different projects:
- Present both candidates to the user
- Let the user decide the assignment
- Flag in the report as "split session"

### No Match Found

If neither search terms nor the activity log produce a match:
- Log the entry as "unresolved" in the tracking file
- Include it in the reconciliation report
- Suggest the user add search terms or check project mappings

## Example Flow

```
Timely Memory: "Claude — 45 min (10:15 AM - 11:00 AM)" on 2026-03-04
  → Standard search: No match (description is just "Claude")
  → Activity log line found:
    "2026-03-04 10:12 | cowork | Designed activity logging skill | Timely Timesheet Logger | timely,timesheet,activity-logger"
  → Monday.com match: "timely" matches project "Internal Tools"
  → Result: Assign to "Internal Tools" with HIGH confidence
```

```
Timely Memory: "Zoom — 30 min (2:00 PM - 2:30 PM)" on 2026-03-04
  → Standard search: No match
  → Activity log: No matching line (Claude wasn't in the Zoom call)
  → Calendar fallback: Google Calendar shows "Example Project Alpha Weekly Sync" at 2:00 PM
  → Monday.com match: "example-alpha" matches project "Example Project Alpha"
  → Result: Assign to "Example Project Alpha" with HIGH confidence
```
