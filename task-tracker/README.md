# task-tracker

A Claude Code skill for a personal task list. You manage the list from the Claude Code terminal in plain English.
A read-only board in the browser shows your progress.

## Features

- Add a task, with an optional description for the details.
- Edit the title or the description of a task, and show all details of one task.
- Move a task through four statuses: Not Started, In Progress, Blocked, and Done.
- Record why a task is blocked.
- Refer to a task by its id or its title.
- List tasks by status, or list all unfinished tasks.
- List the tasks completed in the last N days, weeks, or months.
- Open a board with one column for each status, totals, and a weekly completion chart.
  Click a card to open a pop-up with the full description and all fields.

## Statuses

```
Not Started ──► In Progress ──► Done
                   │   ▲
                   ▼   │
                  Blocked
```

A new task starts as Not Started. You can move a task from any status to any other status.
A move out of Done reopens the task.

## Usage

Type a request in plain English. Claude starts the skill when the request matches:

```
> add a task: write the Q4 report, details: collect revenue numbers from finance
> show the details of the Q4 report
> add to its description: send it to the CFO by Friday
> start the Q4 report
> the login bug is blocked, waiting on API keys
> what am I working on?
> complete the Q4 report task
> what did I complete in the last 3 weeks?
> show my task board
```

You can also start the skill directly with `/task-tracker`, for example `/task-tracker add review PR 42`.

The board is for viewing only. To change a task, use the terminal.

## Installation

### As a plugin (recommended)

```
/plugin marketplace add rahulmg05/claude-skills
/plugin install task-tracker@claude-skills
```

### As a personal skill (for development)

Clone the repository and link the skill folder into your personal skills folder:

```bash
git clone https://github.com/rahulmg05/claude-skills.git
ln -s "$PWD/claude-skills/task-tracker/skills/task-tracker" ~/.claude/skills/task-tracker
```

## Requirements

- Claude Code
- Python 3.7 or later. The script uses only the Python standard library, so you do not need to install packages.

## Data storage

The skill stores all tasks in `~/.task-tracker/tasks.json`. The dashboard file is `~/.task-tracker/dashboard.html`.
Each user has a separate list. The same list is used in all projects.

To store the data in a different folder, set the `TASK_TRACKER_HOME` environment variable.
For example, to keep a separate list for one project, add this to the project's `.claude/settings.json`:

```json
{
  "env": {
    "TASK_TRACKER_HOME": ".task-tracker"
  }
}
```

## Script reference

Claude runs `scripts/tasks.py` for each request. You can also run the script yourself:

| Command | Action |
|---|---|
| `tasks.py add "<title>" [--description "<text>"]` | Add a task with the status `not_started`. |
| `tasks.py edit <id> [--title "<title>"] [--description "<text>"]` | Change the title or the description. `--description ""` removes the description. |
| `tasks.py show <id>` | Print all fields of one task, including the full description. |
| `tasks.py move <id> <status>` | Change the status. `<status>` is `not_started`, `in_progress`, `blocked`, or `done`. |
| `tasks.py move <id> blocked --reason "<text>"` | Mark a task as blocked and record the reason. |
| `tasks.py done <id>` | Mark a task as done. This is the short form of `move <id> done`. |
| `tasks.py list [--status <status>\|open\|all]` | List tasks. `open` means all statuses except `done`. The default is `all`. |
| `tasks.py list --status done --since <N><d\|w\|m>` | List the tasks completed in the period, for example `--since 3w`. |
| `tasks.py dashboard [--no-open]` | Write the board file and open it in the browser. |

Data from version 0.1.x is converted automatically. The old status `open` becomes `not_started`.

## License

Public domain, under [The Unlicense](../LICENSE). You can use this code for any purpose, with no conditions.
