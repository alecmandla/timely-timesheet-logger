# Activity Log Integration

## Overview

The activity log is a JSON file written by Claude sessions (Cowork, Claude Code) that records what was being worked on with timestamps. The timesheet logger uses this to resolve generic Timely memory entries like "Claude — 45 min" or "Zoom — 30 min" into specific project matches.

## File Location

Configured in `config.json` under `activity_log.path`. Default: `data/activity-log.json` (relative to the skill's root directory).

## How It Works in Phase 3

During the daily scan, after the standard search-term matching pass, run a **second pass** for any unmatched entries that have generic app names:

### Generic App Detection

An entry is "generic" if its description matches ONLY an application name with no project-specific text:
- `Claude` / `Claude.ai` / `Anthropic`
- `Zoom` / `Google Meet` / `Microsoft Teams`
- `Terminal` / `iTerm` / `Warp`
- `VS Code` / `Cursor` / `Vim`

These entries would normally be skipped because they don't contain any project search terms.

### Cross-Reference Algorithm

For each generic entry:

1. **Extract the time window** from the Timely memory (start time, end time)
2. **Query the activity log** for entries where:
   - `timestamp` falls within the memory's time window (±15 min tolerance)
   - `session_type` matches the expected type:
     - "Claude" → `cowork` or `claude-code`
     - "Zoom"/"Meet" → check Google Calendar instead (see below)
     - "Terminal"/"VS Code" → `claude-code`
3. **Match activity log `search_terms`** against the project registry (same search terms from Monday.com)
4. **If a match is found**, assign the entry to that project with confidence level:
   - Activity log confidence `high` + search term match → **High** confidence
   - Activity log confidence `medium` + search term match → **Medium** confidence
   - Activity log confidence `low` or only `project_hints` match → **Low** confidence

### Zoom/Meeting Entries

For generic "Zoom" or "Meet" entries, the activity log alone won't help (Claude wasn't in the meeting). Instead:

1. **Query Google Calendar** for the time window
2. Match the meeting title against project search terms
3. If Fireflies is connected, check for a transcript and scan for project keywords

### Multiple Activity Log Matches

If the time window overlaps multiple activity log entries for different projects:
- Split the Timely duration proportionally based on `duration_estimate_min` from each activity log entry
- Flag for user review with both candidate projects shown
- Let the user decide the split

### No Match Found

If neither search terms nor the activity log produce a match:
- Log the entry as "unresolved" in the tracking file
- Include it in the reconciliation report with the raw description
- Suggest the user add search terms or check if a project mapping is missing

## Config Addition

Add to `config.json`:

```json
{
  "activity_log": {
    "path": "data/activity-log.json",
    "enabled": true,
    "time_tolerance_min": 15,
    "calendar_fallback": true
  }
}
```

## Example Flow

```
Timely Memory: "Claude — 45 min (10:15 AM - 11:00 AM)" on 2026-03-03
  → Standard search: No match (description is just "Claude")
  → Activity log lookup: Entry found at 10:12 AM, session_type: cowork
    summary: "Designed activity logging skill for timesheet automation"
    search_terms: ["timely", "timesheet", "activity-logger"]
    project_hints: ["Timely Timesheet Logger"]
  → Monday.com match: "timely" matches project "Internal Tools" with search term "timely"
  → Result: Assign to "Internal Tools" with HIGH confidence
```

```
Timely Memory: "Zoom — 30 min (2:00 PM - 2:30 PM)" on 2026-03-03
  → Standard search: No match (description is just "Zoom")
  → Activity log: No entry (Claude wasn't in the Zoom call)
  → Calendar fallback: Google Calendar shows "Example Project Alpha Weekly Sync" at 2:00 PM
  → Monday.com match: "example-alpha" matches project "Example Project Alpha"
  → Result: Assign to "Example Project Alpha" with HIGH confidence
```
