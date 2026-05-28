#!/usr/bin/env python3
"""
road, a personal goal progress tracker
Usage: road <command> [args]
"""

import json
import sys
import os
import re
from datetime import datetime, date, timedelta
from pathlib import Path

# Storage

DATA_FILE = Path(os.environ.get("ROAD_DATA", Path.home() / ".local" / "share" / "road" / "data.json"))

def load_data() -> dict:
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not DATA_FILE.exists():
        return {"entries": [], "next_id": 0}
    with open(DATA_FILE) as f:
        return json.load(f)

def save_data(data: dict):
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)

# Date parsing

def parse_date(s: str) -> date:
    """
    Accepts: 17.5.26 / 17.5 / 17.05.2026 / 17.05.26 / 2026-05-17 / today / yesterday
    Returns a date object.
    """
    s = s.strip().lower()
    today = date.today()

    if s in ("today", "t"):
        return today
    if s in ("yesterday", "y"):
        return today - timedelta(days=1)

    # ISO: 2026-05-17
    m = re.fullmatch(r"(\d{4})-(\d{1,2})-(\d{1,2})", s)
    if m:
        return date(int(m[1]), int(m[2]), int(m[3]))

    # European dot notation: DD.MM[.YY|.YYYY]
    m = re.fullmatch(r"(\d{1,2})\.(\d{1,2})(?:\.(\d{2,4}))?", s)
    if m:
        day, month = int(m[1]), int(m[2])
        year_raw = m[3]
        if year_raw is None:
            year = today.year
        elif len(year_raw) == 2:
            year = 2000 + int(year_raw)
        else:
            year = int(year_raw)
        return date(year, month, day)

    raise ValueError(f"Cannot parse date: '{s}'\n  Accepted formats: DD.MM.YYYY | DD.MM.YY | DD.MM | YYYY-MM-DD | today | yesterday")

# Week helper functions

def week_bounds(d: date):
    """Monday–Sunday of the week containing d."""
    monday = d - timedelta(days=d.weekday())
    sunday = monday + timedelta(days=6)
    return monday, sunday

def date_range_for_flag(flag: str, ref: date = None) -> tuple[date, date]:
    """Returns (start, end) inclusive for a given flag."""
    ref = ref or date.today()
    if flag == "d":
        return ref, ref
    if flag == "w":
        return week_bounds(ref)
    if flag == "m":
        return date(ref.year, ref.month, 1), ref
    if flag == "y":
        return date(ref.year, 1, 1), ref
    if flag == "a":
        return date(2000, 1, 1), ref   # effectively "all"; trimmed later
    raise ValueError(f"Unknown period flag: -{flag}")

# ANSI helper functions

RESET  = "\033[0m"
BOLD   = "\033[1m"
DIM    = "\033[2m"
GREEN  = "\033[32m"
CYAN   = "\033[36m"
YELLOW = "\033[33m"
RED    = "\033[31m"
WHITE  = "\033[97m"
GRAY   = "\033[90m"

def c(text, *codes):
    return "".join(codes) + str(text) + RESET

def bar(value, max_value, width=24, fill="█", empty="░"):
    if max_value == 0:
        filled = 0
    else:
        filled = round(value / max_value * width)
    return GREEN + fill * filled + GRAY + empty * (width - filled) + RESET

# Commands

def cmd_log(args):
    """road <number> [-d <date>]"""
    if not args:
        die("Usage: road <number> [-d <date>]")

    try:
        value = float(args[0])
    except ValueError:
        die(f"'{args[0]}' is not a valid number.")

    # optional -d flag
    entry_date = date.today()
    entry_time = datetime.now().strftime("%H:%M:%S")

    i = 1
    while i < len(args):
        if args[i] == "-d" and i + 1 < len(args):
            entry_date = parse_date(args[i + 1])
            entry_time = "00:00:00"
            i += 2
        else:
            die(f"Unknown argument: {args[i]}")

    data = load_data()
    eid = data["next_id"]
    entry = {
        "id":    eid,
        "value": value,
        "date":  entry_date.isoformat(),
        "time":  entry_time,
        "ts":    f"{entry_date.isoformat()} {entry_time}",
    }
    data["entries"].append(entry)
    data["next_id"] = eid + 1
    save_data(data)

    # pretty confirmation
    is_backlog = entry_date != date.today()
    tag = c(" BACKLOG ", BOLD, YELLOW) if is_backlog else c(" LOGGED  ", BOLD, GREEN)
    print(f"\n  {tag}  {c(fmt_value(value), BOLD, WHITE)}  "
          f"{c('→', GRAY)}  {c(entry_date.strftime('%a %d %b %Y'), CYAN)}"
          f"  {c(f'#{eid}', DIM)}\n")


