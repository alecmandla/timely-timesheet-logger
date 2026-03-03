# Tracking Approach — Why Local JSON, Not Timely Tags

## The Problem
Timely does not support tagging or annotating unlogged memories. The Memory Tracker entries are read-only until you assign them to a project and log them. There is no intermediate state between "unlogged memory" and "logged time entry."

Timely does have status states on entries (No state, Build, Locked, Build and locked, Needs build), but these are organization-level configurations managed by an admin and should not be modified by this skill without explicit admin approval.

## The Solution: Local JSON Tracking File

Instead of marking entries inside Timely, we maintain a `data/weekly-tracking.json` file that records which memories matched which projects during daily scans. This file serves as the "staging area" between scanning (daily) and committing (Friday).

### Advantages:
- **Zero risk**: Nothing in Timely is touched during daily scans
- **Full audit trail**: Every match, confidence level, and term is recorded
- **Portable**: The tracking file can be shared, reviewed, or used for analytics
- **Reliable**: No dependency on Timely UI states or features that might change

### How Commit Reconnects to the Right Entries:
During the Friday commit, the skill needs to find the same memory entries it scanned during the week. It matches by:
1. **Date** — navigate to the correct day
2. **Memory text** — match the description stored in the tracking file against what's on the page
3. **Time range** — secondary confirmation that it's the same entry

This combination should be unique enough to identify the correct entry. If an entry can't be found (maybe the user already logged it manually), skip it and note it in the report.

### File Lifecycle:
- **Created**: On the first daily scan of the week (or manual run)
- **Appended to**: Each subsequent daily scan adds its results
- **Read by**: The Friday commit process
- **Archived**: After a successful Friday commit, the file can be moved to `data/archive/` with a date stamp
- **Reset**: A new file is created for the next week
