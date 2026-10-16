# league-ninja-scraper

**Find out when and where your rec-league games are without digging through the league website.**

league-ninja-scraper reads your club's [league.ninja](https://league.ninja) schedule
(Flannagan's and similar clubs) and gives you your team's games: date, time,
opponent and court. It saves them as a simple JSON file, and can also export a
calendar file you can drop into Google Calendar, Apple Calendar or Outlook.

It's free to run, takes about 3 seconds, and needs **no API key, no browser and no
AI**. Just Python.

## Who it's for

- Players and captains who want their game times without checking the site every week.
- Anyone on several teams or levels (e.g. Beer A *and* Beer B) who wants them all in one place.
- People who'd like their games in their calendar, or sent to them by a bot.

## Quick start

You'll need **Python 3.11+**.

```bash
# 1. Install
git clone https://github.com/rbaas293/league-ninja-scraper.git
cd league-ninja-scraper
python3 -m venv .venv && source .venv/bin/activate
pip install ./python

# 2. Make your own config (it stays on your machine; never committed)
cp config.example.yaml config.yaml
#    edit config.yaml: your club's siteUrl, your captain or team name, your levels

# 3. Run it
league-ninja-scraper --config config.yaml
#    prints your games and writes games.json

# 4. Put your games on your calendar
league-ninja-scraper --config config.yaml --ics games.ics
#    then import games.ics into Google / Apple / Outlook
```

A minimal `config.yaml`:

```yaml
siteUrl: "https://example.league.ninja"
captainName: ["J. Pike"]        # as shown on the standings page, or use teamName
levels: ["Beer A", "Beer B"]
```

Re-import `games.ics` any time. Rescheduled games update in place instead of
showing up twice. See [docs/CALENDAR.md](docs/CALENDAR.md) for step-by-step import
instructions.

## Volleyball Grok Bot

Don't want to run it yourself? Use the ready-made
**[Volleyball Grok Bot template](https://x.ai/bot/Ij_P-Hc7m6AkvPguvJUj1)**.

- **Every morning** (8:00 AM in your time zone by default) it checks the schedule.
- **On game days** it messages you with team, opponent, time and court, for example:
  > 🏐 Tonight: **Net Gains vs Dig Deep**, 7:15 PM ET, Outdoors - Court H
- **Other days it stays quiet.** It only speaks up if something's wrong, like the
  season not being posted yet or the site being down.
- **Setup is a chat.** The first time you open it, it asks for your club, teams and
  time zone. It saves your `config.yaml` on the bot's own machine (never committed)
  and runs a test check so you can confirm it found you. Change anything later by
  just telling it, e.g. *"add my Tuesday team"* or *"check at 7 instead"*. It can also
  produce a calendar file on request.

## FAQ & troubleshooting

**Do I need an API key or an AI account?**
No. The default mode reads the club's public schedule data directly. An optional
AI/browser fallback exists (see [docs/LLM_MODE.md](docs/LLM_MODE.md)), and it only
asks for a key if you turn it on and it actually runs.

**"Could not find config.yaml"**
Run `cp config.example.yaml config.yaml`, or point at your file with
`--config PATH` or `LEAGUE_NINJA_CONFIG=PATH`. Check it with
`league-ninja-scraper --config config.yaml --check-config`.

**It can't find my team.**
`captainName` must match the standings page exactly, apart from punctuation and case
(`J Pike` = `J. Pike`, but `Pike` alone won't match). Or use the exact `teamName`.
Make sure `levels` matches your division names (e.g. `Beer A`).

**It says the schedule isn't posted yet.**
The new season probably hasn't been published. The scraper skips seasons with no
posted data. Try again later, or force a season with `season:` in your config.

**The game times look off.**
Times are shown in US Eastern (`America/New_York`), the league's local time. The
calendar file carries the time zone, so your calendar app converts it to yours.

**I used the old name `stagehand-volleyball`.**
The project was renamed. The old command and the `STAGEHAND_VOLLEYBALL_CONFIG` variable
still work, the old GitHub URL redirects, and calendar event IDs are unchanged. Use the
new name going forward; `LEAGUE_NINJA_CONFIG` wins if both variables are set.
Reinstall the package under the new name.

## Docs

- [Configuration](docs/CONFIGURATION.md): every config key, environment variables, config lookup order, `.env` files
- [Calendar export](docs/CALENDAR.md): `.ics` options, importing, and using it from an AI agent or workflow
- [LLM mode](docs/LLM_MODE.md): the optional Stagehand + Grok fallback, API keys, token usage comparison
- [Development](docs/DEVELOPMENT.md): repo layout, tests, CI, wheels and shiv binaries, HTTP robustness internals

## License

Private / personal use unless otherwise noted.
