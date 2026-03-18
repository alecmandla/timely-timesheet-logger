#!/usr/bin/env python3
"""
Headless Playwright MCP Server for Timely timesheet automation.

Replaces Chrome browser automation with a background headless browser,
so scanning and committing Timely memory entries never steals focus
from the user's active Chrome window.

Transport: stdio (runs as a local subprocess)
Auth: Persistent browser context stores Timely session cookies.
      First run requires `timely_login` (headed) for the user to sign in.
"""

import asyncio
import json
import logging
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional, List, Dict, Any

from pydantic import BaseModel, Field, ConfigDict, field_validator
from mcp.server.fastmcp import FastMCP, Context

# ---------------------------------------------------------------------------
# Logging — stderr only (stdio transport uses stdout for MCP messages)
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    stream=sys.stderr,
)
log = logging.getLogger("timely_mcp")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
DEFAULT_USER_DATA_DIR = os.path.expanduser(
    "~/.timely-mcp/browser-data"
)
TIMELY_BASE_URL = "https://app.timelyapp.com"
PAGE_LOAD_WAIT_MS = 4000  # wait after navigation for SPA to render
COMMIT_ACTION_WAIT_MS = 2500  # wait after clicks during commit

# ---------------------------------------------------------------------------
# Scan JavaScript template
# Identical to the production-tested template from timely-ui-patterns.md
# but parameterized for search terms.
# ---------------------------------------------------------------------------
SCAN_JS_TEMPLATE = """
(function() {
  var targets = SEARCH_TERMS_PLACEHOLDER;
  var ignorable = IGNORABLE_TERMS_PLACEHOLDER;
  var entries = document.querySelectorAll('._memoryContainer_7imx7_8');
  if (entries.length === 0) {
    // Fallback: try data-testid selector
    var lane = document.querySelector('[data-testid="timeline_lane_default"]');
    if (lane) {
      entries = lane.querySelectorAll('[class*="memoryContainer"]');
    }
  }
  var results = [];
  for (var i = 0; i < entries.length; i++) {
    var el = entries[i];
    var labels = el.querySelectorAll('[class*="label_"]');
    if (labels.length >= 2) {
      var title = (labels[0].textContent || '').trim()
        .replace(/https?:\\/\\/[^\\s]+/g, '[URL]')
        .replace(/[?&=]+/g, '');
      var lowerTitle = title.toLowerCase();
      // Check ignorable terms first
      var isIgnorable = false;
      for (var ig = 0; ig < ignorable.length; ig++) {
        if (lowerTitle.includes(ignorable[ig].toLowerCase())) {
          isIgnorable = true;
          break;
        }
      }
      if (isIgnorable) continue;
      var matchedTerm = '';
      for (var t = 0; t < targets.length; t++) {
        if (lowerTitle.includes(targets[t].toLowerCase())) {
          matchedTerm = targets[t];
          break;
        }
      }
      if (matchedTerm) {
        var span = labels[1].querySelector('span');
        var duration = span ? span.textContent.trim() : labels[1].textContent.trim();
        results.push({
          idx: i,
          title: title.substring(0, 120),
          duration: duration,
          term: matchedTerm
        });
      }
    }
  }
  return JSON.stringify({
    date: 'TARGET_DATE_PLACEHOLDER',
    total_entries: entries.length,
    matches: results
  });
})();
"""

# ---------------------------------------------------------------------------
# Lifespan — manage the Playwright browser
# ---------------------------------------------------------------------------
_browser_context = None
_playwright_instance = None


async def _ensure_browser(headed: bool = False):
    """Launch or return the existing Playwright browser context."""
    global _browser_context, _playwright_instance

    if _browser_context is not None:
        try:
            # Quick health check — if context is closed this will fail
            _browser_context.pages
            return _browser_context
        except Exception:
            _browser_context = None

    from playwright.async_api import async_playwright

    user_data_dir = os.environ.get("TIMELY_MCP_USER_DATA_DIR", DEFAULT_USER_DATA_DIR)
    Path(user_data_dir).mkdir(parents=True, exist_ok=True)

    _playwright_instance = await async_playwright().start()

    _browser_context = await _playwright_instance.chromium.launch_persistent_context(
        user_data_dir=user_data_dir,
        headless=not headed,
        viewport={"width": 1512, "height": 900},
        args=[
            "--disable-blink-features=AutomationControlled",
            "--no-first-run",
            "--disable-default-apps",
        ],
    )
    log.info("Browser launched (headed=%s, user_data=%s)", headed, user_data_dir)
    return _browser_context


