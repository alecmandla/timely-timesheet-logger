# Timely Timesheet Logger — Changelog

All notable changes to the Timely Timesheet Logger skill are documented here, sorted with the most recent change first.

---

## 2026-03-12 — Project Sync & Cleanup

**What changed**: Cleaned up file inconsistencies that accumulated during development. Brought all files into sync so the repo is ready for public release.

- `activity-logger/CLAUDE.md` — Rewrote to match the plain text format (was still using old JSON format). Now generates the correct `echo >>` command targeting `activity-log.txt`.
- `SKILL.md` — Fixed Phase 3.5 cross-reference section: changed `activity-log.json` → `activity-log.txt`, updated field names from JSON keys to plain text pipe-delimited fields.
- `README.md` — Updated file structure to include `activity-logger/` subfolder and `activity-log-integration.md` reference.
- `.gitignore` — Removed dead entries for `activity-log.json` and `activity-log.tmp.json`. Added `PUBLISHING.md`.
- `references/config-schema.md` — Fixed `activity-log.json` → `activity-log.txt` file path reference.
- Deleted `data/activity-log.json` (empty dead file from old format).

**Also in this session**: Reviewed skill installation model (installed copy vs repo). Decided to uninstall the skill from Claude Desktop since scheduled tasks run from the repo path directly, avoiding version drift.

---

## 2026-03-12 — Activity Logger: JSON → Plain Text Migration

**What changed**: Replaced the JSON-based activity logging format with a simple plain text `echo >>` approach across all activity logger files.

**Why**: The JSON format (UUID entries, array parsing, `activity-log.json`) was fragile — it required Claude to parse and append to a JSON array, which is error-prone in bash. The plain text format uses a single `echo` command to append one pipe-delimited line per session to `activity-log.txt`. Simpler, more reliable, and already proven in production (the `activity-log.txt` file had real entries; the `activity-log.json` file was empty).

**Files updated**:
- `activity-logger/SKILL.md` — Rewrote from 132 lines (JSON format with complex entry schema) to 75 lines (plain text format with simple pipe-delimited lines)
- `activity-logger/CLAUDE.md.template` — Same migration, JSON → plain text template
- `references/activity-log-integration.md` — Rewrote cross-reference docs: added parsing instructions for plain text format, renamed Phase 3 → Phase 3.5, simplified confidence scoring, removed JSON-specific handling

**Format change**:
```
# Old (JSON, activity-log.json)
{"id": "uuid", "timestamp": "...", "session_type": "cowork", "search_terms": [...], ...}

# New (plain text, activity-log.txt)
2026-03-04 14:30 | cowork | Building activity logger | Project Name | search,terms,here
```

---

## 2026-03-03 — Week 3 Scan & Commits Complete (Feb 16–22)

**Results**: 610 entries scanned across 7 days. 2 matches found and committed, totaling 17 minutes, all to Example Project Alpha.

| Date | Day | Total Entries | Matches | Committed |
|------|-----|:---:|:---:|:---:|
| Feb 16 | Mon | 220 | 0 | — |
| Feb 17 | Tue | 114 | 1 | example-script.js (11m) |
| Feb 18 | Wed | 144 | 1 | Dashboard.Golf Data Sources for Example Golf (6m) |
| Feb 19 | Thu | 0 | 0 | — |
| Feb 20 | Fri | 130 | 0 | — |
| Feb 21 | Sat | 2 | 0 | — |
| Feb 22 | Sun | 0 | 0 | — |

**Files updated**: `data/weekly-tracking.json` (week_3 added), `CHANGELOG.md`

---

## 2026-03-03 — Week 2 Commits Complete (Feb 11–13)

**Results**: 14 entries committed across 3 days, totaling 151 minutes ($378.06), all to Example Project Alpha.

| Date | Entries | Minutes | Timesheet Total |
|------|:---:|:---:|:---:|
| Feb 11 | 7 | 70m | 5h 21m (incl. pre-existing) |
| Feb 12 | 3 | 43m | 43m |
| Feb 13 | 4 | 38m | 38m |

**Search term additions**: During review, user approved adding `example-etl-tool` and `example-script.js` as new search terms for Example Project Alpha. These captured 6 entries that would have been missed with original terms. Terms were added to Monday.com item REDACTED_MONDAY_ITEM_ID.

**Files updated**: `data/weekly-tracking.json` (week_2 added), `data/february-test-log.md` (Phase 2 results), `CHANGELOG.md`

---

## 2026-03-03 — Monday.com as Source of Truth for Search Terms

**What changed**: Search terms are now loaded from Monday.com before each scan, instead of being hardcoded in the skill or tracking files. Two new columns on the Cloud Connect Projects board (REDACTED_MONDAY_BOARD_ID) drive this:

- **Timesheet Search Terms** (`REDACTED_COLUMN_ID_1`): Comma-separated terms the agent uses to match Timely memories to a project. The human can view and edit these at any time.
- **Ignorable Search Terms** (`REDACTED_COLUMN_ID_2`): Comma-separated terms the agent must skip. Used to suppress false positives (e.g., "claude" matching non-project work).

