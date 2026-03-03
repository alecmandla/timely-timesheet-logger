# Timely UI Patterns — Browser Automation Reference

This documents how to interact with Timely's web UI via browser automation tools. These patterns were refined through 4 weeks of production testing (February 2026) and encode the most reliable approaches discovered.

**Last verified**: March 3, 2026 — Full February 2026 test run (4 weeks, 1,543 entries scanned, 24 committed).

## Two-Tool Architecture — CRITICAL

Timely automation uses TWO different browser tool systems, each for a specific purpose. Understanding which to use when is the single biggest factor in reliability.

### Tool System 1: Control Chrome (`execute_javascript`, `open_url`)
**Use for: Scanning (reading data from pages)**
- `execute_javascript` with `window.location.href = 'URL'` is the **most reliable navigation method**
- `execute_javascript` runs JavaScript directly on a tab by ID — works regardless of tab groups
- Can operate on any open Timely tab by its tab ID
- No screenshot capability — pure data extraction
- **Best for**: Sequential day scanning where you need to navigate 6+ dates and extract DOM data

### Tool System 2: Claude in Chrome (`javascript_tool`, `computer`, `navigate`)
**Use for: Committing (clicking UI elements to log time)**
- `computer` provides screenshots and click/scroll actions — required for the commit workflow
- `javascript_tool` provides DOM access within the Claude in Chrome tab group
- `navigate` works for navigation but can be slow/timeout — use as fallback
- **Best for**: The click-heavy commit workflow (click entry → select project → click Save)

### Why Two Systems?
- **Scanning** needs fast, reliable navigation across many dates + JavaScript DOM queries. Control Chrome's `execute_javascript` handles this perfectly — no timeouts, no autocomplete interference, no tab group restrictions.
- **Committing** needs screenshot verification and precise mouse clicks. Only Claude in Chrome provides `computer` tool screenshots and click actions.

### Navigation Method Ranking (most to least reliable)
1. ✅ **`Control Chrome execute_javascript`**: `window.location.href = 'https://app.timelyapp.com/...'` — Never fails, no autocomplete
2. ✅ **`Claude in Chrome navigate`**: Works but can timeout on slow loads — use for commit phase
3. ⚠️ **`Claude in Chrome javascript_tool`**: `window.location.href = '...'` — Can timeout
4. ❌ **Address bar typing** (`cmd+l`, type URL, Enter): Chrome autocomplete hijacks the URL, navigates to wrong dates. **Never use this method.**
5. ❌ **`Control Chrome open_url`**: Opens in a new tab outside the Claude in Chrome group — breaks the commit workflow

## Page Navigation

### Calendar Day View URL
```
https://app.timelyapp.com/{account_id}/calendar/day?date={YYYY-MM-DD}&multiUserMode=false&tic=true
```
- `tic=true` ensures the timeline/memory column is visible
- `multiUserMode=false` shows only the current user's entries
- Account ID: `{account_id}` (from config)

### Sequential Day Navigation (Scanning Phase)
For scanning multiple days, use Control Chrome `execute_javascript`:
```javascript
// Run on the Timely tab via Control Chrome
window.location.href = 'https://app.timelyapp.com/{account_id}/calendar/day?date=2026-02-26&multiUserMode=false&tic=true';
```
Wait 3 seconds after each navigation before querying the DOM.

### Single Day Navigation (Commit Phase)
Use Claude in Chrome `navigate` tool with the full URL. Wait 3 seconds for the SPA to render.

## Tool Compatibility — CRITICAL

### Tools that DO NOT WORK on Timely's React SPA:
- **`read_page`**: Returns "Page script returned empty result" — Timely's React SPA does not expose a standard accessibility tree
- **`find`**: Same issue — returns empty results
- **These tools are NEVER usable for Timely automation — do not attempt them**

### Tools that WORK reliably:
- **`javascript_tool`** (Claude in Chrome): Full DOM access — primary tool for element inspection, coordinate extraction, and data reading
- **`execute_javascript`** (Control Chrome): Same DOM access, works on any tab by ID — primary tool for scanning
- **`computer` screenshot/click** (Claude in Chrome): Essential for commit workflow visual verification and clicking
- **`get_page_text`** (Claude in Chrome): Returns all visible text — useful as a quick check

## Phase 1: Scanning — Complete JavaScript Template

This is the production-tested scan script. Run via `Control Chrome execute_javascript` for each day:

```javascript
// SCANNING TEMPLATE — run via Control Chrome execute_javascript
// Replace TARGETS array with current search terms from Monday.com
var targets = ["example-script.js", "example-auth.js", "example-bugfix.js",
  "example-reports.js", "example-project-alpha", "dms", "andrei", "example-update", "example-alpha",
  "ls 2.", "example-etl-tool", "example-script.js", "example-beta", "example-beta-sub",
  "example-beta", "example-dashboard", "example-daily"];
var entries = document.querySelectorAll('._memoryContainer_7imx7_8');
var results = [];
for (var i = 0; i < entries.length; i++) {
  var el = entries[i];
  var labels = el.querySelectorAll('._label_1ad4p_87');
  if (labels.length >= 2) {
    var title = (labels[0].textContent || '').trim()
      .replace(/https?:\/\/[^\s]+/g, '[URL]')
      .replace(/[?&=]+/g, '');
    var lowerTitle = title.toLowerCase();
    var matchedTerm = '';
    for (var t = 0; t < targets.length; t++) {
      if (lowerTitle.includes(targets[t])) { matchedTerm = targets[t]; break; }
    }
    if (matchedTerm) {
      var span = labels[1].querySelector('span');
      var duration = span ? span.textContent.trim() : labels[1].textContent.trim();
      results.push({ idx: i, title: title.substring(0, 80), duration: duration, term: matchedTerm });
    }
  }
}
JSON.stringify({ date: 'YYYY-MM-DD', total_entries: entries.length, matches: results }, null, 2);
```