async def _get_page(context, url: str):
    """Navigate a page to url, reusing an existing Timely tab if possible."""
    # Reuse the first Timely tab, or create one
    timely_page = None
    for p in context.pages:
        if TIMELY_BASE_URL in (p.url or ""):
            timely_page = p
            break
    if timely_page is None:
        timely_page = await context.new_page()

    await timely_page.goto(url, wait_until="domcontentloaded")
    await timely_page.wait_for_timeout(PAGE_LOAD_WAIT_MS)
    return timely_page


async def _shutdown_browser():
    """Close the browser context and Playwright."""
    global _browser_context, _playwright_instance
    if _browser_context:
        try:
            await _browser_context.close()
        except Exception:
            pass
        _browser_context = None
    if _playwright_instance:
        try:
            await _playwright_instance.stop()
        except Exception:
            pass
        _playwright_instance = None


# ---------------------------------------------------------------------------
# MCP Server
# ---------------------------------------------------------------------------
mcp = FastMCP("timely_mcp")


# ---- Input Models ---------------------------------------------------------

class ScanDayInput(BaseModel):
    """Input for scanning a single day's Timely memories."""
    model_config = ConfigDict(str_strip_whitespace=True)

    account_id: str = Field(..., description="Timely account ID (from config)")
    date: str = Field(
        ...,
        description="Date to scan in YYYY-MM-DD format",
        pattern=r"^\d{4}-\d{2}-\d{2}$",
    )
    search_terms: List[str] = Field(
        ...,
        description="List of search terms to match against memory descriptions",
        min_length=1,
    )
    ignorable_terms: List[str] = Field(
        default_factory=list,
        description="Terms to exclude from matching (overrides search_terms)",
    )


class ScanRangeInput(BaseModel):
    """Input for scanning a range of dates."""
    model_config = ConfigDict(str_strip_whitespace=True)

    account_id: str = Field(..., description="Timely account ID")
    start_date: str = Field(..., description="Start date YYYY-MM-DD", pattern=r"^\d{4}-\d{2}-\d{2}$")
    end_date: str = Field(..., description="End date YYYY-MM-DD", pattern=r"^\d{4}-\d{2}-\d{2}$")
    search_terms: List[str] = Field(..., description="Search terms to match", min_length=1)
    ignorable_terms: List[str] = Field(default_factory=list, description="Terms to exclude")


class CommitEntryInput(BaseModel):
    """Input for committing a single memory entry to a project."""
    model_config = ConfigDict(str_strip_whitespace=True)

    account_id: str = Field(..., description="Timely account ID")
    date: str = Field(..., description="Date of the entry YYYY-MM-DD", pattern=r"^\d{4}-\d{2}-\d{2}$")
    entry_index: int = Field(..., description="DOM index of the memory entry (from scan results)", ge=0)
    project_name: str = Field(..., description="Timely project name to assign", min_length=1)


class SessionCheckInput(BaseModel):
    """Input for checking Timely session status."""
    model_config = ConfigDict(str_strip_whitespace=True)

    account_id: str = Field(..., description="Timely account ID")


# ---- Tools ----------------------------------------------------------------

