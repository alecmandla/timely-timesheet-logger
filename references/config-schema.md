# Configuration Schema

The skill uses a `config.json` file in its `data/` directory to store user-specific settings. This file is created during the setup flow and can be edited manually.

## Config File Location

`timely-timesheet-logger/data/config.json`

## Schema

```json
{
  "timely": {
    "account_id": "string — Timely account ID (visible in URL: app.timelyapp.com/{account_id}/...)",
    "user_id": "string — Your Timely user ID (from API: GET /accounts → users)",
    "base_url": "string — default: https://app.timelyapp.com"
  },
  "monday": {
    "board_id": "string — Monday.com board ID that tracks projects",
    "timely_name_column_id": "string — Column ID containing the Timely project name mapping",
    "client_name_column_id": "string — Column ID containing the client name"
  },
  "schedule": {
    "daily_scan_time": "string — default: 10:00",
    "weekly_commit_time": "string — default: 11:00",
    "weekly_commit_day": "string — default: monday",
    "scan_days": "array — default: [monday, tuesday, wednesday, thursday, friday, saturday, sunday]"
  },
  "preferences": {
    "auto_save_on_commit": true,
    "skip_weekends": false,
    "confidence_threshold": "string — low/medium/high — minimum match confidence to auto-track. Default: low",
    "default_date_range": "string — default: current_week"
  },
  "activity_log": {
    "path": "string — path to the activity log text file. Default: data/activity-log.txt (relative to skill root)",
    "enabled": "boolean — whether to use the activity log for cross-referencing. Default: true",
    "time_tolerance_min": "number — minutes of tolerance when matching timestamps. Default: 15",
    "calendar_fallback": "boolean — whether to query Google Calendar for Zoom/Meet entries. Default: true"
  },
  "setup_complete": false
}
```

## How Each Field Gets Populated

### Auto-discoverable (skill can find these)
- `timely.account_id` — Extracted from the Timely URL when the user navigates to it
- `timely.user_id` — Found via the Timely API if they have a bearer token, or extracted from the URL
- `monday.board_id` — Found by searching Monday.com boards for ones the user owns
- `monday.timely_name_column_id` — Found by reading board column metadata
- `monday.client_name_column_id` — Found by reading board column metadata

### User-provided (must ask or guide)
- Timely login session — User must be logged in via the browser
- Monday.com connection — Must be connected as a Cowork MCP connector
- Gmail connection — Must be connected as a Cowork MCP connector (optional but recommended)

## Default Config Template

```json
{
  "timely": {
    "account_id": "",
    "user_id": "",
    "base_url": "https://app.timelyapp.com"
  },
  "monday": {
    "board_id": "",
    "timely_name_column_id": "",
    "client_name_column_id": ""
  },
  "schedule": {
    "daily_scan_time": "10:00",
    "weekly_commit_time": "11:00",
    "weekly_commit_day": "monday",
    "scan_days": ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
  },
  "preferences": {
    "auto_save_on_commit": true,
    "skip_weekends": false,
    "confidence_threshold": "low",
    "default_date_range": "current_week"
  },
  "activity_log": {
    "path": "data/activity-log.json",
    "enabled": true,
    "time_tolerance_min": 15,
    "calendar_fallback": true
  },
  "setup_complete": false
}
```
