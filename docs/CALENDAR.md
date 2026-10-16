# Calendar export (.ics)

[← Back to README](../README.md)

Write an [RFC 5545](https://www.rfc-editor.org/rfc/rfc5545) iCalendar file that
imports into Google Calendar, Apple Calendar, and Outlook:

```bash
league-ninja-scraper --ics games.ics                       # scrape + games.json + games.ics
league-ninja-scraper --ics-from games.json --ics games.ics # convert only (no network)
league-ninja-scraper --ics games.ics --ics-duration 90     # event length (default 60 min)
```

| Flag | Purpose |
|---|---|
| `--ics PATH` | Also write the games as an `.ics` file (atomic write; refuses symlinks). |
| `--ics-from GAMES_JSON` | Convert an existing `games.json` without scraping. Requires `--ics`. |
| `--ics-duration MINUTES` | Event length, 1–1440 (default 60). |

## What's in each event

- **SUMMARY** `Your Team vs Opponent`, **LOCATION** the court (e.g. `Outdoors - Court H`)
- **DTSTART/DTEND** in `America/New_York` (embedded `VTIMEZONE`, correct across DST)
- **DESCRIPTION** league, division, week, status/result, schedule link
- **UID** stable across re-scrapes (from division + week + teams, not the time),
  so re-importing a newer file **updates** a rescheduled game instead of duplicating it.
  The UID domain stays `@stagehand-volleyball` from before the rename, so older imports keep matching.
- Cancelled games are kept with `STATUS:CANCELLED`; games without a posted time (TBD) are skipped.

Lean-mode games carry a machine-readable `startsAt` (UTC). For games without it
(llm mode), the date and time text are parsed and the year is inferred as the one
closest to `scrapedAt`.

## Importing

- **Google Calendar** → Settings → Import & export → Import (pick a calendar)
- **Apple Calendar** → File → Import (or double-click the file)
- **Outlook** → Add calendar → Upload from file

For an auto-refreshing calendar, host the `.ics` somewhere private and subscribe to
its URL (Google: "From URL"; Apple: File → New Calendar Subscription), re-running the
scraper on a schedule (cron / CI).

## Using it from an AI agent / workflow

Both outputs are designed for agents:

- **`games.json`** is structured, one object per game: `team`, `opponent`, `date`,
  `time` (display, Eastern), `startsAt` (UTC ISO-8601, lean mode), `location`,
  `status`, `result`, `week`, `leagueName`, `divisionName`, `url`. An agent with a
  calendar tool (Google Calendar API, MCP calendar server, etc.) can loop over
  `games`, skip `status == "cancelled"`, and create or update an event per game with
  `summary = f"{team} vs {opponent}"`, `location`, and `start = startsAt`. Reuse the
  `.ics` UID (or `ics_export.game_uid(game)`) as the event's external id so repeat
  runs update rather than duplicate.
- **`games.ics`** is for agents and tools that can only import files. Hand them the
  `.ics` directly; it's plain text and safe to attach to an email or upload.

Example agent prompt: *"Run `league-ninja-scraper --ics games.ics`, then add every
non-cancelled game in `games.json` to my calendar (title "team vs opponent", location
= court, 1 hour), updating events that already exist."*

```python
import json
from ics_export import build_ics, game_start, game_uid

data = json.load(open("games.json"))
for g in data["games"]:
    print(game_uid(g), game_start(g, None), g["team"], "vs", g["opponent"], g["location"])
open("games.ics", "w", newline="").write(build_ics(data)[0])
```

The [Volleyball Grok Bot template](https://x.ai/bot/Ij_P-Hc7m6AkvPguvJUj1) is a
ready-made agent built this way.
