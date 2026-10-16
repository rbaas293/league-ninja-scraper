"""Lean mode must work with no XAI_API_KEY and without stagehand/openai installed."""

from __future__ import annotations

import os
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

PY_DIR = Path(__file__).resolve().parents[1]

# Runs in a fresh interpreter where importing stagehand / openai / httpx fails,
# exactly like a core-only install (no [llm] extra).
_BLOCKER = textwrap.dedent(
    """
    import importlib.abc, sys
    class _Block(importlib.abc.MetaPathFinder):
        def find_spec(self, name, path=None, target=None):
            if name.split(".")[0] in {"stagehand", "openai", "httpx"}:
                raise ImportError(f"No module named {name!r}", name=name)
            return None
    sys.meta_path.insert(0, _Block())
    for mod in list(sys.modules):
        if mod.split(".")[0] in {"stagehand", "openai", "httpx"}:
            del sys.modules[mod]
    """
)


def _run(script: str, tmp_path: Path) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if k not in ("XAI_API_KEY", "BROWSERBASE_API_KEY")}
    env.pop("SCRAPE_MODE", None)
    env.pop("SCRAPE_LLM_FALLBACK", None)
    env["PYTHONPATH"] = str(PY_DIR)
    return subprocess.run(
        [sys.executable, "-c", _BLOCKER + textwrap.dedent(script)],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )


_CFG = """
captainName: ["J. Pike"]
mode: "lean"
levels: ["Beer A"]
siteUrl: "https://example.league.ninja"
apiBaseUrl: "https://api.example.invalid/pub-api"
"""

_FAKE_LEAN = """
import asyncio, json, sys
import main
main.discover_target_divisions = lambda cfg: (
    "Fall 2026",
    [{"divisionUid": "11111111-1111-1111-1111-111111111111", "divisionName": "Sunday Beer (A)",
      "leagueName": "Beer A", "dayOfWeek": "Sunday"}],
    None,
)
main.get_standings = lambda api, uid: [{"teamName": "Block Party", "captainName": "J. Pike"}]
main.get_schedule_v2 = lambda api, uid: [{
    "matchStart": "2026-10-18T22:00:00Z",
    "homeTeam": {"name": "Block Party"}, "awayTeam": {"name": "Ace Ventura"},
    "location": {"locationGeneratedName": "Outdoors - Court E"},
    "incrementName": "Week", "incrementNumber": 3, "incrementDate": "2026-10-18T00:00:00Z",
    "result": 0,
}]
"""


def test_lean_scrape_without_key_or_stagehand(tmp_path: Path) -> None:
    (tmp_path / "config.yaml").write_text(_CFG, encoding="utf-8")
    proc = _run(
        _FAKE_LEAN
        + """
out = asyncio.run(main.scrape(cli_config="config.yaml"))
assert "stagehand" not in sys.modules and "openai" not in sys.modules
g = out["games"][0]
print(json.dumps({"team": g["team"], "opp": g["opponent"], "time": g["time"], "startsAt": g["startsAt"]}))
""",
        tmp_path,
    )
    assert proc.returncode == 0, proc.stderr
    assert '"team": "Block Party"' in proc.stdout
    assert '"startsAt": "2026-10-18T22:00:00Z"' in proc.stdout
    assert '"time": "6:00 pm"' in proc.stdout


def test_lean_cli_writes_ics_without_key_or_stagehand(tmp_path: Path) -> None:
    (tmp_path / "config.yaml").write_text(_CFG, encoding="utf-8")
    proc = _run(
        _FAKE_LEAN
        + """
main._RUNNING_FROM_SOURCE = False
main.main(["--config", "config.yaml", "--ics", "games.ics"])
""",
        tmp_path,
    )
    assert proc.returncode == 0, proc.stderr
    ics = (tmp_path / "games.ics").read_text(encoding="utf-8")
    assert "SUMMARY:Block Party vs Ace Ventura" in ics
    assert "DTSTART;TZID=America/New_York:20261018T180000" in ics
    assert (tmp_path / "games.json").exists()


def test_llm_mode_without_key_gives_clear_error(tmp_path: Path) -> None:
    (tmp_path / "config.yaml").write_text(_CFG.replace('"lean"', '"llm"'), encoding="utf-8")
    proc = _run(
        """
import main
main.discover_target_divisions = lambda cfg: ("S", [], None)
main.main(["--config", "config.yaml"])
""",
        tmp_path,
    )
    assert proc.returncode == 1
    assert "XAI_API_KEY is not set" in proc.stderr
    assert "Traceback" not in proc.stderr


def test_llm_mode_with_key_but_no_stagehand_gives_install_hint(tmp_path: Path) -> None:
    (tmp_path / "config.yaml").write_text(_CFG.replace('"lean"', '"llm"'), encoding="utf-8")
    proc = _run(
        """
import os
os.environ["XAI_API_KEY"] = "dummy-not-a-real-key"
import main
main.discover_target_divisions = lambda cfg: ("S", [], None)
main.main(["--config", "config.yaml"])
""",
        tmp_path,
    )
    assert proc.returncode == 1
    assert 'pip install "league-ninja-scraper[llm]"' in proc.stderr
    assert "dummy-not-a-real-key" not in proc.stderr + proc.stdout
    assert "Traceback" not in proc.stderr


@pytest.mark.parametrize("flag", ["0", None])
def test_lean_failure_without_fallback_does_not_touch_llm(tmp_path: Path, flag) -> None:
    (tmp_path / "config.yaml").write_text(_CFG, encoding="utf-8")
    pre = "import os\n" + (f"os.environ['SCRAPE_LLM_FALLBACK'] = {flag!r}\n" if flag else "")
    proc = _run(
        pre
        + """
import asyncio, sys
import main
from lean_api import LeanApiError
def boom(cfg):
    raise LeanApiError("site down")
main.scrape_lean = boom
try:
    asyncio.run(main.scrape(cli_config="config.yaml"))
except LeanApiError:
    print("raised-lean")
assert "stagehand" not in sys.modules
""",
        tmp_path,
    )
    assert proc.returncode == 0, proc.stderr
    assert "raised-lean" in proc.stdout


def test_lean_failure_with_fallback_runs_llm(tmp_path: Path) -> None:
    (tmp_path / "config.yaml").write_text(_CFG + "llmFallback: true\n", encoding="utf-8")
    proc = _run(
        """
import asyncio
import main
from lean_api import LeanApiError
def boom(cfg):
    raise LeanApiError("site down")
async def fake_llm(cfg):
    return {"mode": cfg.mode, "games": []}
main.scrape_lean = boom
main.scrape_llm = fake_llm
print(asyncio.run(main.scrape(cli_config="config.yaml")))
""",
        tmp_path,
    )
    assert proc.returncode == 0, proc.stderr
    assert "'mode': 'llm'" in proc.stdout
    assert "llmFallback is on" in proc.stderr
