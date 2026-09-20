# Electronic Checklist

A simple desktop app that recreates aircraft electronic checklists (ECL). Checklists
are grouped by aircraft, and each checklist holds an ordered list of items you check
off as you work through it.

## Features

- **Aircraft-grouped checklists** — add as many aircraft as you like, each with its
  own set of checklists (Before Start, Taxi, Before Takeoff, etc.)
- **Menu-driven navigation** — pick an aircraft, tap a checklist to open it, and it
  automatically returns to the checklist menu once every item is checked
- **Text + result items** — items can have a challenge and a response
  (`Packs.......................................Auto`), styled with a dot leader
  like a real ECL
- **Separators** — insert a solid divider between items to mark a pause point
  (Airbus-style)
- **Completion tracking** — completed checklists show a checkmark in the aircraft
  menu until reopened
- **Export / import** — export a checklist (or every checklist for an aircraft) to
  a `.json` file, and import checklists from a file into any aircraft

## Requirements

- Python 3.10+ (uses only the standard library — `tkinter`, no extra packages)

## Running it

```bash
python app.py
```

On Windows, double-click `Run Checklist.bat` to launch without a terminal window.

## Building a standalone .exe

Requires [PyInstaller](https://pyinstaller.org/):

```bash
pip install pyinstaller
pyinstaller --onefile --windowed --name "Electronic Checklist" app.py
```

The exe is written to `dist/Electronic Checklist.exe`. It's fully standalone — no
Python install needed on the target machine — and stores `data.json` next to
wherever the exe itself lives, so it can be copied anywhere. Build output
(`build/`, `dist/`, the generated `.spec` file) isn't tracked in git; rebuild from
source whenever you need a fresh exe.

## Data storage

Checklist data is stored in `data.json` next to the app (not tracked in git — a
sample Cessna 172 checklist is created automatically on first run). Back it up or
share it using the in-app **Export** / **Import** buttons under **Edit Checklists**.
