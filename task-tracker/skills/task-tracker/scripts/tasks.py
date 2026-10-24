#!/usr/bin/env python3
"""Command-line task tracker for the task-tracker skill.

Statuses: not_started -> in_progress -> blocked -> done (any move is allowed).

Commands:
  add "<title>" [--description TEXT]     Add a task with status not_started.
  edit <id> [--title T] [--description D]
                                         Change the title or description. --description "" clears it.
  show <id>                              Print all fields of one task.
  move <id> <status> [--reason TEXT]     Change the status. --reason applies to blocked.
  done <id>                              Short form of: move <id> done.
  list [--status S] [--since PERIOD]     List tasks. S is a status, open (not done) or all.
                                         PERIOD is <N>d, <N>w or <N>m.
  dashboard [--no-open]                  Write a read-only HTML board and open it.

Data file: $TASK_TRACKER_HOME/tasks.json (default: ~/.task-tracker/tasks.json).
Only the Python standard library is used, so there is nothing to install.
"""

import argparse
import calendar
import html
import json
import os
import re
import sys
import tempfile
import webbrowser
from datetime import datetime, timedelta
from pathlib import Path

TIME_FORMAT = "%Y-%m-%dT%H:%M:%S"
DASHBOARD_WEEKS = 12
DONE_COLUMN_LIMIT = 20

# Board order. The values are the labels shown to the user.
STATUSES = {
    "not_started": "Not Started",
    "in_progress": "In Progress",
    "blocked": "Blocked",
    "done": "Done",
}
# Statuses written by version 0.1.x.
LEGACY_STATUSES = {"open": "not_started"}


# ---------------------------------------------------------------- storage

def data_dir():
    return Path(os.environ.get("TASK_TRACKER_HOME", str(Path.home() / ".task-tracker"))).expanduser()


def load():
    path = data_dir() / "tasks.json"
    if not path.exists():
        return {"next_id": 1, "tasks": []}
    with path.open(encoding="utf-8") as f:
        data = json.load(f)
    for task in data["tasks"]:
        migrate(task)
    return data


def migrate(task):
    """Upgrade a task from an older file format in place."""
    task["status"] = LEGACY_STATUSES.get(task["status"], task["status"])
    task.setdefault("status_changed_at", task.get("updated_at") or task.get("completed_at") or task["created_at"])
    task.setdefault("updated_at", task["status_changed_at"])
    task.setdefault("blocked_reason", None)
    task.setdefault("description", None)


def save(data):
    directory = data_dir()
    directory.mkdir(parents=True, exist_ok=True)
    # Write to a temporary file, then rename it. A crash never leaves a half-written tasks.json.
    fd, tmp_path = tempfile.mkstemp(dir=str(directory), suffix=".tmp")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
        f.write("\n")
    os.replace(tmp_path, str(directory / "tasks.json"))


def find_task(data, task_id):
    task = next((t for t in data["tasks"] if t["id"] == task_id), None)
    if task is None:
        fail("No task with id {}.".format(task_id))
    return task


# ---------------------------------------------------------------- time helpers

def now():
    return datetime.now().replace(microsecond=0)


def parse_time(value):
    return datetime.strptime(value, TIME_FORMAT)


def subtract_months(dt, months):
    index = dt.year * 12 + (dt.month - 1) - months
    year, month = divmod(index, 12)
    month += 1
    # Clamp the day, for example 31 March minus 1 month is 28/29 February.
    day = min(dt.day, calendar.monthrange(year, month)[1])
    return dt.replace(year=year, month=month, day=day)


def parse_since(value, reference):
    """Convert '10d', '3w' or '2m' into the start datetime of that period."""
    match = re.fullmatch(r"(\d+)([dwm])", value.strip().lower())
    if not match:
        fail("Invalid --since value '{}'. Use <N>d, <N>w or <N>m, for example 3w.".format(value))
    amount, unit = int(match.group(1)), match.group(2)
    if unit == "d":
        return reference - timedelta(days=amount)
    if unit == "w":
        return reference - timedelta(weeks=amount)
    return subtract_months(reference, amount)


