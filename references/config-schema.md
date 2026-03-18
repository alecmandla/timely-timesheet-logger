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
    "user_id": "string — Your Monday.com user ID (used for People column filtering)"
  },
  "boards": [
    {
      "board_id": "string — Monday.com board ID",
      "board_name": "string — Human-readable board name (for display in reports)",
      "timely_name_column_id": "string — Column ID containing the Timely project name, or '__item_name__' to use the item name itself",
      "search_terms_column_id": "string — Column ID for reading/writing search terms",
      "ignorable_terms_column_id": "string — Column ID for ignorable search terms (optional, can be empty string)",
      "people_column_id": "string — Column ID for the People column (used to filter to current user's projects)",
      "status_filter": {
        "mode": "string — 'status_column', 'groups', or 'both'",
        "status_column_id": "string — Column ID for status (required if mode is 'status_column' or 'both')",
        "active_statuses": "array of strings — Status values that mean 'actively tracking time' (required if mode is 'status_column' or 'both')",
        "active_groups": "array of strings — Group IDs that contain active projects (required if mode is 'groups' or 'both')"
      },
      "billable": {
        "mode": "string — 'column', 'checkbox', 'all_billable', 'all_non_billable', or 'unknown'",
        "column_id": "string — Column ID for billable status (required if mode is 'column' or 'checkbox')",
        "billable_values": "array of strings — Column values that mean billable (required if mode is 'column')"
      }
    }
  ],
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
- `timely.user_id` — Found via the Timely API or extracted from the URL
- `monday.user_id` — Found by calling `list_users_and_teams` with `getMe: true`
- `boards[].board_id` — Found by searching Monday.com boards via `get_user_context`
- `boards[].board_name` — Returned by `get_board_info`
- All column IDs — Found by reading board column metadata via `get_board_info`
- `boards[].status_filter.active_groups` — Group names/IDs returned by `get_board_info`

### User-provided (must ask or guide)
- Timely login session — User must be logged in via the browser
- Monday.com connection — Must be connected as a Cowork MCP connector
- Gmail connection — Must be connected as a Cowork MCP connector (optional but recommended)
- Board selection — User chooses which boards to track
- Column mappings — User confirms which columns serve which purpose (skill suggests based on column names/types)
- Active statuses — User identifies which status values mean "in progress"
- Billable mapping — User defines how billable status is determined per board

## Default Config Template

```json
{
  "timely": {
    "account_id": "",
    "user_id": "",
    "base_url": "https://app.timelyapp.com"
  },
  "monday": {
    "user_id": ""
  },
  "boards": [],
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
    "path": "data/activity-log.txt",
    "enabled": true,
    "time_tolerance_min": 15,
    "calendar_fallback": true
  },
  "setup_complete": false
}
```

## Migration from Single-Board Config

If you have an existing `config.json` with the old single-board format (with `monday.board_id`, `monday.timely_name_column_id`, etc.), the skill will detect this and offer to migrate it to the new multi-board format. The migration:

1. Reads the old `monday.*` fields
2. Creates a single entry in `boards[]` with those values
3. Asks the user to provide the additional fields that didn't exist before (people_column_id, status_filter, billable)
4. Removes the old `monday.board_id`, `monday.timely_name_column_id`, `monday.client_name_column_id`, `monday.search_terms_column_id`, and `monday.ignorable_terms_column_id` fields
5. Preserves `monday.user_id`
