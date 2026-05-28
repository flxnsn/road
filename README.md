# road

A small cli tool to track progress, cause my pc is always on anyway.
Logs numeric values without specified units to a local JSON file with no dependencies beyond Python 3.

---

## Setup

**1. Place the script**
```bash
mkdir -p ~/.local/bin
cp road.py ~/.local/bin/road
chmod +x ~/.local/bin/road
```

**2. Make sure `~/.local/bin` is in your PATH**

First check if it already is:
```bash
echo $PATH
```

If you don't see `/home/yourusername/.local/bin` in the output, add this line to the bottom of your `~/.bashrc`:
```bash
export PATH="$HOME/.local/bin:$PATH"
```

Then reload it:
```bash
source ~/.bashrc
```

**3. Done.** Type `road help` to verify it works.

---

## Data

Entries are stored at:
```
~/.local/share/road/data.json
```

The file and its parent directory are created automatically on first use. To use a different location, set the `ROAD_DATA` environment variable.

---

## Commands

### Logging
```bash
road 20                  # log 20 for today
road 20 -d 17.5.26       # backlog to a specific date
```

Accepted date formats: `17.5` · `17.5.26` · `17.05.2026` · `2026-05-17` · `today` · `yesterday`  
When backdating, the time is set to 00:00:00. Omitting the year assumes the current year.

### Viewing
```bash
road list                # this week (default)
road list -d             # today
road list -w             # current week
road list -m             # current month
road list -y             # current year
road list -a             # all time

road dlist               # same flags, but shows every raw entry with ID and timestamp
road stats               # all-time summary
```

`road list` shows cumulative daily totals, a progress bar, percentage share, and stats like average, best day, week-over-week change, and current streak.

### Management
```bash
road rm 3                # delete entry by ID
road edit 3 25           # correct the value of entry #3
```

IDs are permanent and never reassigned. Removing entry #2 from a set of 0–4 means the next new entry gets #5, leaving a gap at #2.

---

## Help
```bash
road help
```