def relevant_time(task):
    """Completion time for done tasks, time of the last status change for the others."""
    return parse_time(task["completed_at"] or task["status_changed_at"])


def format_time(value):
    return parse_time(value).strftime("%Y-%m-%d %H:%M") if value else "-"


# ---------------------------------------------------------------- output

def fail(message):
    print("Error: " + message, file=sys.stderr)
    sys.exit(1)


def describe(task):
    if task["status"] == "blocked" and task["blocked_reason"]:
        return "{} (blocked: {})".format(task["title"], task["blocked_reason"])
    return task["title"]


def print_table(tasks):
    if not tasks:
        print("No tasks found.")
        return
    rows = [("ID", "STATUS", "DATE", "TITLE")]
    for task in tasks:
        rows.append((str(task["id"]), task["status"], relevant_time(task).strftime("%Y-%m-%d"), describe(task)))
    widths = [max(len(row[i]) for row in rows) for i in range(3)]
    for row in rows:
        print("  ".join(cell.ljust(widths[i]) for i, cell in enumerate(row[:3])) + "  " + row[3])
    print("\n{} task(s)".format(len(tasks)))


# ---------------------------------------------------------------- commands

def cmd_add(args):
    title = " ".join(args.title).strip()
    if not title:
        fail("The task title is empty.")
    data = load()
    created = now().strftime(TIME_FORMAT)
    task = {
        "id": data["next_id"],
        "title": title,
        "description": clean_description(args.description),
        "status": "not_started",
        "created_at": created,
        "updated_at": created,
        "status_changed_at": created,
        "completed_at": None,
        "blocked_reason": None,
    }
    data["tasks"].append(task)
    data["next_id"] += 1
    save(data)
    print("Added task {}: {}".format(task["id"], task["title"]))


def clean_description(value):
    """An empty or blank description is stored as null."""
    if value is None:
        return None
    return value.strip() or None


def cmd_edit(args):
    if args.title is None and args.description is None:
        fail("Nothing to change. Use --title, --description, or both.")
    if args.title is not None and not args.title.strip():
        fail("The task title is empty.")
    data = load()
    task = find_task(data, args.id)
    if args.title is not None:
        task["title"] = args.title.strip()
    if args.description is not None:
        task["description"] = clean_description(args.description)
    # An edit is not a status change, so status_changed_at stays the same.
    task["updated_at"] = now().strftime(TIME_FORMAT)
    save(data)
    print("Updated task {}: {}".format(task["id"], task["title"]))


def cmd_show(args):
    task = find_task(load(), args.id)
    print("#{}  {}".format(task["id"], task["title"]))
    print("Status:     {}".format(STATUSES[task["status"]]))
    if task["status"] == "blocked":
        print("Blocked:    {}".format(task["blocked_reason"] or "(no reason given)"))
    print("Created:    {}".format(format_time(task["created_at"])))
    print("Updated:    {}".format(format_time(task["updated_at"])))
    print("Completed:  {}".format(format_time(task["completed_at"])))
    print()
    if task["description"]:
        print("Description:")
        for line in task["description"].splitlines():
            print("  " + line)
    else:
        print("Description: (none)")


def move(task_id, status, reason=None):
    data = load()
    task = find_task(data, task_id)
    if task["status"] == status and not (status == "blocked" and reason):
        fail("Task {} is already {}.".format(task["id"], STATUSES[status]))
    stamp = now().strftime(TIME_FORMAT)
    task["status"] = status
    task["status_changed_at"] = stamp
    task["updated_at"] = stamp
    # A move out of done reopens the task, so the completion time no longer applies.
    task["completed_at"] = stamp if status == "done" else None
    task["blocked_reason"] = reason if status == "blocked" else None
    save(data)
    if status == "done":
        print("Completed task {}: {}".format(task["id"], task["title"]))
    else:
        print("Moved task {} to {}: {}".format(task["id"], STATUSES[status], describe(task)))


