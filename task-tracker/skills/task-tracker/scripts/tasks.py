#!/usr/bin/env python3
"""Command-line task tracker for the task-tracker skill.

Commands:
  add "<title>"                          Add an open task.
  done <id>                              Mark a task as done.
  list [--status S] [--since PERIOD]     List tasks. S is open, done or all.
                                         PERIOD is <N>d, <N>w or <N>m.
  dashboard [--no-open]                  Write a read-only HTML dashboard and open it.

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


# ---------------------------------------------------------------- storage

def data_dir():
    return Path(os.environ.get("TASK_TRACKER_HOME", str(Path.home() / ".task-tracker"))).expanduser()


def load():
    path = data_dir() / "tasks.json"
    if not path.exists():
        return {"next_id": 1, "tasks": []}
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def save(data):
    directory = data_dir()
    directory.mkdir(parents=True, exist_ok=True)
    # Write to a temporary file, then rename it. A crash never leaves a half-written tasks.json.
    fd, tmp_path = tempfile.mkstemp(dir=str(directory), suffix=".tmp")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
        f.write("\n")
    os.replace(tmp_path, str(directory / "tasks.json"))


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
    """Completion time for done tasks, creation time for open tasks."""
    return parse_time(task["completed_at"] or task["created_at"])


# ---------------------------------------------------------------- output

def fail(message):
    print("Error: " + message, file=sys.stderr)
    sys.exit(1)


def print_table(tasks):
    if not tasks:
        print("No tasks found.")
        return
    rows = [("ID", "STATUS", "DATE", "TITLE")]
    for task in tasks:
        rows.append((str(task["id"]), task["status"], relevant_time(task).strftime("%Y-%m-%d"), task["title"]))
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
    task = {
        "id": data["next_id"],
        "title": title,
        "status": "open",
        "created_at": now().strftime(TIME_FORMAT),
        "completed_at": None,
    }
    data["tasks"].append(task)
    data["next_id"] += 1
    save(data)
    print("Added task {}: {}".format(task["id"], task["title"]))


def cmd_done(args):
    data = load()
    task = next((t for t in data["tasks"] if t["id"] == args.id), None)
    if task is None:
        fail("No task with id {}.".format(args.id))
    if task["status"] == "done":
        fail("Task {} is already done (completed {}).".format(task["id"], task["completed_at"][:10]))
    task["status"] = "done"
    task["completed_at"] = now().strftime(TIME_FORMAT)
    save(data)
    print("Completed task {}: {}".format(task["id"], task["title"]))


def cmd_list(args):
    tasks = load()["tasks"]
    if args.status != "all":
        tasks = [t for t in tasks if t["status"] == args.status]
    if args.since:
        start = parse_since(args.since, now())
        tasks = [t for t in tasks if relevant_time(t) >= start]
        print("Since {}:".format(start.strftime("%Y-%m-%d")))
    # Newest completions first, then open tasks in creation order.
    done = sorted((t for t in tasks if t["status"] == "done"), key=relevant_time, reverse=True)
    open_ = sorted((t for t in tasks if t["status"] == "open"), key=lambda t: t["id"])
    print_table(done + open_)


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
<title>Task Dashboard</title>
<style>
  :root {
    --bg: #f7f7f5; --card: #ffffff; --text: #1d1d1b; --muted: #6b6b66;
    --border: #e3e3de; --accent: #2f6fdb; --track: #ecece7;
  }
  @media (prefers-color-scheme: dark) {
    :root {
      --bg: #161615; --card: #1f1f1d; --text: #ececea; --muted: #9a9a94;
      --border: #33332f; --accent: #6b9cf0; --track: #2a2a27;
    }
  }
  * { box-sizing: border-box; }
  body { margin: 0; background: var(--bg); color: var(--text);
         font: 15px/1.5 -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }
  main { max-width: 960px; margin: 0 auto; padding: 32px 16px 48px; }
  h1 { font-size: 24px; margin: 0 0 4px; }
  h2 { font-size: 15px; margin: 0 0 16px; }
  .sub { color: var(--muted); font-size: 13px; margin: 0 0 24px; }
  .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 12px; margin-bottom: 16px; }
  .card { background: var(--card); border: 1px solid var(--border); border-radius: 10px; padding: 16px; margin-bottom: 16px; }
  .grid .card { margin-bottom: 0; }
  .label { color: var(--muted); font-size: 12px; text-transform: uppercase; letter-spacing: .04em; }
  .value { font-size: 28px; font-weight: 600; font-variant-numeric: tabular-nums; }
  .progress { height: 8px; background: var(--track); border-radius: 4px; overflow: hidden; margin-top: 8px; }
  .progress > div { height: 100%; background: var(--accent); }
  .chart { display: flex; align-items: flex-end; gap: 6px; height: 160px; }
  .col { flex: 1; display: flex; flex-direction: column; align-items: center; justify-content: flex-end; height: 100%; min-width: 0; }
  .bar { width: 100%; max-width: 36px; background: var(--accent); border-radius: 3px 3px 0 0; }
  .count { font-size: 12px; color: var(--muted); font-variant-numeric: tabular-nums; }
  .week { font-size: 11px; color: var(--muted); margin-top: 4px; white-space: nowrap; }
  table { width: 100%; border-collapse: collapse; }
  th, td { text-align: left; padding: 8px 6px; border-bottom: 1px solid var(--border); vertical-align: top; }
  th { color: var(--muted); font-size: 12px; font-weight: 500; text-transform: uppercase; }
  td.num { font-variant-numeric: tabular-nums; white-space: nowrap; color: var(--muted); }
  .empty { color: var(--muted); }
  .two { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 16px; }
</style>
</head>
<body>
<main>
__BODY__
</main>
</body>
</html>
"""


