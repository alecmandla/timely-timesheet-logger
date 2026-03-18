# Timely UI Patterns — Browser Automation Reference

This documents how to interact with Timely's web UI via the headless Playwright MCP server (`timely_mcp`). These patterns were refined through 4 weeks of production testing (February 2026) and encode the most reliable approaches discovered.

**Last verified**: March 3, 2026 — Full February 2026 test run (4 weeks, 1,543 entries scanned, 24 committed).

## Headless Playwright Architecture

All Timely browser automation runs through the `timely_mcp` MCP server, which uses a headless Playwright browser. This means:

- **No visible browser windows** — the user's Chrome is never touched
- **No focus stealing** — scanning and committing happen completely in the background
- **Persistent login** — session cookies are stored in `~/.timely-mcp/browser-data/`
- **One-time headed login** — `timely_login` opens a visible window only for initial sign-in

### Available MCP Tools

| Tool | Purpose | Headed? |
|------|---------|---------|
| `timely_scan_day` | Scan one day's memories against search terms | No (headless) |
| `timely_scan_range` | Scan multiple days in a single call | No (headless) |
| `timely_commit_entry` | Assign a memory entry to a project | No (headless) |
| `timely_check_session` | Verify login status | No (headless) |
| `timely_login` | One-time sign-in | **Yes (visible)** |
| `timely_screenshot` | Debug: capture current page state | No (headless) |
| `timely_get_page_text` | Debug: get visible text | No (headless) |
| `timely_run_js` | Debug: run custom JavaScript | No (headless) |

### DEPRECATED — Do NOT use these tools for Timely:
- **`Control Chrome execute_javascript`** — steals focus, interferes with user's browser
- **`Claude in Chrome` tools** (`javascript_tool`, `computer`, `navigate`) — steals focus
- **`read_page`**, **`find`** — return empty on Timely's React SPA (never worked)

## Page Navigation

### Calendar Day View URL
```
https://app.timelyapp.com/{account_id}/calendar/day?date={YYYY-MM-DD}&multiUserMode=false&tic=true
```
- `tic=true` ensures the timeline/memory column is visible
- `multiUserMode=false` shows only the current user's entries
- Account ID: `{account_id}` (from config)

Navigation is handled internally by the MCP tools — you just pass the `account_id` and `date`.

## Phase 1: Scanning

Scanning is handled by `timely_scan_day` or `timely_scan_range`. The tools internally run the same production-tested JavaScript that was previously used via Control Chrome, but now in a headless Playwright context.

### How to scan:

```
Tool: timely_scan_day
Params:
  account_id: "YOUR_ACCOUNT_ID"
  date: "2026-03-15"
  search_terms: ["acme-redesign", "beta-app", "figma-acme", ...]
  ignorable_terms: ["chrome", "slack"]
```

Returns:
```json
{
  "date": "2026-03-15",
  "total_entries": 42,
  "matches": [
    {"idx": 3, "title": "Terminal — acme-redesign build script", "duration": "15m", "term": "acme-redesign"},
    {"idx": 12, "title": "Chrome — beta-app dashboard review", "duration": "22m", "term": "beta-app"}
  ]
}
```

For multi-day scans, use `timely_scan_range` — it's more efficient because it reuses the same headless page:

```
Tool: timely_scan_range
Params:
  account_id: "YOUR_ACCOUNT_ID"
  start_date: "2026-03-09"
  end_date: "2026-03-15"
  search_terms: [...]
  ignorable_terms: [...]
```

### Internal JavaScript Template

The scan script embedded in `timely_mcp` uses these selectors:

```javascript
// Primary selector for memory entry blocks
document.querySelectorAll('._memoryContainer_7imx7_8')

// Fallback: use data-testid (more stable across Timely deploys)
document.querySelector('[data-testid="timeline_lane_default"]')
  .querySelectorAll('[class*="memoryContainer"]')

// Labels within each entry (first = title, second = duration)
el.querySelectorAll('[class*="label_"]')
```

