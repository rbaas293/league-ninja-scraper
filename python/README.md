# Python scraper

See the [root README](../README.md) for config, modes, and environment variables.

## Requirements

- **Python 3.11+**
- Lean mode (default): nothing else — no API key, no Chrome, no Stagehand.
- llm mode / `llmFallback` only: the `[llm]` extra (`pip install -e ".[llm]"` or
  `pip install -r requirements-llm.txt`), Google Chrome, and `XAI_API_KEY` (or `BROWSERBASE_API_KEY`).
  Stagehand is imported lazily, so a missing extra/key only errors when llm actually runs.

## Setup

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt   # lean only; add requirements-llm.txt for llm mode
cp .env.example .env               # or reuse the repo-root .env
cp ../config.example.yaml ../config.yaml   # once; gitignored
# edit ../config.yaml — captainName / levels / mode / …
export XAI_API_KEY=...             # llm mode only, if not using .env
python main.py                     # lean by default
python main.py --ics games.ics     # also export an importable calendar file
```

Config: prefers **`../config.yaml`**, falls back to `python/config.yaml`.
Env: shell > `python/.env` > `../.env`.
Output: `python/games.json` (gitignored).

## Packaging (wheels / shiv)

`pyproject.toml` packages `main.py`, `lean_api.py`, `lean_http.py`, `token_usage.py`,
and `ics_export.py` with console script `stagehand-volleyball` (`main:main`). Core
dependencies (lean) match `requirements.txt`; the optional `[llm]` extra
(Stagehand + openai) matches `requirements-llm.txt`. Wheels and shiv binaries are
core-only by default (`pip install "stagehand-volleyball[llm]"` adds the fallback).

```bash
cd python
pip install -e ".[dev,llm]"      # editable + ruff/pytest/build/shiv
python -m build                  # wheels + sdist under dist/
shiv -c stagehand-volleyball -o dist/shiv/stagehand-volleyball.pyz .
pytest -q                        # unit + smoke (no live network)
```

GitHub Actions (`.github/workflows/python-ci.yml`) gates on scraper PR #1 being
merged, then runs checks (3.11/3.12), wheel builds, and shiv binaries.

## Config file location (wheels / shiv)

`stagehand-volleyball` (and `python main.py`) resolve config in order:

1. `--config PATH`
2. `$STAGEHAND_VOLLEYBALL_CONFIG`
3. `./config.yaml` (cwd)
4. Repo-root / `python/config.yaml` only for source checkouts

```bash
stagehand-volleyball --help
stagehand-volleyball --config /path/to/config.yaml --check-config
stagehand-volleyball --config config.yaml          # full scrape
```

Packaged installs never read `site-packages/config.yaml`. Put `config.yaml` in
the directory you run from, or pass `--config` / `$STAGEHAND_VOLLEYBALL_CONFIG`.
Use `--env-file` for allow-listed secrets (cwd `.env` is not auto-loaded).
Optional config key `httpTrustEnv` (default false) controls whether the xAI
HTTP client honors proxy environment variables.

## Output writes

`games.json` is written atomically (temp file + replace). The tool refuses to
write through a symlink at the output path.