def stat_card(label, value, extra=""):
    return '<div class="card"><div class="label">{}</div><div class="value">{}</div>{}</div>'.format(label, value, extra)


def task_table(rows, headers):
    if not rows:
        return '<p class="empty">None.</p>'
    head = "".join("<th>{}</th>".format(h) for h in headers)
    body = ""
    for row in rows:
        body += "<tr>" + "".join(
            '<td class="num">{}</td>'.format(c) if i != 1 else "<td>{}</td>".format(c)
            for i, c in enumerate(row)
        ) + "</tr>"
    return "<table><thead><tr>{}</tr></thead><tbody>{}</tbody></table>".format(head, body)


def render_dashboard(tasks, current):
    """Render static HTML. The page has no forms and no scripts, so it cannot change data."""
    done = [t for t in tasks if t["status"] == "done"]
    open_ = [t for t in tasks if t["status"] == "open"]
    rate = round(100 * len(done) / len(tasks)) if tasks else 0
    last_7 = sum(1 for t in done if relevant_time(t) >= current - timedelta(days=7))
    last_30 = sum(1 for t in done if relevant_time(t) >= current - timedelta(days=30))

    cards = "".join([
        stat_card("Total tasks", len(tasks)),
        stat_card("Open", len(open_)),
        stat_card("Completed", len(done),
                  '<div class="progress"><div style="width:{}%"></div></div>'
                  '<div class="count">{}% complete</div>'.format(rate, rate)),
        stat_card("Done, last 7 days", last_7),
        stat_card("Done, last 30 days", last_30),
    ])

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

    open_rows = [
        (t["id"], html.escape(t["title"]), "{} d".format((current - parse_time(t["created_at"])).days))
        for t in sorted(open_, key=lambda t: t["created_at"])
    ]
    recent = sorted(done, key=relevant_time, reverse=True)[:10]
    done_rows = [(t["id"], html.escape(t["title"]), relevant_time(t).strftime("%Y-%m-%d")) for t in recent]

    body = (
        "<h1>Task Dashboard</h1>"
        '<p class="sub">Generated {}. Read-only view: use Claude Code in the terminal to change tasks.</p>'
        '<div class="grid">{}</div>'
        '<div class="card"><h2>Completed per week (last {} weeks)</h2><div class="chart">{}</div></div>'
        '<div class="two">'
        '<div class="card"><h2>Open tasks (oldest first)</h2>{}</div>'
        '<div class="card"><h2>Recently completed</h2>{}</div>'
        "</div>"
    ).format(
        current.strftime("%Y-%m-%d %H:%M"), cards, DASHBOARD_WEEKS, columns,
        task_table(open_rows, ("ID", "Title", "Age")),
        task_table(done_rows, ("ID", "Title", "Completed")),
    )
    return DASHBOARD_TEMPLATE.replace("__BODY__", body)


# ---------------------------------------------------------------- entry point

def main():
    parser = argparse.ArgumentParser(description="Task tracker for the task-tracker skill.")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("add", help="add an open task")
    p.add_argument("title", nargs="+", help="task title")
    p.set_defaults(func=cmd_add)

    p = sub.add_parser("done", help="mark a task as done")
    p.add_argument("id", type=int, help="task id")
    p.set_defaults(func=cmd_done)

    p = sub.add_parser("list", help="list tasks")
    p.add_argument("--status", choices=("open", "done", "all"), default="all")
    p.add_argument("--since", help="only tasks in the last period: <N>d, <N>w or <N>m")
    p.set_defaults(func=cmd_list)

    p = sub.add_parser("dashboard", help="write the read-only HTML dashboard and open it")
    p.add_argument("--no-open", action="store_true", help="write the file but do not open the browser")
    p.set_defaults(func=cmd_dashboard)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