def cmd_move(args):
    if args.reason and args.status != "blocked":
        fail("--reason applies only to the blocked status.")
    move(args.id, args.status, args.reason)


def cmd_done(args):
    move(args.id, "done")


def cmd_list(args):
    tasks = load()["tasks"]
    if args.status == "open":
        tasks = [t for t in tasks if t["status"] != "done"]
    elif args.status != "all":
        tasks = [t for t in tasks if t["status"] == args.status]
    if args.since:
        start = parse_since(args.since, now())
        tasks = [t for t in tasks if relevant_time(t) >= start]
        print("Since {}:".format(start.strftime("%Y-%m-%d")))
    # Board order for unfinished tasks, then the newest completions.
    order = list(STATUSES)
    unfinished = sorted((t for t in tasks if t["status"] != "done"),
                        key=lambda t: (order.index(t["status"]), t["id"]))
    done = sorted((t for t in tasks if t["status"] == "done"), key=relevant_time, reverse=True)
    print_table(unfinished + done)


def cmd_dashboard(args):
    path = data_dir() / "dashboard.html"
    data_dir().mkdir(parents=True, exist_ok=True)
    path.write_text(render_dashboard(load()["tasks"], now()), encoding="utf-8")
    print("Dashboard written to {}".format(path))
    if not args.no_open:
        webbrowser.open(path.as_uri())


# ---------------------------------------------------------------- dashboard