@mcp.tool(
    name="timely_login",
    annotations={
        "title": "Timely Login (Headed Browser)",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": True,
    },
)
async def timely_login(account_id: str) -> str:
    """Launch a VISIBLE browser window for the user to log in to Timely.

    This is a one-time setup step. After login, the session cookies are
    stored in a persistent browser profile so all future operations run
    headless (invisible).

    The tool waits up to 120 seconds for the user to complete login.
    Once the Timely calendar page loads, login is confirmed and the
    browser closes automatically.

    Args:
        account_id: Timely account ID (visible in Timely URLs)

    Returns:
        str: JSON with login status and any error messages
    """
    await _shutdown_browser()  # close any existing headless session

    try:
        context = await _ensure_browser(headed=True)
        page = await context.new_page()
        login_url = f"{TIMELY_BASE_URL}/{account_id}/calendar"
        await page.goto(login_url, wait_until="domcontentloaded")

        log.info("Waiting for user to log in (up to 120s)...")

        # Wait for the calendar page to load (indicates successful login)
        try:
            await page.wait_for_url(
                f"**/{account_id}/calendar**",
                timeout=120_000,
            )
            await page.wait_for_timeout(3000)
        except Exception:
            return json.dumps({
                "success": False,
                "error": "Login timed out after 120 seconds. Please try again.",
            })

        # Verify we're on the calendar page
        current_url = page.url
        if f"/{account_id}/" in current_url:
            await _shutdown_browser()
            return json.dumps({
                "success": True,
                "message": "Login successful. Session cookies saved. All future operations will run in the background.",
            })
        else:
            await _shutdown_browser()
            return json.dumps({
                "success": False,
                "error": f"Unexpected page after login: {current_url}",
            })
    except Exception as e:
        await _shutdown_browser()
        return json.dumps({"success": False, "error": str(e)})


