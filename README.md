# stagehand-volleyball

Python scraper for volleyball schedules on [league.ninja](https://league.ninja) (Flannagan's and similar clubs).

Example config searches captains **J. Pike** / **M. Alvarez** across **Beer A** and **Beer B** for the current season (placeholder names — put your own in your local `config.yaml`).

## Lean by default — no API key, no browser, no Stagehand

**Lean mode is the default and needs nothing but Python.** It reads the club's
public league.ninja JSON API over plain HTTP: **no API key, no LLM calls, no
Chrome, and the Stagehand package does not even need to be installed.** A full
week across Beer A + Beer B takes ~3 seconds.

**Stagehand + xAI Grok (`llm` mode) is an optional fallback.** It is only
imported, and `XAI_API_KEY` is only checked, at the moment llm mode actually
runs. If you never use it you never need a key. If you do use it without the
extra installed (or without a key) you get a one-line error telling you exactly
what to install / set — lean runs are never affected.

| `mode` | What it does | Needs |
|---|---|---|
| **`lean`** (default) | Club public LMS API for seasons, division nav, standings, and schedules. | Python only |
| **`llm`** (optional) | [Stagehand v4](https://docs.stagehand.dev/v4/first-steps/quickstart) + xAI Grok BYO callback: browser `extract()` on standings and each schedule week. | `pip install ".[llm]"`, Chrome (or Browserbase), `XAI_API_KEY` |

Set in `config.yaml` (`mode: lean|llm`) or override with `SCRAPE_MODE`.

**Automatic fallback (opt-in):** set `llmFallback: true` in `config.yaml` (or
`SCRAPE_LLM_FALLBACK=1`) and, if a lean run fails on a site/API error (outage,
circuit breaker, standings probe error), the scraper retries once with llm mode.
Config/team-resolution errors never trigger it. The key and the `[llm]` extra are
only required if the fallback actually fires.

Multi-division: `levels: ["Beer A", "Beer B"]` plus `siteUrl`. Auto-pick prefers an in-range season with **posted** data for those levels (skips seasons that exist but are not posted yet — no matching divisions / no teams). Output includes `seasonStatus`. Empty team schedules are reported as “schedule not posted yet”. Set `season` to force a name or uid. Single-division `leagueUrl` still works when `levels` is empty.

## Requirements

- **Python 3.11+**
- Lean (default): nothing else — no key, no Chrome, no Stagehand.
- llm mode / fallback only: `pip install ".[llm]"` (Stagehand + openai client), **Google Chrome** for a local browser, and `XAI_API_KEY` (or `BROWSERBASE_API_KEY`).

## Layout

| Path | Role |
|---|---|
| `config.example.yaml` | Public template at **repo root** (copy → local `config.yaml`) |
| `config.yaml` | Local only (gitignored) |
| `python/main.py` | CLI entrypoint |
| `python/lean_api.py` | Pub-api client (lean mode) |
| `python/lean_http.py` | Robust lean HTTP (retries, circuit breaker, concurrency) |
| `python/token_usage.py` | xAI token / cost accumulator |
| `python/ics_export.py` | RFC 5545 `.ics` calendar export |
| `python/games.json` | Output (gitignored) |
| `.env` (root or `python/`) | Secrets (gitignored); root `.env` is the fallback |

The scraper code stays under **`python/`** (not moved to repo root) so existing packaging/CI that targets `python/` (see PR #3) keeps working without path rewrites. Root owns config and docs only.

## Config file location

Env files are **not** auto-loaded from the cwd for installed binaries. Use
`--env-file PATH`, or rely on `python/.env` / repo-root `.env` in a source
checkout. Only known keys are imported from those files. Set `httpTrustEnv: true`
in config.yaml only if you intentionally want the xAI client to honor proxy env
vars.



The scraper resolves `config.yaml` in this order:

1. `--config PATH` on the CLI
2. `$STAGEHAND_VOLLEYBALL_CONFIG`
3. `./config.yaml` in the current working directory
4. Repo-root `config.yaml` (and optional `python/config.yaml`) **only when running from a source checkout**

Installed wheels / shiv binaries do **not** look next to the package in site-packages.
If nothing is found, the error lists every path tried and reminds you to
`cp config.example.yaml config.yaml`. `.env` is loaded from the cwd as well
(shell exports still win). Use `--check-config` to validate a config without scraping.

## Config

`config.yaml` is **local only** (gitignored). Start from the public template:

```bash
cp config.example.yaml config.yaml
# edit captainName / levels / siteUrl / mode / …
```

If `config.yaml` is missing, the scraper exits with an error that includes that `cp` hint — it does **not** fall back to the example file.


| Field | Required | Purpose |
|---|---|---|
| `captainName` | one of captain/team | String or YAML list. Exact after normalizing punctuation/case (`"J Pike"` ≡ `"J. Pike"`; no substrings). |
| `teamName` | one of captain/team | Exact match; used only when `captainName` is empty. |
| `mode` | no | `lean` (default) or `llm`. |
| `levels` | no | Name substrings for multi-div discovery (e.g. `Beer A`, `Beer B`). |
| `siteUrl` | with levels | Club origin, e.g. `https://example.league.ninja`. |
| `apiBaseUrl` | no | Override pub API base (inferred for known clubs). |
| `season` | no | Optional season **name or uid** override. When empty, auto-pick prefers in-range seasons that have **posted** data for `levels` (skips “not posted yet”). |
| `http` | no | Lean HTTP knobs: timeouts, retries, Retry-After, circuit breaker, `concurrency` (default 4). |
| `leagueUrl` | single-div | Division URL when `levels` is empty. |
| `day` / `league` | no | Notes for single-div; multi-div uses API fields. |
| `model` | no | xAI Grok id (default `grok-4-fast-reasoning`). |
| `schedulePathSuffix` | no | Default `"/schedule"` (llm mode). |
| `llmFallback` | no | Default `false`. Retry with llm mode if lean fails on a site/API error. |

## Environment

| Variable | Required | Purpose |
|---|---|---|
| `XAI_API_KEY` | llm mode / fallback only | xAI key (`https://api.x.ai/v1`). Never needed for lean. |
| `BROWSERBASE_API_KEY` | optional | Cloud browser (+ Model Gateway if no xAI key). |
| `STAGEHAND_MODEL` | optional | Overrides `config.model`. |
| `SCRAPE_MODE` | optional | Overrides `config.mode`. |
| `SCRAPE_LLM_FALLBACK` | optional | `1`/`0` overrides `config.llmFallback`. |
| `SCRAPE_LLM_PREFILTER` | optional | Multi-div llm: default `1` HTTP-prefilters standings; `0` disables. |
| `HEADLESS` | optional | `false` to show Chrome (llm). |

`.env` load order (first wins): **shell exports → `python/.env` → repo-root `.env`**.

Lean mode does not need `XAI_API_KEY`.

## Run

```bash
cd python
python3 -m venv .venv && source .venv/bin/activate
pip install .                           # core = lean only (or: pip install -r requirements.txt)
python main.py                          # lean by default — no key needed
python main.py --ics games.ics          # …and also write a calendar file

# Optional llm mode / fallback:
pip install ".[llm]"                    # or: pip install -r requirements-llm.txt
SCRAPE_MODE=llm XAI_API_KEY=… python main.py
```

Stdout is JSON; also writes `python/games.json`. Null keys are omitted; `scrapedAt` is UTC with millisecond precision (`YYYY-MM-DDTHH:MM:SS.mmmZ`). Each run logs LLM usage (calls, tokens, estimated USD from published xAI rates).

## Calendar export (.ics)

Write an [RFC 5545](https://www.rfc-editor.org/rfc/rfc5545) iCalendar file that
imports into Google Calendar, Apple Calendar, and Outlook:

```bash
stagehand-volleyball --ics games.ics                       # scrape + games.json + games.ics
stagehand-volleyball --ics-from games.json --ics games.ics # convert only (no network)
stagehand-volleyball --ics games.ics --ics-duration 90     # event length (default 60 min)
```

Each game becomes one event:

- **SUMMARY** `Your Team vs Opponent`, **LOCATION** the court (e.g. `Outdoors - Court H`)
- **DTSTART/DTEND** in `America/New_York` (embedded `VTIMEZONE`, correct across DST)
- **DESCRIPTION** league, division, week, status/result, schedule link
- **UID** stable across re-scrapes (from division + week + teams, not the time),
  so re-importing a newer file **updates** a rescheduled game instead of duplicating it
- Cancelled games are kept with `STATUS:CANCELLED`; games without a posted time (TBD) are skipped

Import: **Google** → Settings → Import & export → Import (pick a calendar);
**Apple** → File → Import (or double-click the file); **Outlook** → Add calendar →
Upload from file. For an auto-refreshing calendar, host the `.ics` somewhere private
and subscribe to its URL (Google: “From URL”; Apple: File → New Calendar Subscription),
re-running the scraper on a schedule (cron / CI).

### Using it from an AI agent / workflow

Both outputs are designed for agents:

- **`games.json`** — structured, one object per game: `team`, `opponent`, `date`,
  `time` (display, Eastern), `startsAt` (UTC ISO-8601, lean mode), `location`,
  `status`, `result`, `week`, `leagueName`, `divisionName`, `url`. An agent with a
  calendar tool (Google Calendar API, MCP calendar server, etc.) can loop over
  `games`, skip `status == "cancelled"`, and create/update an event per game with
  `summary = f"{team} vs {opponent}"`, `location`, and `start = startsAt`. Reuse the
  `.ics` UID (or `ics_export.game_uid(game)`) as the event's external id so repeat
  runs update rather than duplicate.
- **`games.ics`** — for agents/tools that can only import files, hand them the
  `.ics` directly; it is plain text and safe to attach to an email or upload.

Example agent prompt: *“Run `stagehand-volleyball --ics games.ics`, then add every
non-cancelled game in `games.json` to my calendar (title “team vs opponent”, location
= court, 1 hour), updating events that already exist.”*

```python
import json
from ics_export import build_ics, game_start, game_uid

data = json.load(open("games.json"))
for g in data["games"]:
    print(game_uid(g), game_start(g, None), g["team"], "vs", g["opponent"], g["location"])
open("games.ics", "w", newline="").write(build_ics(data)[0])
```

## Team resolution

Prefer `captainName` (exact after normalizing punctuation/case); else exact `teamName`. Multi-div: a miss in one division is OK — failure only if nothing matches across all scanned divisions. Resolve errors name the season scanned and hint at the `season` config override.

## License

Private / personal use unless otherwise noted.