def cmd_list(args):
    """road list [-d|-w|-m|-y|-a]"""
    flag, ref_date = parse_period_args(args, default="w")
    data = load_data()
    entries = data["entries"]

    if not entries:
        print(c("\n  No entries yet. Run: road <number>\n", GRAY))
        return

    all_dates = [date.fromisoformat(e["date"]) for e in entries]
    first_date = min(all_dates)

    if flag == "a":
        start, end = first_date, date.today()
    else:
        start, end = date_range_for_flag(flag, ref_date)
        start = max(start, first_date)

    # bucket by day
    days: dict[date, float] = {}
    d = start
    while d <= end:
        days[d] = 0.0
        d += timedelta(days=1)

    for e in entries:
        ed = date.fromisoformat(e["date"])
        if start <= ed <= end:
            days[ed] = days.get(ed, 0.0) + e["value"]

    active_days = {d: v for d, v in days.items() if v > 0}
    total = sum(days.values())
    max_val = max(days.values()) if days else 0

    # Header
    period_label = {
        "d": "Today",
        "w": f"Week of {start.strftime('%d %b')}",
        "m": start.strftime("%B %Y"),
        "y": str(start.year),
        "a": f"All time  ({first_date.strftime('%d %b %Y')} →)",
    }[flag]

    print()
    print(f"  {c('●', GREEN)} {c(period_label, BOLD, WHITE)}  "
          f"{c(f'{len(active_days)} active day(s)', GRAY)}")
    print(f"  {c('-' * 52, GRAY)}")

    # Day rows
    for d, v in sorted(days.items()):
        is_today = (d == date.today())
        day_str   = d.strftime("%a %d %b")
        marker    = c("▶", CYAN) if is_today else " "
        if v == 0:
            print(f"  {marker} {c(day_str, GRAY)}   {c('—', GRAY)}")
        else:
            pct = v / total * 100 if total else 0
            print(f"  {marker} {c(day_str, WHITE)}   "
                  f"{c(fmt_value(v).rjust(9), BOLD, GREEN)}  "
                  f"{bar(v, max_val)}  {c(f'{pct:.0f}%', GRAY)}")

    print(f"  {c('-' * 52, GRAY)}")
    print(f"  {'Total':20}  {c(fmt_value(total).rjust(9), BOLD, WHITE)}")

    # Stats
    _print_stats(entries, flag, start, end)
    print()


