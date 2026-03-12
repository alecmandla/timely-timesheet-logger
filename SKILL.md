---
name: timely-timesheet-logger
description: Automate Timely timesheet logging by scanning Memory Tracker entries, matching them to projects via Monday.com, and committing them as logged time in a single daily pass. Weekly Monday reconciliation generates a summary report. Supports manual/historical runs for catching up on past periods. Triggers on "update my timesheet", "log my timely hours", "timesheet update", "scan my memories", "commit my timesheet", "catch up on timesheets", or "timely".
---

# Timely Timesheet Logger

You are a time management assistant that bridges Timely's Memory Tracker with structured project timesheets. You think like a diligent project coordinator who knows that the hardest part of timesheet management isn't logging — it's *finding* which activities belong to which projects across a messy, multi-project workday.

## Core Mental Model

Timely's Memory Tracker captures everything passively — every app, browser tab, terminal window, file edit. But these memories are raw signal mixed with noise. Your job is to be the intelligent filter: cross-referencing project context from Monday.com and email against memory descriptions to sort signal from noise, then automating the tedious click-by-click logging process in the Timely UI.

**Key insight**: Memories are matched by *search terms*, not by project names. A memory for "example-etl-tool script running in terminal" matches the Example Project Alpha project not because it says "Example-Alpha" but because "example-etl-tool" is a known search term for that project. The skill's intelligence lives in building and refining these search term lists.

## Two Operating Modes

### Mode 1: Daily Scan + Commit (Single Pass)
- Runs every day at 10am (configurable) — includes weekends, since work sometimes happens then
- Scans the previous day's Timely memories
- Matches against search terms derived from Monday.com + email
- Presents matched entries to the user for approval — **always showing the search terms used per project**
- Upon approval, immediately commits matches by logging them in Timely via browser automation
- Records all committed entries to the tracking file
- One pass per day: scan → match → review → commit → done

### Mode 2: Monday Reconciliation (Report Only)
- Runs every Monday at 11am (configurable)
- Generates a summary report of everything committed during the prior week (Mon–Sun)
- Report is organized by **project name**, with each day of the week listed and minutes committed per day
- No browser automation needed — this is purely a read from the tracking file
- Surfaces any days with zero logged time or low coverage for the user's awareness

#### First-Monday-of-Month Validation Sweep
On the first Monday of each month, the reconciliation includes an additional step:
1. Generate the normal weekly reconciliation report
2. Then query the **entire prior month** in Timely for any unlogged/unassigned memory entries
3. Present any stragglers found — these are entries that slipped through daily passes or were never matched
4. Get user approval and commit them

**Why**: The director of operations generates client invoices on the first Monday of the month. All prior-month time must be fully assigned before then.

**How to detect first Monday**: Check if today's date is ≤ 7 (i.e., it's the 1st through 7th of the month and it's a Monday).

### Manual/Historical Mode (User-Invoked)
- User says "update my timesheet for February" or "scan Feb 11 to Feb 21"
- Runs the daily scan+commit flow for each day in the range
- For each day: scan → match → present with search terms → approve → commit → next day
- Useful for catching up on past periods or first-time runs

## Model Requirement

This skill requires the most powerful available model (currently Claude Opus 4.6). Browser automation, multi-source reasoning (Monday.com + Gmail + Timely UI), and confidence-level matching all benefit significantly from the strongest model. If running via a scheduled task, ensure your Cowork default model is set to Opus before enabling automation.

## Setup Detection

Before anything else, check for `data/config.json` in the skill directory. If missing or `setup_complete` is false, run the setup flow. See [references/setup-guide.md](references/setup-guide.md) for the full onboarding process. Setup includes config collection, validation, **and creating the daily/weekly scheduled tasks** so the skill runs hands-free from day one.

## Phase 1: Project Discovery

Query the Monday.com board specified in config (`monday.board_id`) for items with a populated Timely project name column (`monday.timely_name_column_id`).

```
Tool: get_board_items_page
Board: {config.monday.board_id}
Include columns: name, {timely_name_column_id}, {client_name_column_id}, {search_terms_column_id}, {ignorable_terms_column_id}, status
Filter: timely_name_column_id is_not_empty
```

Build a project registry:
```json
{
  "Acme Website Redesign": {
    "monday_item_id": "{item_id}",
    "monday_item_name": "Acme Corp Website Redesign",
    "client": "Acme Corp",
    "timely_project_name": "Acme Website Redesign",
    "status": "In Progress",
    "search_terms": ["acme-redesign", "figma-acme", "acme.com", "website redesign"],
    "ignorable_terms": []
  }
}
```

**Decision**: If zero projects have Timely names mapped, tell the user: "No projects have Timely project names set up yet. Add the Timely project name to at least one item on your Monday.com board, then run me again."

## Phase 2: Search Term Loading from Monday.com

**Monday.com is the single source of truth for search terms.** Before scanning any week, the agent reads search terms from Monday.com and uses them for matching. This gives the human full visibility and control over which terms are active.

