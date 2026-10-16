"""
RFC 5545 iCalendar (.ics) export for games.json.

Pure stdlib, no network, no LLM. Usable as a library or via the CLI:

    stagehand-volleyball --ics games.ics              # scrape, then also write .ics
    stagehand-volleyball --ics-from games.json --ics games.ics   # convert only

Design notes:
- Times are emitted as local America/New_York with TZID and an embedded
  VTIMEZONE, so Google / Apple / Outlook show the right wall-clock time.
- UIDs are stable across re-scrapes: derived from division + week + team +
  opponent (NOT the start time), so a rescheduled game updates the existing
  calendar entry on re-import instead of duplicating it.
- Cancelled games are kept with STATUS:CANCELLED so re-imports clear them.
"""

from __future__ import annotations

import hashlib
import re
from datetime import date, datetime, timedelta, timezone
from typing import Any
from zoneinfo import ZoneInfo

TZID = "America/New_York"
_TZ = ZoneInfo(TZID)
PRODID = "-//stagehand-volleyball//games ics export//EN"
DEFAULT_DURATION_MINUTES = 60

# Standard US Eastern definition (DST rules in force since 2007).
VTIMEZONE = (
    "BEGIN:VTIMEZONE",
    f"TZID:{TZID}",
    "X-LIC-LOCATION:America/New_York",
    "BEGIN:DAYLIGHT",
    "TZOFFSETFROM:-0500",
    "TZOFFSETTO:-0400",
    "TZNAME:EDT",
    "DTSTART:19700308T020000",
    "RRULE:FREQ=YEARLY;BYMONTH=3;BYDAY=2SU",
    "END:DAYLIGHT",
    "BEGIN:STANDARD",
    "TZOFFSETFROM:-0400",
    "TZOFFSETTO:-0500",
    "TZNAME:EST",
    "DTSTART:19701101T020000",
    "RRULE:FREQ=YEARLY;BYMONTH=11;BYDAY=1SU",
    "END:STANDARD",
    "END:VTIMEZONE",
)

_MONTHS = {m: i for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], 1
)}
_DATE_RE = re.compile(r"([A-Za-z]{3})[a-z]*\.?\s+(\d{1,2})(?:,?\s+(\d{4}))?")
_TIME_RE = re.compile(r"(\d{1,2})(?::(\d{2}))?\s*([ap])\.?m?\.?", re.IGNORECASE)


_DESC_FIELDS = (
    ("leagueName", "League"),
    ("divisionName", "Division"),
    ("week", "Week"),
    ("status", "Status"),
    ("result", "Result"),
    ("url", "Schedule"),
)


def _parse_utc(raw: Any) -> datetime | None:
    if not raw or not isinstance(raw, str):
        return None
    try:
        dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _infer_year(month: int, day: int, ref: date) -> int | None:
    """Pick the year (ref-1..ref+1) whose date is closest to the reference date."""
    best: tuple[int, int] | None = None
    for year in (ref.year - 1, ref.year, ref.year + 1):
        try:
            cand = date(year, month, day)
        except ValueError:
            continue
        dist = abs((cand - ref).days)
        if best is None or dist < best[0]:
            best = (dist, year)
    return best[1] if best else None


def game_start(game: dict[str, Any], scraped_at: datetime | None = None) -> datetime | None:
    """Return an aware America/New_York start datetime, or None if unknown/TBD."""
    utc = _parse_utc(game.get("startsAt"))
    if utc is not None:
        return utc.astimezone(_TZ)
    dm = _DATE_RE.search(str(game.get("date") or ""))
    tm = _TIME_RE.search(str(game.get("time") or ""))
    if not dm or not tm:
        return None
    month = _MONTHS.get(dm.group(1).lower())
    if month is None:
        return None
    day = int(dm.group(2))
    ref = (scraped_at or datetime.now(timezone.utc)).astimezone(_TZ).date()
    year = int(dm.group(3)) if dm.group(3) else _infer_year(month, day, ref)
    hour = int(tm.group(1)) % 12 + (12 if tm.group(3).lower() == "p" else 0)
    minute = int(tm.group(2) or 0)
    try:
        return datetime(year, month, day, hour, minute, tzinfo=_TZ)
    except (TypeError, ValueError):
        return None