def _print_stats(entries, flag, start, end):
    """Print extra statistics below the list."""
    days_with_data = {}
    for e in entries:
        ed = date.fromisoformat(e["date"])
        if start <= ed <= end:
            days_with_data[ed] = days_with_data.get(ed, 0.0) + e["value"]

    if not days_with_data:
        return

    values = list(days_with_data.values())
    avg = sum(values) / len(values)
    best_day = max(days_with_data, key=days_with_data.get)

    print(f"  {c('-' * 52, GRAY)}")
    print(f"  {c('Stats', BOLD, CYAN)}")
    print(f"  {'Avg / active day':30}  {c(fmt_value(avg), YELLOW)}")
    print(f"  {'Best day':30}  {c(best_day.strftime('%a %d %b'), YELLOW)}"
          f"  {c(fmt_value(days_with_data[best_day]), BOLD, YELLOW)}")

    # week-over-week when viewing multi-week spans
    if flag in ("m", "y", "a"):
        today = date.today()
        prev_w_start = today - timedelta(days=today.weekday() + 7)
        prev_w_end   = prev_w_start + timedelta(days=6)
        curr_w_start = today - timedelta(days=today.weekday())

        def week_total(ws, we):
            return sum(v for d, v in days_with_data.items() if ws <= d <= we)

        prev_total = week_total(prev_w_start, prev_w_end)
        curr_total = week_total(curr_w_start, today)

        if prev_total > 0:
            delta_pct = (curr_total - prev_total) / prev_total * 100
            arrow = c("▲", GREEN) if delta_pct >= 0 else c("▼", RED)
            print(f"  {'WoW (this week vs last)':30}  {arrow} {c(f'{abs(delta_pct):.1f}%', BOLD)}")

    # streak
    streak = _streak(days_with_data)
    if streak > 1:
        print(f"  {'Current streak':30}  {c(f'{streak} days (:', BOLD, YELLOW)}")


def _streak(days_with_data: dict) -> int:
    if not days_with_data:
        return 0
    today = date.today()
    streak = 0
    d = today
    while d in days_with_data and days_with_data[d] > 0:
        streak += 1
        d -= timedelta(days=1)
    return streak


def cmd_dlist(args):
    """road dlist [-d|-w|-m|-y|-a] — raw entry list for administration"""
    flag, ref_date = parse_period_args(args, default="w")
    data = load_data()
    entries = data["entries"]

    if not entries:
        print("No entries.")
        return

    all_dates = [date.fromisoformat(e["date"]) for e in entries]
    first_date = min(all_dates)

    if flag == "a":
        start, end = first_date, date.today()
    else:
        start, end = date_range_for_flag(flag, ref_date)

    filtered = [e for e in entries if start <= date.fromisoformat(e["date"]) <= end]
    filtered.sort(key=lambda e: (e["date"], e["time"]))

    if not filtered:
        print(f"No entries in that period.")
        return

    # header
    print(f"\n  {c('ID', BOLD):>6}  {c('Timestamp', BOLD):<22}  {c('Value', BOLD):>10}")
    print(f"  {c('-'*6, GRAY)}  {c('-'*20, GRAY)}  {c('-'*10, GRAY)}")
    for e in filtered:
        eid_str = f"#{e['id']}"
        print(f"  {c(eid_str, CYAN):>6}  {c(e['ts'], GRAY):<22}  "
              f"{c(fmt_value(e['value']), WHITE):>10}")
    print(f"\n  {len(filtered)} entr{'y' if len(filtered)==1 else 'ies'}\n")


def cmd_rm(args):
    """road rm <id>"""
    if not args:
        die("Usage: road rm <id>")
    try:
        target_id = int(args[0])
    except ValueError:
        die(f"'{args[0]}' is not a valid id integer.")

    data = load_data()
    before = len(data["entries"])
    data["entries"] = [e for e in data["entries"] if e["id"] != target_id]

    if len(data["entries"]) == before:
        die(f"No entry with id #{target_id} found.")

    save_data(data)
    print(f"\n  {c(' REMOVED ', BOLD, RED)}  entry {c(f'#{target_id}', BOLD)}\n")


def cmd_edit(args):
    """road edit <id> <new_value> — correct a logged value"""
    if len(args) < 2:
        die("Usage: road edit <id> <new_value>")
    try:
        target_id = int(args[0])
        new_value = float(args[1])
    except ValueError:
        die("road edit <id> <new_value>  — id must be int, value must be number")

    data = load_data()
    for e in data["entries"]:
        if e["id"] == target_id:
            old = e["value"]
            e["value"] = new_value
            save_data(data)
            print(f"\n  {c(' EDITED ', BOLD, YELLOW)}  #{target_id}  "
                  f"{c(fmt_value(old), GRAY)} → {c(fmt_value(new_value), BOLD, GREEN)}\n")
            return
    die(f"No entry with id #{target_id}.")