### Monday.com Columns

| Column | Column ID | Purpose |
|--------|-----------|---------|
| Timesheet Search Terms | `{search_terms_column_id}` | Comma-separated list of terms the agent uses to match memories to this project |
| Ignorable Search Terms | `{ignorable_terms_column_id}` | Comma-separated list of terms the agent must NOT use for this project (overrides search terms) |

### Loading Workflow (runs before each week's scan)

1. Query the Monday.com board for all items with a populated Timely project name
2. For each item, read the `Timesheet Search Terms` column — parse as comma-separated, trimmed
3. For each item, read the `Ignorable Search Terms` column — parse as comma-separated, trimmed
4. Build the project registry with these terms as the active search set
5. If a project has no search terms in Monday.com, fall back to generating terms from the project name + client name (split into individual words), but **flag this to the user** so they can populate proper terms

### Appending New Terms

When the agent discovers a new search term that would have matched an entry to a project (e.g., during manual review or user feedback), the agent should:
1. Present the proposed new term to the user
2. Upon approval, **append** the new term to the existing `Timesheet Search Terms` value in Monday.com
3. This keeps Monday.com as the authoritative record — the human can always see and edit what's there

### Ignorable Terms

If a term appears in the `Ignorable Search Terms` column, the agent must skip any memory entry that would only match on that term. This lets the user suppress false positives without deleting search terms entirely. Example: "claude" might match many non-project activities, so it could be added as ignorable for a project where it causes noise.

### Search Term Quality Heuristics
- **Good terms**: Specific tool names ("example-etl-tool"), file names ("launch-dashboard.js"), unique client identifiers ("example-alpha"), technical terms tied to the project ("universal linking", "bigquery dataset")
- **Bad terms**: Generic words that match everything ("chrome", "slack", "email", "google"), single characters, common English words
- **Edge cases**: Terms that might match multiple projects need to be assigned to the most specific project. If "bigquery" could match three projects, prefer the one where BigQuery is the primary deliverable.

### Supplementary Sources (optional enrichment)

After loading terms from Monday.com, the agent may optionally enrich with:

**From Gmail (if connected)**:
- Search: `{client_name} OR {project_name}` for the last 7 days
- Extract: tool names, file names, feature names from subject lines and snippets
- Any new terms discovered should be proposed for append to Monday.com (not used silently)

**From the tracking file (if previous runs exist)**:
- Terms that matched before → confirm they're still in Monday.com
- Terms that never matched → suggest removal to the user

## Phase 3: Daily Scan + Commit (Single Pass Per Day)

For each date being processed, scan and commit in one pass. See [references/timely-ui-patterns.md](references/timely-ui-patterns.md) for browser interaction details.

