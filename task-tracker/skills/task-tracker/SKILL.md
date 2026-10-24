---
name: task-tracker
description: Personal task tracker that is operated from the terminal. Use when the user wants to add a task, edit a task's title or description, view the details of a task, start a task, mark a task as in progress, blocked, or done, list tasks by status, see tasks completed in the last N days, weeks, or months, or open the task board dashboard.
allowed-tools: Bash(python3 *)
---

# Task Tracker
All task data is in one JSON file. Always use the script to read or change it.
Do not edit the JSON file directly.

Script: `python3 ${CLAUDE_SKILL_DIR}/scripts/tasks.py <command>`

## Statuses

| Status value | Label | User words that mean this status |
|---|---|---|
| `not_started` | Not Started | to do, new, backlog, not started, reset |
| `in_progress` | In Progress | start, working on, in progress, picked up |
| `blocked` | Blocked | blocked, stuck, waiting on, on hold |
| `done` | Done | done, complete, finished, closed |

A new task always starts as `not_started`.

## Commands

| User intent | Command |
|---|---|
| Add a task | `add "<title>"` |
| Add a task with details | `add "<title>" --description "<text>"` |
| Change the title | `edit <id> --title "<title>"` |
| Change the description | `edit <id> --description "<text>"` |
| Remove the description | `edit <id> --description ""` |
| Show the details of one task | `show <id>` |
| Change the status of a task | `move <id> <status>` |
| Mark a task as blocked, with a reason | `move <id> blocked --reason "<reason>"` |
| Complete a task | `done <id>` |
| List unfinished tasks | `list --status open` |
| List tasks with one status | `list --status <status>` |
| List all completed tasks | `list --status done` |
| Completed in a period | `list --status done --since <N><d\|w\|m>` |
| Open the board dashboard | `dashboard` |

## Rules

1. Convert time periods to the `--since` format. "Last 3 weeks" is `3w`. "Last 2 months" is `2m`.
2. If the user names a task by title and not by id, run `list --status all` first. Find the matching id.
3. If more than one task matches, ask the user which task. Do not guess.
4. Map the user's words to a status value with the Statuses table. If the words are unclear, ask the user.
5. If the user says why a task is blocked, pass the reason with `--reason`.
6. When the user gives more than a short title, put a short title in `title` and the details in `--description`.
7. When the user asks about the details of one task, run `show <id>`.
8. `edit --description` replaces the full text. To add text to a description, run `show <id>` first, then pass the old and the new text together.
9. If the user says "this task", use the task from the conversation. If no task is clear, ask which task.
10. If the user asks to edit a description but gives no new text, run `show <id>`, show the current text, and ask for the new text.
11. `edit` does not change the status. For "rename and start", run `edit` and then `move`.
12. Show list results as a Markdown table with the columns: id, title, status, date. Show the status label, not the value.
13. After `add`, `edit`, `move`, or `done`, confirm the action in one sentence.
14. The dashboard is read-only. If the user asks to change data from the dashboard, tell them to use the terminal.