**Important notes:**
- Use `var` not `const`/`let` — more reliable across execution contexts
- URL sanitization (`.replace(...)`) is mandatory — URLs in memory titles can block output
- Truncate titles to 80 chars to prevent output overflow
- The `idx` field is the entry's position in the DOM — needed for coordinate lookup during commits

## Phase 2: Committing — Step-by-Step Workflow

Committing requires Claude in Chrome tools (screenshots + clicks). For each approved entry:

### Step 1: Get entry coordinates
Use `javascript_tool` to find the entry by its index and get bounding box:
```javascript
var entries = document.querySelectorAll('._memoryContainer_7imx7_8');
var el = entries[TARGET_IDX];
var rect = el.getBoundingClientRect();
JSON.stringify({
  x: Math.round(rect.x + rect.width/2),
  y: Math.round(rect.y + rect.height/2),
  width: Math.round(rect.width)
});
```

### Step 2: Handle horizontal scrolling
If the entry's x-coordinate exceeds the viewport width (typically 1512px), scroll right first:
```
computer: scroll at (1300, 500), direction: right, scroll_amount: 5
```
**After scrolling, ALWAYS re-query coordinates** — positions shift after scroll.

### Step 3: Click the entry
```
computer: left_click at (centerX, centerY)
```
Wait 2 seconds for the editor panel to open on the left side.

### Step 4: Take a screenshot to verify editor opened
```
computer: screenshot
```
Confirm the editor panel is visible with "Select Project" dropdown and the correct memory time.

### Step 5: Handle memory grouping (EDGE CASE)
Sometimes Timely auto-groups multiple memories into one editor. Check the "Memories X / Y" count:
- If Y > expected, the editor contains extra unrelated memories
- Look for `FROM ... TO ...` rows showing each memory's time range
- Click the X button next to any unwanted memory's FROM/TO row to remove it
- Verify the "Logged time" updates to show only the desired entry's duration

### Step 6: Select the project
Projects appear in the "Select Project" dropdown. Click the project name directly:
- Recent projects are listed first — check if the target project is visible
- If not visible, click the dropdown arrow to expand the full list
- Alternatively, type the project name to filter

**Known project positions (may shift — always verify via screenshot):**
- After recent commits, frequently used projects tend to appear at the top of the list

### Step 7: Click Save
The Save button appears at the bottom of the editor panel. It turns green when a project is selected.
- Approximate position: (~133, 573) — but verify via screenshot
- Wait 2 seconds after clicking Save

### Step 8: Verify the commit
Take a screenshot. The timesheet header should show increased logged time and the entry should appear in the left sidebar list.

### Step 9: Re-query positions before next entry
After each commit, the DOM changes. **Always re-query entry positions** via `javascript_tool` before clicking the next entry.

## Page Structure

The day view has three main columns:
1. **Left panel (Timesheet)**: Shows logged time entries. Clicking a memory entry opens an editor here.
2. **Center column (Google Calendar)**: Calendar events with durations
3. **Right column (Memories)**: Unlogged memories from the Memory Tracker

### Memory Entry Structure
Each memory appears as a block showing app icon, title (truncated), and duration.

**Key DOM selectors (verified March 2026):**
- `._memoryContainer_7imx7_8` — individual memory entry blocks
- `._label_1ad4p_87` — label elements within each block (first = title, second = duration)
- `[data-testid="timeline_lane_default"]` — the Memories lane container (stable, use as fallback)

### CSS Class Volatility Warning
The CSS classes (e.g., `_memoryContainer_7imx7_8`) contain hashed suffixes that will change when Timely deploys new builds. If selectors stop working:
1. Use `[data-testid="timeline_lane_default"]` to find the memories lane
2. Traverse child elements by structure (DIV → DIV → LABEL pattern)
3. Use `get_page_text` as a last-resort fallback

## URL Sanitization — MANDATORY

Memory entry titles frequently contain full URLs from browser activity. These MUST be sanitized before output:
```javascript
title.replace(/https?:\/\/[^\s]+/g, '[URL]').replace(/[?&=]+/g, '')
```
Without this, the JavaScript output can be blocked or truncated by content filters.

## Error Recovery Playbook

| Problem | Solution |
|---------|----------|
| `navigate` times out | Use `Control Chrome execute_javascript` with `window.location.href` |
| Address bar autocomplete hijacks URL | Never use address bar typing — always use programmatic navigation |
| Entry x-coordinate > viewport width | Scroll right, then re-query coordinates |
| Editor groups multiple memories | Remove unwanted memories via the X button on their FROM/TO rows |
| `javascript_tool` returns empty | Page may not have loaded — wait 3 seconds and retry |
| CSS selectors stop matching | Fall back to `data-testid` selectors, then DOM structure traversal |
| Click hits wrong element | Take screenshot, re-query coordinates, try again |
| Project not in dropdown | Type project name to search/filter |

## Handling the "No Matches" Case

If the scan script returns `matches: []` for a day:
- Record in tracking file as "no matches" with the total_entries count
- Move to next day immediately — don't waste time with screenshots or further investigation

## Future: Headless Automation

The current approach requires visible Chrome windows. For a less disruptive experience:
- **Scanning** could be moved to a Puppeteer/Playwright headless MCP server — all it needs is DOM queries
- **Committing** could also go headless since we know the exact DOM selectors and click targets
- This would require building a custom MCP server (see `references/` for architecture notes)
- The scan JavaScript template above would work identically in a headless context
