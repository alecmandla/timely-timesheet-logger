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
2. One or more Monday.com boards where you track projects
3. Optionally, Gmail access for smarter search term suggestions

Would you like to provide these details yourself, or would you like me to track them
down for you?
```

### Option A: "Track them down for me"

**Timely details:**
1. Call `timely_check_session` to see if the user is already logged in
2. If logged in, the account_id is available from their Timely URL
3. If not logged in, call `timely_login` to open a visible browser for the user to sign in
4. Extract the account_id from the URL after login
5. The user_id can be found via the Timely API if they have a bearer token, or extracted from profile navigation

**Monday.com details:**
1. Use the Monday.com MCP tools to call `get_user_context` — this shows the user's favorite/recent boards
2. Also call `list_users_and_teams` with `getMe: true` to get the user's Monday.com user ID (needed for People column filtering)
3. Present the boards and ask: "Which boards do you want to use for timesheet tracking? You can select multiple."
4. For each selected board, run the **Per-Board Configuration** flow below

**Gmail:**
1. Check if Gmail MCP is connected by attempting a simple search
2. If not connected: "Gmail isn't connected yet. It's optional but helps me suggest better search terms by looking at your recent project-related emails. You can connect it in your Cowork settings under Connectors."

### Option B: "I'll provide them"

Use AskUserQuestion to collect:
1. Timely account ID (tell them where to find it: "It's the number in your Timely URL, like app.timelyapp.com/1234567/...")
2. Timely user ID (tell them where to find it, or offer to look it up)
3. Monday.com board IDs (tell them where to find it: "It's the number in your Monday.com board URL"). They can provide multiple.
4. Then run the Per-Board Configuration flow for each board

### Per-Board Configuration

For each board the user selects, walk through these questions. Use `get_board_info` to inspect the board's columns and groups before asking.

**1. Timely project name mapping:**
```
For board "{board_name}", which column should I use as the project name in Timely?
Or should I just use the item name itself?
```
Options: list available text/name columns, plus "Use item name"

**2. Billable status mapping:**
```
How should I determine if a project on "{board_name}" is billable or non-billable?
```
Options:
- "I have a status/dropdown column for that" → Ask which column, then ask which values mean billable vs. non-billable
- "I use a checkbox column" → Ask which column (checked = billable)
- "All projects on this board are billable" → Set default to billable
- "All projects on this board are non-billable" → Set default to non-billable
- "I don't track billable status" → Set default to unknown

**3. Search terms column:**
```
Which column on "{board_name}" should I use to store and read search terms?
These are the keywords I'll match against your Timely memories.
```
If no suitable column exists, offer to create one: "I don't see a search terms column. Would you like me to create a text column called 'Timesheet Search Terms' on this board?"

**4. Ignorable terms column (optional):**
```
Would you like a column for ignorable search terms? These let you suppress false
positives without removing search terms. This is optional.
```
If yes, same pattern — find existing or offer to create.

**5. People column:**
```
Which column on "{board_name}" identifies who is assigned to each project?
This is how I'll filter down to only your projects.
```
Present available People columns from the board info.

**6. Project status filtering:**
```
How do you indicate whether a project on "{board_name}" is active, not started, or completed?
```
Options:
- "I use a status column" → Ask which column, then: "Which status values mean the project is actively being tracked?" Let the user select one or more values. Everything else is treated as inactive.
- "I use board groups" → Ask which groups contain active projects. Present the board's group names.
- "I use both" → Collect both status values and active groups. A project is active if it matches either condition.

### Duplicate Name Detection

After configuring all boards, build a preliminary project registry across all boards. Check for duplicate Timely project names:

```
I found a naming conflict: "{project_name}" appears on both your
"{board_1_name}" board and your "{board_2_name}" board.

How would you like to differentiate them?
1. Prepend the client name (e.g., "Acme — {project_name}")
2. Append the board name (e.g., "{project_name} ({board_name})")
3. I'll specify a custom name for each one
```

Resolve all collisions before proceeding.

### Validation

After collecting all details, validate:
- Timely: Call `timely_check_session` to verify the session is active
- Monday.com: For each board, call `get_board_info` to verify the board and columns exist
- People column: Verify the user's Monday.com ID returns at least one assigned project on at least one board
- Active status: Verify at least one project passes the active status filter

### Completion

Save `data/config.json` with all collected values and set `setup_complete: true`.

```
Setup complete! Here's what I've configured:

- Timely account: {account_id}
- Monday.com boards:
  - {board_1_name}: {N} active projects assigned to you
  - {board_2_name}: {N} active projects assigned to you
- Gmail: {Connected / Not connected}

I found {total_N} active projects across your boards.
You can add or remove boards anytime by saying "add a board" or "remove a board".

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

## Post-Setup: Adding a Board

When a user says "add a board" or "I want to track time from another board":

1. Run the **Per-Board Configuration** flow above for the new board
2. Run **Duplicate Name Detection** against existing boards in config
3. Append the new board config to `config.boards[]`
4. Confirm: "Added {board_name} with {N} active projects. These will be included in your next daily scan."

## Post-Setup: Removing a Board

When a user says "remove a board" or "stop tracking time from {board_name}":

1. List currently configured boards and ask which to remove
2. Confirm: "This will stop scanning {board_name} for timesheet entries. Existing Timely projects and historical tracking data won't be affected. Proceed?"
3. On confirmation, remove the board entry from `config.boards[]`
4. Confirm: "Removed {board_name}. Your next daily scan will only include the remaining boards."

## Post-Setup: Adding Projects

When the user adds a new project to any of their configured Monday.com boards, the skill will automatically pick it up on the next run — provided the user is assigned via the People column and the project has an active status. If the project doesn't yet exist in Timely, the skill will offer to create it.

## Sharing This Skill

To share with a coworker:
1. Copy the entire `timely-timesheet-logger/` folder to their Cowork skills directory
2. Delete `data/config.json` and `data/weekly-tracking.json` (these are user-specific)
3. They run the skill and it enters setup mode automatically
