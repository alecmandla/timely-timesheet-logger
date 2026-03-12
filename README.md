# Timely Timesheet Logger

A Claude Cowork skill that automates Timely timesheet logging by scanning Memory Tracker entries, matching them to projects via Monday.com, and committing matched time via browser automation.

## What This Does

If you use [Timely](https://timelyapp.com) for time tracking and [Monday.com](https://monday.com) for project management, this skill bridges the gap between passive time capture and structured project timesheets.

Timely's Memory Tracker records everything you do — every app, browser tab, terminal window, file edit. But those memories sit unassigned until someone manually clicks through and logs them to the right projects. This skill automates that tedious process by:

1. **Scanning** your Timely memories for a given day
2. **Matching** them against project-specific search terms stored in your Monday.com board
3. **Presenting** matches for your review (with the search terms and confidence levels shown)
4. **Committing** approved matches by clicking through the Timely UI via browser automation
5. **Tracking** everything in a local JSON file for reconciliation reports

## Prerequisites

- [Claude Desktop](https://claude.ai/download) with Cowork mode enabled
- A [Timely](https://timelyapp.com) account with Memory Tracker active
- A [Monday.com](https://monday.com) account connected as a Cowork MCP connector
- Google Chrome (required for browser automation)
- Claude's model set to **Opus** (required for reliable browser automation and multi-source reasoning)

### Monday.com Board Setup

Your Monday.com board needs the following columns (the setup wizard will help you create them if they don't exist):

| Column | Type | Purpose |
|--------|------|---------|
| Timely Project Name | Text | The exact project name as it appears in Timely's project dropdown |
| Client Name | Text | The client associated with the project (used for search term fallback) |
| Timesheet Search Terms | Text | Comma-separated terms the skill uses to match memories to this project |
| Ignorable Search Terms | Text | Comma-separated terms to exclude from matching (prevents false positives) |

Each row on your board represents a project. Only rows with a populated "Timely Project Name" column will be picked up by the skill.

### Search Terms — The Key Concept

The skill matches memories by **search terms**, not project names. A memory titled "looker-automation script running in terminal" matches the Acme project not because it says "Acme" but because `looker-automation` is a known search term for that project.

Good search terms are specific: tool names (`figma-acme`), file names (`launch-dashboard.js`), unique client identifiers (`acme.com`), repo names (`acme-redesign`). Bad search terms are generic: `chrome`, `slack`, `email`, `google`.

You manage search terms directly in your Monday.com board. The skill reads them fresh before each scan, so any changes you make are picked up immediately.

## Installation

1. Copy the `timely-timesheet-logger/` folder into your Cowork skills directory
2. Run the skill for the first time — it will detect that setup hasn't been completed and walk you through configuration
3. The setup wizard collects your Timely account ID, user ID, and Monday.com board details (it can auto-discover most of these)

After setup, a `data/config.json` file is created with your account-specific settings. This file is gitignored and never shared.

## How to Use It

### Daily Automated Mode (Scheduled)

Once you set up a schedule (the skill will prompt you), it runs automatically:

- **Every day at 10am** (configurable): Scans the previous day's memories, matches against search terms, presents results for approval, and commits approved entries
- **Every Monday at 11am** (configurable): Generates a weekly reconciliation report organized by project with daily breakdowns
- **First Monday of each month**: Runs a month-end validation sweep to catch any stragglers before invoicing

### Manual Prompts

You can invoke the skill anytime with natural language. Here are the most common prompts:

**Daily scan + commit:**
> "Update my timesheet"

> "Log my timely hours"

> "Scan my memories"

These trigger a scan of the previous day's memories and commit approved matches.

**Historical/catch-up scan:**
> "Update my timesheet for February"

> "Scan Feb 11 to Feb 21"

> "Catch up on timesheets for last week"

These run the daily scan+commit flow for each day in the specified range. Useful for first-time runs or catching up after time away.

**Weekly reconciliation:**
> "Run a reconciliation for this week"

> "Show me my timesheet summary for last week"

Generates a report from the tracking file — no browser automation needed.

### Adding a New Project Mid-Month (Ad-Hoc Reconciliation)

This is a common scenario: you realize at the end of the month that a project wasn't being tracked. Here's how to handle it:

1. **Add the project to your Monday.com board** — fill in the Timely Project Name, Client Name, and Timesheet Search Terms columns
2. **Run a historical scan for the month:**

> "Update my timesheet for February"

or

> "Scan February 1 to February 28"

The skill will:
- Load the updated project list from Monday.com (now including your new project)
- Scan each day of the month in Timely
- **Only find unlogged memories** — anything already committed in previous daily passes is already logged in Timely and won't appear again
- Match against the new project's search terms
- Present only the new matches for your approval

You do NOT need to re-commit previously logged entries. The Timely UI only shows unlogged memories in the Memory Tracker column, so the skill naturally filters out everything that's already been assigned.

**Example scenario:**
You add "Cloud Connect Analytics" to your Monday.com board on March 1st with search terms `cloud-connect, analytics-pipeline, cc-dashboard`. You then say:

> "Scan February for my timesheet"

The skill scans all 28 days of February. Days where you already committed Lightspeed or JDM entries won't show those again (they're already logged). But any memory from February containing `cloud-connect`, `analytics-pipeline`, or `cc-dashboard` that was never assigned will surface for your review.

## Operating Modes Summary

| Mode | Trigger | What It Does | Browser Needed? |
|------|---------|-------------|:---:|
| Daily Scan + Commit | Schedule or "update my timesheet" | Scans yesterday's memories, matches, commits | Yes |
| Historical Scan | "Scan [date range]" | Same as daily but for a date range | Yes |
| Weekly Reconciliation | Schedule (Mondays) or "run reconciliation" | Report of committed time by project/day | No |
| Month-End Validation | Auto on first Monday of month | Full-month sweep for stragglers | Yes |
| Ad-Hoc Project Backfill | "Scan [month] for my timesheet" after adding a project | Finds unlogged entries for newly mapped projects | Yes |

## Configuration

After setup, your `data/config.json` controls behavior. Key settings:

| Setting | Default | Description |
|---------|---------|-------------|
| `schedule.daily_scan_time` | `10:00` | When the daily scan runs |
| `schedule.weekly_commit_day` | `monday` | Day of the week for reconciliation reports |
| `schedule.weekly_commit_time` | `11:00` | When the reconciliation report runs |
| `preferences.confidence_threshold` | `low` | Minimum match confidence to present (low/medium/high) |
| `preferences.skip_weekends` | `false` | Whether to skip scanning weekend days |

See `references/config-schema.md` for the full schema.

## File Structure

```
timely-timesheet-logger/
├── SKILL.md                          # Main skill instructions (Claude reads this)
├── README.md                         # This file
├── .gitignore                        # Excludes user-specific data
├── activity-logger/
│   ├── SKILL.md                      # Activity logger sub-skill instructions
│   ├── CLAUDE.md                     # Global Claude instructions for logging (gitignored, user-specific paths)
│   └── CLAUDE.md.template            # Template for generating CLAUDE.md during setup
├── data/
│   ├── config.json                   # Your account settings (gitignored)
│   ├── weekly-tracking.json          # Running log of scans and commits (gitignored)
│   └── activity-log.txt              # Claude session activity log (gitignored)
└── references/
    ├── setup-guide.md                # Onboarding flow details
    ├── config-schema.md              # Full config file schema
    ├── tracking-approach.md          # Why we use local JSON tracking
    ├── timely-ui-patterns.md         # Browser automation DOM selectors and workflows
    └── activity-log-integration.md   # How activity log cross-references generic Timely entries
```

## How the Matching Works

1. Before each scan, the skill reads your Monday.com board to build a project registry with search terms
2. For each day being scanned, it extracts all unlogged memory entries from Timely's UI via JavaScript
3. Each memory's title is checked against every project's search terms (case-insensitive substring match)
4. Matches are assigned a confidence level:
   - **High**: Unique, specific term that matches only one project
   - **Medium**: General term that matches one project but could be ambiguous
   - **Low**: Match on a broad term like a client name
   - **Ambiguous**: Memory matches search terms from two or more projects (flagged for manual review)
5. All matches are presented to you with the search term that triggered each match, so you can verify
6. You approve or reject each match before anything is committed

## Safeguards

- **Never commits without your approval** — every match is reviewed first
- **Never modifies existing logged entries** — only processes unlogged memories
- **Always shows search terms** — you can see exactly why each entry was matched
- **Always shows confidence levels** — you know how strong each match is
- **If the UI looks unexpected** — the skill takes a screenshot and stops rather than clicking blindly

## Troubleshooting

**"No projects have Timely project names set up yet"**
Add the Timely project name to at least one item on your Monday.com board, then run again.

**Very low match rate (<5%)**
You probably need to map more projects in Monday.com or add more specific search terms. Check the unmatched entries in your reconciliation reports for patterns.

**Browser automation fails or clicks the wrong thing**
Timely's CSS class names contain hashed suffixes that change when they deploy updates. If selectors stop working, the skill falls back to `data-testid` attributes and DOM structure traversal. If that also fails, take a screenshot and report the issue.

**Entries are grouped unexpectedly**
Timely sometimes auto-groups multiple memories when you click one. The skill detects this and removes extras, but if it looks wrong, cancel and try again.

## Technical Notes

- The skill uses **two browser tool systems**: Control Chrome (for fast sequential scanning) and Claude in Chrome (for screenshot-verified commits). See `references/timely-ui-patterns.md` for details.
- Timely is a React SPA — standard accessibility tools (`read_page`, `find`) return empty results. All DOM interaction uses `javascript_tool` and `execute_javascript`.
- Memory entry CSS selectors contain hashed suffixes that may change on Timely deploys. The skill includes fallback strategies using `data-testid` attributes.

## License

MIT