def escape_text(value: Any) -> str:
    """RFC 5545 §3.3.11 TEXT escaping."""
    text = str(value or "")
    text = text.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,")
    text = text.replace("\r\n", "\\n").replace("\n", "\\n").replace("\r", "\\n")
    return text


def fold_line(line: str) -> str:
    """Fold to <=75 octets per line (RFC 5545 §3.1), never splitting a UTF-8 char."""
    out: list[str] = []
    current = ""
    limit = 75
    for ch in line:
        if len((current + ch).encode("utf-8")) > limit:
            out.append(current)
            current = " " + ch
            limit = 75
        else:
            current += ch
    out.append(current)
    return "\r\n".join(out)


def game_uid(game: dict[str, Any], occurrence: int = 0) -> str:
    key = "|".join(
        str(game.get(k) or "").strip().lower()
        for k in ("url", "divisionName", "week", "team", "opponent")
    )
    if occurrence:
        key += f"|{occurrence}"
    digest = hashlib.sha1(key.encode("utf-8")).hexdigest()[:24]
    return f"{digest}@stagehand-volleyball"


def _fmt_local(dt: datetime) -> str:
    return dt.astimezone(_TZ).strftime("%Y%m%dT%H%M%S")


def _fmt_utc(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def build_ics(
    output: dict[str, Any],
    *,
    duration_minutes: int = DEFAULT_DURATION_MINUTES,
    calendar_name: str = "Volleyball games",
) -> tuple[str, int, int]:
    """
    Build an .ics document from a games.json dict.

    Returns (ics_text, n_events, n_skipped). Games with no parseable date/time
    (TBD) are skipped.
    """
    scraped_at = _parse_utc(output.get("scrapedAt")) or datetime.now(timezone.utc)
    dtstamp = _fmt_utc(scraped_at)
    lines: list[str] = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        f"PRODID:{PRODID}",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        f"X-WR-CALNAME:{escape_text(calendar_name)}",
        f"X-WR-TIMEZONE:{TZID}",
        *VTIMEZONE,
    ]
    seen: dict[str, int] = {}
    n_events = n_skipped = 0
    for game in output.get("games") or []:
        start = game_start(game, scraped_at)
        if start is None:
            n_skipped += 1
            continue
        base_uid = game_uid(game)
        occ = seen.get(base_uid, 0)
        seen[base_uid] = occ + 1
        uid = game_uid(game, occ)
        end = start + timedelta(minutes=duration_minutes)
        team = game.get("team") or "TBD"
        opponent = game.get("opponent") or "TBD"
        desc_parts = [
            f"{label}: {game[key]}"
            for key, label in _DESC_FIELDS
            if game.get(key)
        ]
        event = [
            "BEGIN:VEVENT",
            f"UID:{uid}",
            f"DTSTAMP:{dtstamp}",
            f"DTSTART;TZID={TZID}:{_fmt_local(start)}",
            f"DTEND;TZID={TZID}:{_fmt_local(end)}",
            f"SUMMARY:{escape_text(f'{team} vs {opponent}')}",
        ]
        if game.get("location"):
            event.append(f"LOCATION:{escape_text(game['location'])}")
        if desc_parts:
            event.append(f"DESCRIPTION:{escape_text(chr(10).join(desc_parts))}")
        if game.get("url"):
            url = re.sub(r"[\x00-\x20\x7f]", "", str(game["url"]))
            if url.startswith(("http://", "https://")):
                event.append(f"URL:{url}")
        status = str(game.get("status") or "").lower()
        event.append("STATUS:CANCELLED" if status == "cancelled" else "STATUS:CONFIRMED")
        event.append("TRANSP:OPAQUE")
        event.append("END:VEVENT")
        lines.extend(event)
        n_events += 1
    lines.append("END:VCALENDAR")
    text = "\r\n".join(fold_line(line) for line in lines) + "\r\n"
    return text, n_events, n_skipped