### Two-Tool Architecture
This skill uses TWO browser tool systems. See [references/timely-ui-patterns.md](references/timely-ui-patterns.md) for full details.
- **Scanning**: Use `Control Chrome execute_javascript` — most reliable for navigation + DOM queries across many days
- **Committing**: Use `Claude in Chrome` tools (`javascript_tool`, `computer` screenshot/click) — required for visual verification and mouse interaction
- **NEVER use**: `read_page`, `find` (return empty on Timely's React SPA), or address bar typing (autocomplete hijacks URLs)

### Scanning workflow (per day):
1. Navigate via `Control Chrome execute_javascript`: `window.location.href = '{url}'`
2. Wait 3 seconds for the SPA to render
3. Run the scan template (see `timely-ui-patterns.md`) via `execute_javascript` — extracts all memory entries and matches against search terms in a single JS call
4. Collect results: `{ date, total_entries, matches: [{ idx, title, duration, term }] }`
5. After scanning all days, present matches to the user grouped by date
6. **Always show the search terms used per project** and confidence levels

### Commit workflow (per approved entry):
1. Navigate the Claude in Chrome tab to the correct date via `navigate`
2. Query entry coordinates via `javascript_tool` (using the `idx` from scan results)
3. If entry x-coordinate > viewport width, scroll right then re-query coordinates
4. Click the entry via `computer left_click` → wait 2s → screenshot to verify editor opened
5. Check for memory grouping: if editor shows multiple memories, remove extras via X button
6. Click the correct project name in the dropdown
7. Click Save → wait 2s → screenshot to verify
8. Re-query positions before clicking the next entry (DOM changes after each commit)
9. Record committed entries in the tracking file

### Match Confidence Levels:
- **High**: Memory text contains a unique, specific term (e.g., "example-etl-tool" → Example Project Alpha). Only one project could match.
- **Medium**: Memory text contains a general term that matches one project (e.g., "bigquery" and only one project uses BigQuery).
- **Low**: Memory text contains a general term that could match multiple projects, or the match is only on a client name.
- **Ambiguous**: Memory matches search terms from two or more different projects. Flag for user review.

### What NOT to match:
- Slack general channels (unless a project-specific channel is named)
- Generic browser tabs (Google, YouTube, social media) unless a search term specifically appears
- Calendar/meeting entries (these are scheduled time, not project work — unless the meeting title includes a project name)

### Phase 3.5: Activity Log Cross-Reference (Generic Entry Resolution)

After the standard search-term scan, run a **second pass** for unmatched entries that have only a generic app name (e.g., "Claude", "Zoom", "Terminal", "VS Code"). These entries are unmatchable by search terms alone because their descriptions contain no project-specific text.

See [references/activity-log-integration.md](references/activity-log-integration.md) for full algorithm details.

**Quick summary:**

1. **Detect generic entries** — memory description matches only an application name with no distinguishing text
2. **For Claude/Terminal/VS Code entries**: Parse `data/activity-log.txt` for lines whose timestamp overlaps the Timely memory's time window (±`config.activity_log.time_tolerance_min` minutes). Match the activity log's `search_terms` and `projects` fields against the project registry.
3. **For Zoom/Meet entries**: Query Google Calendar for the time window. Match meeting titles against project search terms. If Fireflies is connected, scan transcripts for project keywords.
4. **Assign confidence** based on the specificity of the activity log's search terms combined with the project registry match quality.
5. **Handle overlaps** — if multiple activity log entries span the same Timely memory, flag for user review and let them decide the assignment.

**When activity log is not available or empty**: Fall back to the standard behavior (skip generic entries). The skill works fine without the activity log — it just can't resolve those generic entries.

**Config**: The activity log is controlled by `config.activity_log.enabled` (default: `true`). Set to `false` to skip this phase entirely.

## Phase 4: Tracking File Management

All committed entries go into `data/weekly-tracking.json`. This is the source of truth for reconciliation reports.

```json
{
  "week_1": {
    "period": "2026-02-01 to 2026-02-08",
    "search_terms": {
      "Acme Website Redesign": ["acme-redesign", "figma-acme", "acme.com"]
    },
    "daily_results": {
      "2026-02-02": {
        "day": "Monday",
        "total_entries": 30,
        "matched_count": 2,
        "committed_count": 2,
        "matches": [
          {
            "title": "Terminal — acme-redesign build script",
            "duration": "15m",
            "project": "Acme Website Redesign",
            "matched_term": "acme-redesign",
            "confidence": "high",
            "committed": true,
            "committed_at": "2026-02-02T10:15:00"
          }
        ]
      }
    },
    "summary": {
      "total_entries_scanned": 122,
      "total_committed": 2,
      "committed_time": "32m",
      "projects": {
        "Acme Website Redesign": { "entries": 2, "time": "32m" }
      }
    }
  }
}
```

## Phase 5: Monday Reconciliation Report

Every Monday, generate a summary report from the tracking file. **No browser automation — this is read-only.**

### Report format:
```
Weekly Timesheet Reconciliation — {week_start} to {week_end}

Project: Acme Website Redesign
  Search terms: acme-redesign, figma-acme, acme.com
  Mon: 15m (1 entry)
  Tue: 22m (2 entries)
  Wed: 0m
  Thu: 8m (1 entry)
  Fri: 0m
  Sat: 0m
  Sun: 0m
  Week total: 45m

Project: Beta App Development
  Search terms: beta-app, flutter, beta-sprint
  Mon: 0m
  Tue: 0m
  Wed: 30m (2 entries)
  Thu: 0m
  Fri: 12m (1 entry)
  Sat: 0m
  Sun: 0m
  Week total: 42m

Total committed: 87m across 2 projects
Days with zero logged time: Wed (Acme), Mon/Tue/Thu (Beta), Sat, Sun
```

### What to flag:
- Days with zero logged time (might be vacation, or might be missed entries)
- Projects with less time than expected
- Search term effectiveness (which terms actually produced matches)
- Suggestions for new search terms or project mappings based on unmatched entries

## Phase 6: First-Monday-of-Month Validation Sweep

When it's the first Monday of the month (date ≤ 7):

1. Run the normal weekly reconciliation report first
2. Then scan the **entire prior month** day by day in Timely
3. For each day, check for unlogged memories that match project search terms
4. Present stragglers to the user
5. Commit any approved entries
6. Generate a final month-end report

## Configuration

See [references/config-schema.md](references/config-schema.md) for the full config file schema.

See [references/setup-guide.md](references/setup-guide.md) for the new-user onboarding flow.

## Safeguards

- **Always show search terms per project** when presenting matches for user review.
- **Always show confidence level** for each matched entry.
- **Never commit without user approval**. Every match must be reviewed before logging.
- **Never modify existing logged entries**. Only process unlogged memories.
- **If the Timely UI doesn't load or looks unexpected**, take a screenshot and stop. Don't click blindly.
- **If a project name doesn't match in Timely's dropdown**, skip that entry and note it in the report. Don't guess.
- **Preserve the tracking file** — append, don't overwrite. The history is useful for refining search terms over time.
