# task-tracker

A Claude Code skill for a personal task list. You manage the list from the Claude Code terminal in plain English.
A read-only dashboard in the browser shows your progress.

## Features

- Add a task.
- Complete a task by its id or its title.
- List open tasks, completed tasks, or all tasks.
- List the tasks completed in the last N days, weeks, or months.
- Open a dashboard with totals, a weekly completion chart, open tasks, and recently completed tasks.

## Usage

Type a request in plain English. Claude starts the skill when the request matches:

```
> add a task: write the Q4 report
> what tasks are open?
> complete the Q4 report task
> what did I complete in the last 3 weeks?
> show my task dashboard
```

You can also start the skill directly with `/task-tracker`, for example `/task-tracker add review PR 42`.

The dashboard is for viewing only. To change a task, use the terminal.

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
| `tasks.py add "<title>"` | Add an open task. |
| `tasks.py done <id>` | Mark a task as done. |
| `tasks.py list [--status open\|done\|all]` | List tasks. The default status is `all`. |
| `tasks.py list --status done --since <N><d\|w\|m>` | List the tasks completed in the period, for example `--since 3w`. |
| `tasks.py dashboard [--no-open]` | Write the dashboard file and open it in the browser. |

## License

Public domain, under [The Unlicense](../LICENSE). You can use this code for any purpose, with no conditions.
