# Setup Guide — Timely Timesheet Logger

This guide walks a new user through setting up the skill. The skill itself drives this process interactively — this document is the reference for how Claude should handle each step.

## First-Run Detection

When the skill is invoked, check for `data/config.json`. If it doesn't exist or `setup_complete` is false, enter setup mode.

## Setup Flow

### Welcome Message

```
Welcome to the Timely Timesheet Logger! Before we start automating your timesheets,
I need to collect a few details. This should only take a couple of minutes.

I'll need:
1. Your Timely account details (account ID and user ID)
2. A Monday.com board where you track projects
3. Optionally, Gmail access for smarter search term suggestions

Would you like to provide these details yourself, or would you like me to track them
down for you?
```

### Option A: "Track them down for me"

**Timely details:**
1. Open a browser tab to `https://app.timelyapp.com`
2. If the user is logged in, extract the account_id from the URL (it's the number after timelyapp.com/)
3. Navigate to the user's profile or use the calendar URL to find the user_id
4. If not logged in, tell them: "I need you to log into Timely first. Once you're logged in, I can grab your account details from the URL."

**Monday.com details:**
1. Use the Monday.com MCP tools to call `get_user_context` — this shows the user's favorite/recent boards
2. Present the boards and ask: "Which of these boards do you use to track your projects?"
3. Once they pick a board, call `get_board_info` to find the columns
4. Look for a column containing Timely project names. If none exists, suggest creating one:
   "I don't see a column for Timely project names. Would you like me to create a text column called 'Timely Project Name' on this board? This is how I'll know which Monday.com projects map to which Timely projects."
5. Store the board_id, timely_name_column_id, and client_name_column_id

**Gmail:**
1. Check if Gmail MCP is connected by attempting a simple search
2. If not connected: "Gmail isn't connected yet. It's optional but helps me suggest better search terms by looking at your recent project-related emails. You can connect it in your Cowork settings under Connectors."

### Option B: "I'll provide them"

Use AskUserQuestion to collect:
1. Timely account ID (tell them where to find it: "It's the number in your Timely URL, like app.timelyapp.com/1234567/...")
2. Timely user ID (tell them where to find it, or offer to look it up)
3. Monday.com board ID (tell them where to find it: "It's the number in your Monday.com board URL")
4. Which column has the Timely project name mapping

### Validation

After collecting all details, validate:
- Timely: Navigate to `{base_url}/{account_id}/calendar/day` and verify the page loads
- Monday.com: Call `get_board_info` with the board_id and verify it returns data
- Check that the Timely name column exists and at least one project has a value

### Completion

Save `data/config.json` with all collected values and set `setup_complete: true`.

```
Setup complete! Here's what I've configured:

- Timely account: {account_id} (user: {user_id})
- Monday.com board: {board_name} (ID: {board_id})
- Timely name column: {column_name}
- Gmail: {Connected / Not connected}

I found {N} projects on your board that have Timely project names mapped.
You can add more anytime by filling in the Timely Project Name column on your
Monday.com board.

Let's set up your automated schedules next so this runs hands-free.
```

After showing this message, immediately proceed to the **Schedule Creation** section below.

## Post-Setup: Schedule Creation

After config is saved and validated, offer to create the two scheduled tasks. Use the `create_scheduled_task` tool from the scheduled-tasks MCP.

### Prompt the user:

```
Would you like me to set up the automated schedules now? This will create two tasks:

1. **Daily Scan + Commit** — Runs every day at 10:00 AM
   Scans yesterday's Timely memories, matches them to projects, and asks for your approval before committing.

2. **Weekly Reconciliation** — Runs every Monday at 11:00 AM
   Generates a summary of everything committed during the prior week. On the first Monday of the month, also does a validation sweep for any missed entries.

You can adjust the times or disable either one later.
```

### If the user approves (or selects specific schedules):

**Daily task:**
```
Tool: create_scheduled_task
taskId: timely-daily-scan
description: Scan yesterday's Timely memories, match to projects, and commit approved entries
cronExpression: 0 10 * * *
prompt: |
  Run the Timely Timesheet Logger skill in Daily Scan + Commit mode.
  Process yesterday's date only.
  Follow the skill instructions in the timely-timesheet-logger folder.
```

**Weekly task:**
```
Tool: create_scheduled_task
taskId: timely-weekly-reconciliation
description: Generate weekly timesheet reconciliation report (monthly validation sweep on first Monday)
cronExpression: 0 11 * * 1
prompt: |
  Run the Timely Timesheet Logger skill in Monday Reconciliation mode.
  Generate the weekly reconciliation report for the prior Mon-Sun period.
  If today is the first Monday of the month (date ≤ 7), also run the
  monthly validation sweep for the entire prior month.
  Follow the skill instructions in the timely-timesheet-logger folder.
```

### If the user declines:

```
No problem! You can set these up anytime by saying "schedule my timesheet tasks"
or by creating them manually in Claude Desktop under scheduled tasks.
```

### Post-scheduling confirmation:

```
Schedules created! Here's what's set up:

- Daily scan: Every day at 10:00 AM → scans + commits yesterday's entries
- Weekly reconciliation: Every Monday at 11:00 AM → weekly summary report

Both tasks will ask for your approval before committing any entries.
You can manage these in Claude Desktop under your scheduled tasks.
```

## Post-Setup: Adding Projects

When the user adds a new project to their Monday.com board with a Timely project name, the skill will automatically pick it up on the next run. No config changes needed — the board is the source of truth.

## Sharing This Skill

To share with a coworker:
1. Copy the entire `timely-timesheet-logger/` folder to their Cowork skills directory
2. Delete `data/config.json` and `data/weekly-tracking.json` (these are user-specific)
3. They run the skill and it enters setup mode automatically