@mcp.tool(
    name="timely_check_session",
    annotations={
        "title": "Check Timely Session",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def timely_check_session(params: SessionCheckInput) -> str:
    """Check if the Timely session is still valid (user is logged in).

    Navigates to the Timely calendar in a headless browser and checks
    whether the page loads successfully or redirects to login.

    Args:
        params: SessionCheckInput with account_id

    Returns:
        str: JSON with session status, logged_in boolean, and current URL
    """
    try:
        context = await _ensure_browser(headed=False)
        url = f"{TIMELY_BASE_URL}/{params.account_id}/calendar"
        page = await _get_page(context, url)

        current_url = page.url
        logged_in = f"/{params.account_id}/" in current_url and "login" not in current_url.lower()

        return json.dumps({
            "logged_in": logged_in,
            "current_url": current_url,
            "message": "Session is active." if logged_in else "Session expired. Run timely_login to re-authenticate.",
        })
    except Exception as e:
        return json.dumps({"logged_in": False, "error": str(e)})


@mcp.tool(
    name="timely_scan_day",
    annotations={
        "title": "Scan Timely Memories for One Day",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def timely_scan_day(params: ScanDayInput) -> str:
    """Scan a single day's Timely Memory Tracker entries and match against search terms.

    Navigates to the Timely day view in a HEADLESS browser, extracts all
    memory entries from the DOM, and matches them against the provided
    search terms. Returns matched entries with their index, title,
    duration, and the term that matched.

    This runs completely in the background — no visible browser window.

    Args:
        params: ScanDayInput with account_id, date, search_terms, ignorable_terms

    Returns:
        str: JSON with date, total_entries scanned, and matches array.
             Each match has: idx, title, duration, term.

    Example result:
        {
          "date": "2026-03-15",
          "total_entries": 42,
          "matches": [
            {"idx": 3, "title": "Terminal — acme-redesign build script", "duration": "15m", "term": "acme-redesign"},
            {"idx": 12, "title": "Chrome — beta-app dashboard review", "duration": "22m", "term": "beta-app"}
          ]
        }
    """
    try:
        context = await _ensure_browser(headed=False)
        url = (
            f"{TIMELY_BASE_URL}/{params.account_id}/calendar/day"
            f"?date={params.date}&multiUserMode=false&tic=true"
        )
        page = await _get_page(context, url)

        # Check for login redirect
        if "login" in page.url.lower() or f"/{params.account_id}/" not in page.url:
            return json.dumps({
                "error": "Not logged in. Run timely_login first.",
                "date": params.date,
                "total_entries": 0,
                "matches": [],
            })

        # Build the scan script with injected search terms
        terms_json = json.dumps([t.lower() for t in params.search_terms])
        ignorable_json = json.dumps([t.lower() for t in params.ignorable_terms])
        script = SCAN_JS_TEMPLATE.replace(
            "SEARCH_TERMS_PLACEHOLDER", terms_json
        ).replace(
            "IGNORABLE_TERMS_PLACEHOLDER", ignorable_json
        ).replace(
            "TARGET_DATE_PLACEHOLDER", params.date
        )

        result = await page.evaluate(script)
        return result  # already a JSON string from the JS

    except Exception as e:
        log.error("Scan failed for %s: %s", params.date, e)
        return json.dumps({
            "error": str(e),
            "date": params.date,
            "total_entries": 0,
            "matches": [],
        })


@mcp.tool(
    name="timely_scan_range",
    annotations={
        "title": "Scan Timely Memories for a Date Range",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def timely_scan_range(params: ScanRangeInput) -> str:
    """Scan multiple days of Timely memories in a single call.

    Iterates through each date from start_date to end_date (inclusive),
    scanning each day's memory entries against the provided search terms.
    All scanning happens in a HEADLESS browser — completely invisible.

    This is more efficient than calling timely_scan_day repeatedly because
    it reuses the same browser page and navigates sequentially.

    Args:
        params: ScanRangeInput with account_id, start_date, end_date,
                search_terms, ignorable_terms

    Returns:
        str: JSON with results array (one entry per day) and summary.
    """
    from datetime import datetime, timedelta

    try:
        start = datetime.strptime(params.start_date, "%Y-%m-%d")
        end = datetime.strptime(params.end_date, "%Y-%m-%d")
    except ValueError as e:
        return json.dumps({"error": f"Invalid date format: {e}"})

    if end < start:
        return json.dumps({"error": "end_date must be >= start_date"})

    context = await _ensure_browser(headed=False)
    results = []
    total_matches = 0
    current = start

    while current <= end:
        date_str = current.strftime("%Y-%m-%d")
        scan_input = ScanDayInput(
            account_id=params.account_id,
            date=date_str,
            search_terms=params.search_terms,
            ignorable_terms=params.ignorable_terms,
        )
        day_result_str = await timely_scan_day(scan_input)
        day_result = json.loads(day_result_str)
        results.append(day_result)
        total_matches += len(day_result.get("matches", []))
        current += timedelta(days=1)

    return json.dumps({
        "start_date": params.start_date,
        "end_date": params.end_date,
        "days_scanned": len(results),
        "total_matches": total_matches,
        "daily_results": results,
    }, indent=2)


@mcp.tool(
    name="timely_commit_entry",
    annotations={
        "title": "Commit a Memory Entry to a Project",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": True,
    },
)
async def timely_commit_entry(params: CommitEntryInput) -> str:
    """Assign a Timely memory entry to a project by clicking through the UI.

    Navigates to the correct date, clicks the memory entry at the given
    DOM index, selects the specified project from the dropdown, and
    clicks Save. All of this happens in a HEADLESS browser — completely
    invisible to the user.

    IMPORTANT: Always re-scan after each commit, as DOM indices shift
    when entries are assigned.

    Args:
        params: CommitEntryInput with account_id, date, entry_index, project_name

    Returns:
        str: JSON with success status, committed entry details, and any errors.
    """
    try:
        context = await _ensure_browser(headed=False)
        url = (
            f"{TIMELY_BASE_URL}/{params.account_id}/calendar/day"
            f"?date={params.date}&multiUserMode=false&tic=true"
        )
        page = await _get_page(context, url)

        # Check login
        if "login" in page.url.lower() or f"/{params.account_id}/" not in page.url:
            return json.dumps({
                "success": False,
                "error": "Not logged in. Run timely_login first.",
            })

        # Step 1: Get the entry element and click it
        click_result = await page.evaluate(f"""
        (function() {{
            var entries = document.querySelectorAll('._memoryContainer_7imx7_8');
            if (entries.length === 0) {{
                var lane = document.querySelector('[data-testid="timeline_lane_default"]');
                if (lane) entries = lane.querySelectorAll('[class*="memoryContainer"]');
            }}
            if ({params.entry_index} >= entries.length) {{
                return JSON.stringify({{
                    error: 'Entry index ' + {params.entry_index} + ' out of range (found ' + entries.length + ' entries)'
                }});
            }}
            var el = entries[{params.entry_index}];
            var rect = el.getBoundingClientRect();

            // Scroll into view if needed
            if (rect.right > window.innerWidth || rect.left < 0) {{
                el.scrollIntoView({{ behavior: 'instant', inline: 'center' }});
            }}

            return JSON.stringify({{
                found: true,
                x: Math.round(rect.x + rect.width / 2),
                y: Math.round(rect.y + rect.height / 2),
                width: Math.round(rect.width),
                total_entries: entries.length
            }});
        }})();
        """)

        click_data = json.loads(click_result)
        if "error" in click_data:
            return json.dumps({"success": False, "error": click_data["error"]})

        # Click the memory entry
        await page.mouse.click(click_data["x"], click_data["y"])
        await page.wait_for_timeout(COMMIT_ACTION_WAIT_MS)

        # Step 2: Find and click the project in the editor panel
        # Look for the project selector / dropdown
        project_assigned = await page.evaluate(f"""
        (async function() {{
            // Look for project dropdown or selector
            var projectInput = document.querySelector(
                'input[placeholder*="project" i], ' +
                'input[placeholder*="Project" i], ' +
                '[class*="projectSelect"] input, ' +
                '[class*="project-select"] input, ' +
                '[data-testid*="project"] input'
            );

            if (projectInput) {{
                // Clear and type the project name
                projectInput.focus();
                projectInput.value = '';
                projectInput.dispatchEvent(new Event('input', {{ bubbles: true }}));
                await new Promise(r => setTimeout(r, 300));

                // Type the project name character by character
                var name = {json.dumps(params.project_name)};
                for (var i = 0; i < name.length; i++) {{
                    projectInput.value += name[i];
                    projectInput.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    await new Promise(r => setTimeout(r, 50));
                }}
                await new Promise(r => setTimeout(r, 1000));

                // Look for the matching dropdown option
                var options = document.querySelectorAll(
                    '[class*="option"], [class*="dropdown"] [class*="item"], ' +
                    '[role="option"], [role="listbox"] > *, [class*="menuItem"]'
                );
                for (var j = 0; j < options.length; j++) {{
                    if ((options[j].textContent || '').toLowerCase().includes(name.toLowerCase())) {{
                        options[j].click();
                        return JSON.stringify({{ found_input: true, selected: true }});
                    }}
                }}
                return JSON.stringify({{ found_input: true, selected: false, hint: 'Typed but no matching option found in dropdown' }});
            }}

            // Fallback: look for project name text directly in the editor panel
            var allElements = document.querySelectorAll('span, div, li, a, button');
            var name = {json.dumps(params.project_name)};
            for (var k = 0; k < allElements.length; k++) {{
                var text = (allElements[k].textContent || '').trim();
                if (text.toLowerCase() === name.toLowerCase() &&
                    allElements[k].offsetParent !== null) {{
                    allElements[k].click();
                    return JSON.stringify({{ found_input: false, selected: true, method: 'direct_click' }});
                }}
            }}

            return JSON.stringify({{ found_input: false, selected: false, hint: 'Could not find project selector' }});
        }})();
        """)

        assign_data = json.loads(project_assigned)
        if not assign_data.get("selected"):
            # Try clicking by project name as a Playwright selector
            try:
                await page.get_by_text(params.project_name, exact=False).first.click()
                assign_data["selected"] = True
                assign_data["method"] = "playwright_text_selector"
            except Exception:
                pass

        if not assign_data.get("selected"):
            return json.dumps({
                "success": False,
                "error": f"Could not find/select project '{params.project_name}' in the editor.",
                "debug": assign_data,
            })

        await page.wait_for_timeout(1000)

        # Step 3: Click Save
        save_clicked = False
        try:
            save_btn = page.get_by_role("button", name="Save")
            if await save_btn.count() > 0:
                await save_btn.first.click()
                save_clicked = True
        except Exception:
            pass

        if not save_clicked:
            # Fallback: look for save button by text content
            try:
                await page.evaluate("""
                (function() {
                    var buttons = document.querySelectorAll('button');
                    for (var i = 0; i < buttons.length; i++) {
                        if ((buttons[i].textContent || '').trim().toLowerCase() === 'save') {
                            buttons[i].click();
                            return true;
                        }
                    }
                    return false;
                })();
                """)
                save_clicked = True
            except Exception:
                pass

        await page.wait_for_timeout(COMMIT_ACTION_WAIT_MS)

        return json.dumps({
            "success": save_clicked,
            "date": params.date,
            "entry_index": params.entry_index,
            "project": params.project_name,
            "message": "Entry committed successfully." if save_clicked else "Project selected but Save button not found.",
        })

    except Exception as e:
        log.error("Commit failed for %s idx %d: %s", params.date, params.entry_index, e)
        return json.dumps({
            "success": False,
            "error": str(e),
            "date": params.date,
            "entry_index": params.entry_index,
        })


@mcp.tool(
    name="timely_get_page_text",
    annotations={
        "title": "Get Visible Text from Timely Page",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def timely_get_page_text(params: SessionCheckInput) -> str:
    """Get all visible text from the current Timely page.

    Useful for debugging when selectors stop working — returns the raw
    visible text so the agent can adapt.

    Args:
        params: SessionCheckInput with account_id

    Returns:
        str: The visible text content of the current Timely page.
    """
    try:
        context = await _ensure_browser(headed=False)
        pages = context.pages
        timely_page = None
        for p in pages:
            if TIMELY_BASE_URL in (p.url or ""):
                timely_page = p
                break
        if timely_page is None:
            return json.dumps({"error": "No Timely page open. Run a scan first."})

        text = await timely_page.evaluate("document.body.innerText")
        return json.dumps({"url": timely_page.url, "text": text[:5000]})
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool(
    name="timely_screenshot",
    annotations={
        "title": "Take a Screenshot of the Timely Page",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def timely_screenshot(params: SessionCheckInput) -> str:
    """Take a screenshot of the current Timely page and save to a temp file.

    Useful for debugging commit issues or verifying page state. The
    screenshot is saved to /tmp/ and the path is returned.

    Args:
        params: SessionCheckInput with account_id

    Returns:
        str: JSON with the file path to the screenshot.
    """
    try:
        context = await _ensure_browser(headed=False)
        timely_page = None
        for p in context.pages:
            if TIMELY_BASE_URL in (p.url or ""):
                timely_page = p
                break
        if timely_page is None:
            return json.dumps({"error": "No Timely page open. Run a scan first."})

        screenshot_path = f"/tmp/timely-screenshot-{params.account_id}.png"
        await timely_page.screenshot(path=screenshot_path, full_page=False)
        return json.dumps({
            "path": screenshot_path,
            "url": timely_page.url,
            "message": f"Screenshot saved to {screenshot_path}",
        })
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool(
    name="timely_run_js",
    annotations={
        "title": "Execute JavaScript on the Timely Page",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": True,
    },
)
async def timely_run_js(script: str) -> str:
    """Execute arbitrary JavaScript on the current Timely page.

    Escape hatch for when CSS selectors change or the commit workflow
    needs custom DOM interaction. The script runs in the page context
    and should return a JSON string.

    Args:
        script: JavaScript code to execute. Must return a value (use
                JSON.stringify for objects).

    Returns:
        str: The return value of the script, or an error message.
    """
    try:
        context = await _ensure_browser(headed=False)
        timely_page = None
        for p in context.pages:
            if TIMELY_BASE_URL in (p.url or ""):
                timely_page = p
                break
        if timely_page is None:
            return json.dumps({"error": "No Timely page open. Run a scan or navigate first."})

        result = await timely_page.evaluate(script)
        if result is None:
            return json.dumps({"result": None})
        if isinstance(result, str):
            return result
        return json.dumps(result)
    except Exception as e:
        return json.dumps({"error": str(e)})


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    mcp.run()
