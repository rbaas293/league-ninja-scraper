"""RFC 5545 .ics export."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import ics_export
from ics_export import build_ics, escape_text, fold_line, game_start

SAMPLE = {
    "scrapedAt": "2026-10-16T14:13:24.701Z",
    "games": [
        {
            "date": "Fri, Oct 16", "time": "7:15 pm", "week": "Week 6 - Oct 16",
            "team": "Spike Lee", "opponent": "Sand Storm", "location": "Outdoors - Court H",
            "status": "scheduled", "divisionName": "Friday Beer (B)",
            "leagueName": "Friday Coed; Beer B, Evening", "url": "https://example.league.ninja/leagues/division/x",
        },
        {
            "date": "Sun, Oct 18", "time": "6:00 pm", "startsAt": "2026-10-18T22:00:00Z",
            "week": "TOURNAMENT Oct 18", "team": "Net Gains", "opponent": "Dig Deep",
            "location": "Outdoors - Court E", "status": "scheduled",
        },
        {"date": "Sun, Jan 3", "time": "1:00 pm", "team": "Net Gains", "opponent": "Winter Team",
         "week": "Week 1", "location": "Gym", "status": "cancelled"},
        {"date": "TBD", "time": "", "team": "Net Gains", "opponent": "?", "status": "scheduled"},
    ],
}


def _unfold(text: str) -> str:
    return text.replace("\r\n ", "")


def test_structure_and_crlf():
    text, n, skipped = build_ics(SAMPLE)
    assert (n, skipped) == (3, 1)
    assert text.startswith("BEGIN:VCALENDAR\r\nVERSION:2.0\r\nPRODID:")
    assert text.endswith("END:VCALENDAR\r\n")
    assert "\n" not in text.replace("\r\n", "")
    assert text.count("BEGIN:VEVENT") == 3 == text.count("END:VEVENT")
    assert "BEGIN:VTIMEZONE\r\nTZID:America/New_York" in text
    assert all(len(line.encode()) <= 75 for line in text.split("\r\n"))
    assert "DTSTAMP:20261016T141324Z" in text


def test_events_times_summary_location():
    text = _unfold(build_ics(SAMPLE)[0])
    assert "DTSTART;TZID=America/New_York:20261016T191500" in text
    assert "DTEND;TZID=America/New_York:20261016T201500" in text
    assert "SUMMARY:Spike Lee vs Sand Storm" in text
    assert "LOCATION:Outdoors - Court H" in text
    # startsAt (UTC) wins and converts to local EDT.
    assert "DTSTART;TZID=America/New_York:20261018T180000" in text
    # January date scraped in October → next year; cancelled kept as CANCELLED.
    assert "DTSTART;TZID=America/New_York:20270103T130000" in text
    assert "STATUS:CANCELLED" in text
    assert "League: Friday Coed\\; Beer B\\, Evening" in text


def test_uids_stable_and_independent_of_time():
    a = build_ics(SAMPLE)[0]
    moved = json.loads(json.dumps(SAMPLE))
    moved["games"][0]["time"] = "8:15 pm"
    moved["scrapedAt"] = "2026-10-17T00:00:00Z"
    b = build_ics(moved)[0]
    uids = lambda t: [line for line in _unfold(t).split("\r\n") if line.startswith("UID:")]  # noqa: E731
    assert uids(a) == uids(b)
    assert len(set(uids(a))) == 3


def test_duplicate_games_get_distinct_uids():
    g = SAMPLE["games"][0]
    text = _unfold(build_ics({"scrapedAt": SAMPLE["scrapedAt"], "games": [g, dict(g, time="8:15 pm")]})[0])
    uids = [line for line in text.split("\r\n") if line.startswith("UID:")]
    assert len(set(uids)) == 2


def test_escape_and_fold_and_injection():
    assert escape_text("a,b;c\\d\ne") == "a\\,b\\;c\\\\d\\ne"
    folded = fold_line("X:" + "é" * 100)
    assert all(len(part.encode()) <= 75 for part in folded.split("\r\n"))
    evil = {"scrapedAt": SAMPLE["scrapedAt"], "games": [dict(
        SAMPLE["games"][0], opponent="Bad\r\nBEGIN:VEVENT", url="https://x\r\nATTACH:evil")]}
    lines = _unfold(build_ics(evil)[0]).split("\r\n")
    assert lines.count("BEGIN:VEVENT") == 1
    assert not any(line.startswith("ATTACH") for line in lines)


def test_game_start_parsing():
    assert game_start({"date": "Sun, Aug 30", "time": "5:30 pm"}).hour == 17
    assert game_start({"date": "Tue, Oct 20", "time": "12:00 am"}).hour == 0
    assert game_start({"date": "Tue, Oct 20", "time": "TBD"}) is None
    assert ics_export.TZID == "America/New_York"


def test_cli_ics_from_games_json(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    import main

    src = tmp_path / "games.json"
    src.write_text(json.dumps(SAMPLE), encoding="utf-8")
    out = tmp_path / "games.ics"
    main.main(["--ics-from", str(src), "--ics", str(out), "--ics-duration", "90"])
    text = _unfold(out.read_text(encoding="utf-8"))
    assert "DTEND;TZID=America/New_York:20261016T204500" in text


def test_cli_ics_from_requires_ics(capsys):
    import main

    with pytest.raises(SystemExit):
        main.main(["--ics-from", "games.json"])


def test_cli_ics_refuses_symlink(tmp_path: Path):
    import main

    src = tmp_path / "games.json"
    src.write_text(json.dumps(SAMPLE), encoding="utf-8")
    real = tmp_path / "real.txt"
    real.write_text("keep\n", encoding="utf-8")
    link = tmp_path / "games.ics"
    link.symlink_to(real)
    with pytest.raises(SystemExit):
        main.main(["--ics-from", str(src), "--ics", str(link)])
    assert real.read_text(encoding="utf-8") == "keep\n"
