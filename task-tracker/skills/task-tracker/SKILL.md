---
name: task-tracker
description: Personal task tracker that is operated from the terminal. Use when the user wants to add a task, complete a task, list open tasks, list completed tasks, see tasks completed in the last N days, weeks, or months, or open the task progress dashboard.
allowed-tools: Bash(python3 *)
---

# Task Tracker
All task data is in one JSON file. Always use the script to read or change it.
Do not edit the JSON file directly.

Script: `python3 ${CLAUDE_SKILL_DIR}/scripts/tasks.py <command>`

## Commands

| User intent | Command |
|---|---|
| Add a task | `add "<title>"` |
| Complete a task | `done <id>` |
| List open tasks | `list --status open` |
| List all completed tasks | `list --status done` |
| Completed in a period | `list --status done --since <N><d\|w\|m>` |
| Open the dashboard | `dashboard` |

## Rules

1. Convert time periods to the `--since` format. "Last 3 weeks" is `3w`. "Last 2 months" is `2m`.
2. If the user names a task by title and not by id, run `list --status open` first. Find the matching id.
3. If more than one task matches, ask the user which task. Do not guess.
4. Show list results as a Markdown table with the columns: id, title, status, date.
5. After `add` or `done`, confirm the action in one sentence.
6. The dashboard is read-only. If the user asks to change data from the dashboard, tell them to use the terminal.