**Why**: The agent was using search terms that weren't visible or editable by the human. For example, time spent in the Claude desktop app building example tooling wasn't being captured because "claude" wasn't a search term — and even if it were, it would need to be scoped carefully. Making Monday.com the single source of truth gives the human full control and visibility.

**Files updated**:
- `data/config.json` — Added `search_terms_column_id` and `ignorable_terms_column_id` to the monday config block
- `SKILL.md` — Rewrote Phase 2 (Search Term Generation → Search Term Loading from Monday.com), updated Phase 1 project discovery query to include new columns, updated project registry example
- `references/february-test-plan.md` — Updated project registry section to reference Monday.com-driven terms

**Monday.com changes**:
- Example Alpha Custom DMS Dashboards: Appended `example-alpha, ls 2.` to existing search terms
- Example Report Beta: Populated search terms `example-beta, example-beta-sub, example-beta, example-dashboard, example-daily`

---

## 2026-03-03 — Week 2 Scan Complete (Feb 9–15)

**Results**: 4 matches found, all Example Project Alpha (46 total minutes). No Example-Beta matches this week.

| Date | Day | Total Entries | Matches |
|------|-----|:---:|:---:|
| Feb 9 | Mon | 24 | 0 |
| Feb 10 | Tue | 0 | 0 |
| Feb 11 | Wed | 50 | 2 (Example Project Alpha 2.0 Demo Dashboard — 17m, 8m) |
| Feb 12 | Thu | 0 | 0 |
| Feb 13 | Fri | 42 | 2 (Re-Authorizing Example Retail — 12m, 9m) |
| Feb 14 | Sat | 0 | 0 |
| Feb 15 | Sun | 0 | 0 |

**Status**: ✅ All 14 entries committed. See "Week 2 Commits Complete" entry above.

---

## 2026-03-03 — Week 1 Commits Complete (Feb 2)

**Results**: 4 entries committed on Feb 2, totaling 32 minutes ($80).

| Entry | Duration | Project | Search Term |
|-------|:---:|---------|-------------|
| REDACTED_WORKSPACE/LS 2.2.2026 - Google Docs | 6m | Example Project Alpha | ls 2. |
| Example Dashboard Review - Fireflies.ai | 7m | Example Project Beta | example-dashboard |
| Dashboard.Golf Round Buckets for Example Golf Club | 10m | Example Project Beta | example-beta-sub |
| Example Client Beta Dashboard › Example Daily Report | 9m | Example Project Beta | example-beta |

**Files updated**: `data/weekly-tracking.json`, `data/february-test-log.md`

**Automation notes**: After each commit, element positions shift — must re-query via JavaScript before clicking the next entry. Entries near the right viewport edge may need horizontal scrolling.

---

## 2026-03-03 — Workflow Redesign: Single-Pass Daily Scan+Commit

**What changed**: Replaced the two-pass approach (scan all days → then go back to commit) with a single-pass-per-day workflow: scan → match → present → approve → commit immediately → record → next day.

**Why**: The two-pass approach required navigating to each day twice, doubling browser automation work and creating stale-state risks. Single-pass is simpler, faster, and easier to reason about.

**Also changed**: Weekly reconciliation became report-only (no browser automation). It reads from the tracking file and generates a summary organized by project name with daily minute breakdowns.

**Files updated**: `SKILL.md`, `references/february-test-plan.md`, `data/weekly-tracking.json` (structure)

---

## 2026-03-03 — Phase 0: DOM Discovery Complete

**What learned**: Timely's React SPA doesn't work with `read_page` or `find` browser tools. All DOM inspection must use `javascript_tool`. Memory entries live in `._memoryContainer_7imx7_8` elements with `._label_1ad4p_87` labels for title and duration.

**Key patterns documented**:
- Click memory → editor panel opens on left
- Click "Select Project" → search/dropdown → click project → Save
- Save button only becomes active (blue) after a project is selected
- Recent Projects appear at top of dropdown after first commit to that project
- URL sanitization needed: memory titles with URLs cause output blocking

**Files updated**: `references/timely-ui-patterns.md`, `data/february-test-log.md`

---

## 2026-03-03 — Week 1 Scan Complete (Feb 1–8)

**Results**: Only Feb 2 (Monday) had matching entries. Feb 1, 3–8 all had zero matches.

- Feb 2: 4 matches (32m) — 1 Example Project Alpha, 3 Example Client Beta
- Feb 1, 3–8: 0 matches each

**Search terms used**:
- Example Project Alpha: `example-alpha`, `dms`, `ls 2.`
- Example Project Beta: `example-beta`, `example-beta-sub`, `example-beta`, `example-dashboard`, `example-daily`

---

## 2026-03-02 — Initial Skill Setup

**What**: Created the Timely Timesheet Logger skill with full SKILL.md, config.json, setup guide, UI patterns reference, and february test plan.

**Config established**:
- Timely account: REDACTED_TIMELY_ACCOUNT_ID, user: REDACTED_TIMELY_USER_ID
- Monday.com board: REDACTED_MONDAY_BOARD_ID
- Two mapped projects: Example Project Alpha, Example Project Beta

**Files created**: `SKILL.md`, `data/config.json`, `references/setup-guide.md`, `references/timely-ui-patterns.md`, `references/february-test-plan.md`, `data/february-test-log.md`, `data/weekly-tracking.json`