DASHBOARD_TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Task Board</title>
<style>
  :root {
    --bg: #f4f5f7; --card: #ffffff; --column: #ebecf0; --text: #172b4d; --muted: #5e6c84;
    --border: #dfe1e6; --accent: #0c66e4; --track: #dfe1e6;
    --not-started: #8590a2; --in-progress: #0c66e4; --blocked: #c9372c; --done: #1f845a;
  }
  @media (prefers-color-scheme: dark) {
    :root {
      --bg: #1d2125; --card: #2c333a; --column: #22272b; --text: #dee4ea; --muted: #9fadbc;
      --border: #38414a; --accent: #579dff; --track: #38414a;
      --not-started: #8c9bab; --in-progress: #579dff; --blocked: #f87168; --done: #4bce97;
    }
  }
  * { box-sizing: border-box; }
  body { margin: 0; background: var(--bg); color: var(--text);
         font: 14px/1.45 -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }
  main { max-width: 1280px; margin: 0 auto; padding: 28px 16px 48px; }
  h1 { font-size: 22px; margin: 0 0 4px; }
  h2 { font-size: 14px; margin: 0 0 14px; }
  .sub { color: var(--muted); font-size: 13px; margin: 0 0 20px; }
  .stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 10px; margin-bottom: 20px; }
  .stat { background: var(--card); border: 1px solid var(--border); border-radius: 8px; padding: 12px 14px; }
  .label { color: var(--muted); font-size: 11px; text-transform: uppercase; letter-spacing: .04em; }
  .value { font-size: 24px; font-weight: 600; font-variant-numeric: tabular-nums; }
  .progress { height: 6px; background: var(--track); border-radius: 3px; overflow: hidden; margin-top: 6px; }
  .progress > div { height: 100%; background: var(--done); }
  .hint { font-size: 12px; color: var(--muted); }

  .board { display: grid; grid-template-columns: repeat(4, minmax(220px, 1fr)); gap: 12px;
           overflow-x: auto; margin-bottom: 20px; align-items: start; }
  .column { background: var(--column); border-radius: 8px; padding: 10px; min-height: 120px; }
  .column-head { display: flex; align-items: center; gap: 8px; padding: 2px 4px 10px;
                 font-size: 12px; font-weight: 600; text-transform: uppercase; letter-spacing: .04em; color: var(--muted); }
  .dot { width: 8px; height: 8px; border-radius: 50%; flex: none; }
  .column-count { margin-left: auto; font-variant-numeric: tabular-nums; }
  .ticket { display: block; color: inherit; text-decoration: none;
            background: var(--card); border: 1px solid var(--border); border-left: 3px solid var(--status);
            border-radius: 6px; padding: 10px 12px; margin-bottom: 8px; }
  .ticket:hover { border-color: var(--accent); border-left-color: var(--status); }
  .ticket:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
  .ticket-title { font-weight: 500; overflow-wrap: anywhere; }
  .desc-preview { margin-top: 4px; font-size: 12px; color: var(--muted); overflow-wrap: anywhere;
                  display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
  .ticket-meta { display: flex; justify-content: space-between; gap: 8px; margin-top: 6px;
                 font-size: 12px; color: var(--muted); font-variant-numeric: tabular-nums; }
  .reason { margin-top: 6px; font-size: 12px; color: var(--blocked); overflow-wrap: anywhere; }
  .empty { color: var(--muted); font-size: 12px; padding: 4px; }
  .more { color: var(--muted); font-size: 12px; text-align: center; padding: 4px; }

  .panel { background: var(--card); border: 1px solid var(--border); border-radius: 8px; padding: 16px; }
  .chart { display: flex; align-items: flex-end; gap: 6px; height: 140px; overflow-x: auto; }
  .col { flex: 1; display: flex; flex-direction: column; align-items: center; justify-content: flex-end; height: 100%; min-width: 40px; }
  .bar { width: 100%; max-width: 36px; background: var(--done); border-radius: 3px 3px 0 0; }
  .count { font-size: 12px; color: var(--muted); font-variant-numeric: tabular-nums; }
  .week { font-size: 11px; color: var(--muted); margin-top: 4px; white-space: nowrap; }

  /* Pop-up: hidden until the URL fragment is #task-<id>. No JavaScript. */
  .modal { display: none; position: fixed; inset: 0; z-index: 10; align-items: center; justify-content: center; }
  .modal:target { display: flex; }
  .backdrop { position: absolute; inset: 0; background: rgba(9, 30, 66, .54); }
  .modal-panel { position: relative; width: min(640px, calc(100% - 32px)); max-height: 85vh; overflow: auto;
                 background: var(--card); border: 1px solid var(--border); border-top: 4px solid var(--status);
                 border-radius: 8px; padding: 20px 24px; box-shadow: 0 12px 32px rgba(0, 0, 0, .3); }
  .modal-head { display: flex; align-items: center; gap: 8px; font-size: 12px; font-weight: 600;
                text-transform: uppercase; letter-spacing: .04em; color: var(--muted); }
  .modal-close { margin-left: auto; font-size: 22px; line-height: 1; color: var(--muted); text-decoration: none; }
  .modal-close:hover { color: var(--text); }
  .modal-title { font-size: 20px; margin: 10px 0 12px; overflow-wrap: anywhere; }
  .modal-desc { white-space: pre-wrap; overflow-wrap: anywhere; margin: 12px 0 16px; }
  .modal-desc.empty { color: var(--muted); }
  .modal-fields { display: grid; grid-template-columns: max-content 1fr; gap: 4px 16px; margin: 0;
                  padding-top: 12px; border-top: 1px solid var(--border); font-size: 13px; }
  .modal-fields dt { color: var(--muted); }
  .modal-fields dd { margin: 0; font-variant-numeric: tabular-nums; }
</style>
</head>
<body>
<main>
__BODY__
</main>
</body>
</html>
"""

STATUS_COLORS = {
    "not_started": "var(--not-started)",
    "in_progress": "var(--in-progress)",
    "blocked": "var(--blocked)",
    "done": "var(--done)",
}


def stat_card(label, value, extra=""):
    return '<div class="stat"><div class="label">{}</div><div class="value">{}</div>{}</div>'.format(label, value, extra)


def age(since, current):
    days = (current - since).days
    return "today" if days == 0 else "{} d".format(days)


def blocked_reason_html(task):
    if task["status"] == "blocked" and task["blocked_reason"]:
        return '<div class="reason">{}</div>'.format(html.escape(task["blocked_reason"]))
    return ""


def ticket(task, current):
    """One card on the board. A click opens the pop-up of the task (see task_modal)."""
    if task["status"] == "done":
        meta = "Done {}".format(parse_time(task["completed_at"]).strftime("%b %d"))
    elif task["status"] == "not_started":
        meta = "Created {}".format(age(parse_time(task["created_at"]), current))
    else:
        meta = "{} {}".format(STATUSES[task["status"]], age(parse_time(task["status_changed_at"]), current))
    preview = ""
    if task["description"]:
        preview = '<div class="desc-preview">{}</div>'.format(html.escape(task["description"]))
    return (
        '<a class="ticket" href="#task-{id}" style="--status:{color}">'
        '<div class="ticket-title">{title}</div>{preview}{reason}'
        '<div class="ticket-meta"><span>#{id}</span><span>{meta}</span></div>'
        "</a>"
    ).format(color=STATUS_COLORS[task["status"]], title=html.escape(task["title"]),
             preview=preview, reason=blocked_reason_html(task), id=task["id"], meta=meta)


def task_modal(task):
    """Pop-up with all fields of a task. CSS shows it when the URL fragment is #task-<id>."""
    description = (
        '<div class="modal-desc">{}</div>'.format(html.escape(task["description"]))
        if task["description"] else '<div class="modal-desc empty">No description.</div>'
    )
    fields = [("Created", task["created_at"]), ("Updated", task["updated_at"]),
              ("Status changed", task["status_changed_at"]), ("Completed", task["completed_at"])]
    rows = "".join("<dt>{}</dt><dd>{}</dd>".format(label, format_time(value)) for label, value in fields)
    # "#close" matches no element, so closing does not scroll the page to the top.
    return (
        '<div class="modal" id="task-{id}" role="dialog" aria-labelledby="task-{id}-title">'
        '<a class="backdrop" href="#close" aria-label="Close"></a>'
        '<div class="modal-panel" style="--status:{color}">'
        '<div class="modal-head"><span class="dot" style="background:{color}"></span>'
        '<span class="modal-status">{label} &middot; #{id}</span>'
        '<a class="modal-close" href="#close" aria-label="Close">&times;</a></div>'
        '<h2 class="modal-title" id="task-{id}-title">{title}</h2>{reason}{description}'
        '<dl class="modal-fields">{rows}</dl>'
        "</div></div>"
    ).format(id=task["id"], color=STATUS_COLORS[task["status"]], label=STATUSES[task["status"]],
             title=html.escape(task["title"]), reason=blocked_reason_html(task),
             description=description, rows=rows)


def visible_tasks(status, tasks):
    """The cards of one column, in board order. Done shows only the newest DONE_COLUMN_LIMIT."""
    if status == "done":
        return sorted(tasks, key=relevant_time, reverse=True)[:DONE_COLUMN_LIMIT]
    return sorted(tasks, key=lambda t: t["status_changed_at"])


def board_column(status, tasks, current):
    shown = visible_tasks(status, tasks)
    cards = "".join(ticket(t, current) for t in shown) or '<div class="empty">No tasks</div>'
    if len(tasks) > len(shown):
        cards += '<div class="more">+{} older</div>'.format(len(tasks) - len(shown))
    return (
        '<section class="column">'
        '<div class="column-head"><span class="dot" style="background:{color}"></span>{label}'
        '<span class="column-count">{count}</span></div>{cards}</section>'
    ).format(color=STATUS_COLORS[status], label=STATUSES[status], count=len(tasks), cards=cards)


def render_dashboard(tasks, current):
    """Render static HTML. The page has no forms and no scripts, so it cannot change data.
    Pop-ups use the CSS :target selector, so they also work without scripts."""
    by_status = {s: [t for t in tasks if t["status"] == s] for s in STATUSES}
    done = by_status["done"]
    rate = round(100 * len(done) / len(tasks)) if tasks else 0
    last_7 = sum(1 for t in done if relevant_time(t) >= current - timedelta(days=7))

    stats = "".join(
        [stat_card("Total", len(tasks))]
        + [stat_card(STATUSES[s], len(by_status[s])) for s in ("not_started", "in_progress", "blocked")]
        + [stat_card("Done", len(done),
                     '<div class="progress"><div style="width:{}%"></div></div>'
                     '<div class="hint">{}% complete</div>'.format(rate, rate)),
           stat_card("Done, last 7 days", last_7)]
    )
    board = "".join(board_column(s, by_status[s], current) for s in STATUSES)
    modals = "".join(task_modal(t) for s in STATUSES for t in visible_tasks(s, by_status[s]))

    # Completed tasks per week (weeks start on Monday), oldest week on the left.
    this_week = (current - timedelta(days=current.weekday())).date()
    weeks = [this_week - timedelta(weeks=i) for i in reversed(range(DASHBOARD_WEEKS))]
    counts = {w: 0 for w in weeks}
    for t in done:
        d = relevant_time(t).date()
        w = d - timedelta(days=d.weekday())
        if w in counts:
            counts[w] += 1
    peak = max(counts.values()) or 1
    columns = "".join(
        '<div class="col"><div class="count">{c}</div>'
        '<div class="bar" style="height:{h}%"></div>'
        '<div class="week">{label}</div></div>'.format(
            c=counts[w], h=max(2, round(85 * counts[w] / peak)) if counts[w] else 0,
            label=w.strftime("%b %d"))
        for w in weeks
    )

    body = (
        "<h1>Task Board</h1>"
        '<p class="sub">Generated {}. Read-only view: use Claude Code in the terminal to change tasks.</p>'
        '<div class="stats">{}</div>'
        '<div class="board">{}</div>'
        '<div class="panel"><h2>Completed per week (last {} weeks)</h2><div class="chart">{}</div></div>'
        "{}"
    ).format(current.strftime("%Y-%m-%d %H:%M"), stats, board, DASHBOARD_WEEKS, columns, modals)
    return DASHBOARD_TEMPLATE.replace("__BODY__", body)


# ---------------------------------------------------------------- entry point

def main():
    parser = argparse.ArgumentParser(description="Task tracker for the task-tracker skill.")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("add", help="add a task with status not_started")
    p.add_argument("title", nargs="+", help="task title")
    p.add_argument("--description", help="longer details of the task; line breaks are kept")
    p.set_defaults(func=cmd_add)

    p = sub.add_parser("edit", help="change the title or description of a task")
    p.add_argument("id", type=int, help="task id")
    p.add_argument("--title", help="new title")
    p.add_argument("--description", help='new description; "" removes it')
    p.set_defaults(func=cmd_edit)

    p = sub.add_parser("show", help="print all fields of one task")
    p.add_argument("id", type=int, help="task id")
    p.set_defaults(func=cmd_show)

    p = sub.add_parser("move", help="change the status of a task")
    p.add_argument("id", type=int, help="task id")
    p.add_argument("status", choices=list(STATUSES))
    p.add_argument("--reason", help="why the task is blocked (blocked status only)")
    p.set_defaults(func=cmd_move)

    p = sub.add_parser("done", help="mark a task as done (same as: move <id> done)")
    p.add_argument("id", type=int, help="task id")
    p.set_defaults(func=cmd_done)

    p = sub.add_parser("list", help="list tasks")
    p.add_argument("--status", choices=list(STATUSES) + ["open", "all"], default="all",
                   help="a status, open (every status except done) or all")
    p.add_argument("--since", help="only tasks in the last period: <N>d, <N>w or <N>m")
    p.set_defaults(func=cmd_list)

    p = sub.add_parser("dashboard", help="write the read-only HTML board and open it")
    p.add_argument("--no-open", action="store_true", help="write the file but do not open the browser")
    p.set_defaults(func=cmd_dashboard)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