**URL sanitization** is applied automatically — memory titles with full URLs are cleaned.

## Phase 2: Committing

Committing is handled by `timely_commit_entry`. For each approved entry:

```
Tool: timely_commit_entry
Params:
  account_id: "YOUR_ACCOUNT_ID"
  date: "2026-03-15"
  entry_index: 3
  project_name: "Acme Website Redesign"
```

The tool internally:
1. Navigates to the correct date (headless)
2. Finds the memory entry by DOM index
3. Scrolls it into view if needed
4. Clicks it to open the editor panel
5. Types/selects the project name in the project dropdown
6. Clicks Save
7. Returns success/failure status

### CRITICAL: Re-scan after each commit
After committing an entry, the DOM changes — entry indices shift. **Always re-scan the day** before committing the next entry.

### Memory Grouping Edge Case
Sometimes Timely auto-groups multiple memories into one editor. If `timely_commit_entry` returns unexpected results, use `timely_screenshot` to inspect the page state, then `timely_run_js` for custom DOM interaction.

## Page Structure

The day view has three main columns:
1. **Left panel (Timesheet)**: Shows logged time entries. Clicking a memory entry opens an editor here.
2. **Center column (Google Calendar)**: Calendar events with durations
3. **Right column (Memories)**: Unlogged memories from the Memory Tracker

### Memory Entry Structure
Each memory appears as a block showing app icon, title (truncated), and duration.

**Key DOM selectors (verified March 2026):**
- `._memoryContainer_7imx7_8` — individual memory entry blocks
- `[class*="label_"]` — label elements within each block (first = title, second = duration)
- `[data-testid="timeline_lane_default"]` — the Memories lane container (stable, use as fallback)

### CSS Class Volatility Warning
The CSS classes (e.g., `_memoryContainer_7imx7_8`) contain hashed suffixes that will change when Timely deploys new builds. If selectors stop working:
1. Use `[data-testid="timeline_lane_default"]` to find the memories lane
2. Traverse child elements by structure (DIV → DIV → LABEL pattern)
3. Use `timely_get_page_text` as a last-resort fallback
4. Use `timely_run_js` to test new selectors interactively

## URL Sanitization — MANDATORY

Memory entry titles frequently contain full URLs from browser activity. These MUST be sanitized before output:
```javascript
title.replace(/https?:\/\/[^\s]+/g, '[URL]').replace(/[?&=]+/g, '')
```
This is handled automatically by `timely_scan_day` — no manual sanitization needed.

## Error Recovery Playbook

| Problem | Solution |
|---------|----------|
| Session expired | Call `timely_check_session`, then `timely_login` if needed |
| Scan returns 0 entries | Page may not have loaded — call `timely_screenshot` to check |
| Commit fails to find entry | Re-scan the day to get fresh indices |
| Commit fails to select project | Verify project name matches Timely exactly — use `timely_get_page_text` |
| CSS selectors stop matching | `timely_mcp` falls back to `data-testid` selectors automatically. If that also fails, use `timely_run_js` to probe the DOM |
| Editor groups multiple memories | Use `timely_run_js` to remove extras via the X button on FROM/TO rows |
| Need to debug visually | `timely_screenshot` saves a PNG to /tmp/ |

## Handling the "No Matches" Case

If the scan returns `matches: []` for a day:
- Record in tracking file as "no matches" with the total_entries count
- Move to next day immediately — don't waste time with further investigation

## Session Persistence

The headless browser uses a persistent Chromium profile at `~/.timely-mcp/browser-data/`. This means:
- Login cookies survive between MCP server restarts
- Typically you only need to call `timely_login` once every few weeks
- If Timely's session expires, `timely_check_session` will detect it and the skill should prompt the user to re-login

## Environment Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `TIMELY_MCP_USER_DATA_DIR` | `~/.timely-mcp/browser-data` | Persistent browser profile directory |