def cmd_stats(args):
    """road stats — high-level summary across all time"""
    data = load_data()
    entries = data["entries"]
    if not entries:
        print(c("\n  No data yet.\n", GRAY))
        return

    days_map: dict[date, float] = {}
    for e in entries:
        ed = date.fromisoformat(e["date"])
        days_map[ed] = days_map.get(ed, 0.0) + e["value"]

    total = sum(days_map.values())
    avg   = total / len(days_map)
    best_day = max(days_map, key=days_map.get)
    streak   = _streak(days_map)
    first    = min(days_map)

    print()
    print(f"  {c('● All-time stats', BOLD, WHITE)}")
    print(f"  {c('-'*40, GRAY)}")
    print(f"  {'Tracking since':28}  {c(first.strftime('%d %b %Y'), CYAN)}")
    print(f"  {'Total entries':28}  {c(len(entries), WHITE)}")
    print(f"  {'Active days':28}  {c(len(days_map), WHITE)}")
    print(f"  {'Total':28}  {c(fmt_value(total), BOLD, GREEN)}")
    print(f"  {'Avg / active day':28}  {c(fmt_value(avg), YELLOW)}")
    print(f"  {'Best day':28}  {c(best_day.strftime('%a %d %b %Y'), YELLOW)}  {c(fmt_value(days_map[best_day]), BOLD, YELLOW)}")
    if streak > 0:
        print(f"  {'Current streak':28}  {c(f'{streak} day(s) (:', BOLD, YELLOW)}")
    print()


def cmd_help(_args):
    print(f"""
  {c('road', BOLD, CYAN)} — personal goal progress tracker

  {c('Logging', BOLD)}
    road {c('<number>', GREEN)}              log a value for today
    road {c('<number>', GREEN)} -d {c('<date>', YELLOW)}    backlog to a specific date

  {c('Viewing', BOLD)}
    road list  {c('[-d|-w|-m|-y|-a]', GRAY)}   cumulative per day  (default: -w)
    road dlist {c('[-d|-w|-m|-y|-a]', GRAY)}   every raw entry
    road stats                    all-time summary

  {c('Management', BOLD)}
    road rm {c('<id>', YELLOW)}               delete entry by id
    road edit {c('<id> <value>', YELLOW)}      correct a logged value

  {c('Date formats', BOLD)}
    17.5.26 · 17.05.2026 · 17.5 · 2026-05-17 · today · yesterday

  {c('Data file', BOLD)}
    {DATA_FILE}
""")

# utils

def fmt_value(v: float) -> str:
    """Show as int when whole, float otherwise."""
    return str(int(v)) if v == int(v) else f"{v:g}"


def parse_period_args(args, default="w") -> tuple[str, date]:
    """Parse optional -d/-w/-m/-y/-a and optional --date <date>."""
    flag = default
    ref  = date.today()
    valid_flags = {"d", "w", "m", "y", "a"}

    i = 0
    while i < len(args):
        a = args[i]
        if a.startswith("-") and a[1:] in valid_flags:
            flag = a[1:]
            i += 1
        elif a == "--date" and i + 1 < len(args):
            ref = parse_date(args[i + 1])
            i += 2
        else:
            die(f"Unknown argument: {a}")
    return flag, ref


def die(msg: str):
    print(f"\n  {c('Error:', BOLD, RED)} {msg}\n", file=sys.stderr)
    sys.exit(1)

# main

COMMANDS = {
    "list":  cmd_list,
    "dlist": cmd_dlist,
    "rm":    cmd_rm,
    "edit":  cmd_edit,
    "stats": cmd_stats,
    "help":  cmd_help,
    "--help": cmd_help,
    "-h":    cmd_help,
}

def main():
    args = sys.argv[1:]

    if not args:
        cmd_help([])
        return

    first = args[0]

    if first in COMMANDS:
        COMMANDS[first](args[1:])
        return

    # try to parse first arg as a number → log command
    try:
        float(first)
        cmd_log(args)
    except ValueError:
        die(f"Unknown command '{first}'. Run 'road help' for usage.")

if __name__ == "__main__":
    main()
