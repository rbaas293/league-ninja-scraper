# Development

[← Back to README](../README.md)

## Layout

| Path | Role |
|---|---|
| `config.example.yaml` | Public template at **repo root** (copy to a local `config.yaml`) |
| `config.yaml` | Local only (gitignored) |
| `python/main.py` | CLI entrypoint (`league-ninja-scraper`, legacy alias `stagehand-volleyball`) |
| `python/lean_api.py` | Pub-api client (lean mode) |
| `python/lean_http.py` | Robust lean HTTP (retries, circuit breaker, concurrency) |
| `python/token_usage.py` | xAI token / cost accumulator |
| `python/ics_export.py` | RFC 5545 `.ics` calendar export |
| `python/games.json` | Output (gitignored) |
| `.env` (root or `python/`) | Secrets (gitignored); root `.env` is the fallback |
| `docs/` | Detailed docs |

The scraper code stays under **`python/`** (not moved to repo root) so packaging and CI
that target `python/` keep working without path rewrites. The root holds config and
docs only.

## Setup from source

```bash
cd python
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt            # lean only; add requirements-llm.txt for llm mode
cp .env.example .env                       # or reuse the repo-root .env (llm mode only)
cp ../config.example.yaml ../config.yaml   # once; gitignored
python main.py                             # lean by default
python main.py --ics games.ics             # also export a calendar file
```

From a source checkout, config is read from `../config.yaml` (falling back to
`python/config.yaml`), env from shell > `python/.env` > `../.env`, and output goes
to `python/games.json`. See [CONFIGURATION.md](CONFIGURATION.md).

## Packaging (wheels / shiv)

`python/pyproject.toml` packages `main.py`, `lean_api.py`, `lean_http.py`,
`token_usage.py`, and `ics_export.py` as distribution `league-ninja-scraper`, with
console scripts `league-ninja-scraper` and the legacy alias `stagehand-volleyball`
(both `main:main`). Core (lean) dependencies match `requirements.txt`, and the
optional `[llm]` extra (Stagehand + openai) matches `requirements-llm.txt`. Wheels and
shiv binaries are core-only by default; `pip install "league-ninja-scraper[llm]"`
adds the fallback.

```bash
cd python
pip install -e ".[dev,llm]"      # editable + ruff/pytest/build/shiv
python -m build                  # wheels + sdist under dist/
shiv -c league-ninja-scraper -o dist/shiv/league-ninja-scraper.pyz .
pytest -q                        # unit + smoke (no live network)
ruff check .
```

Installed packages never read `site-packages/config.yaml`.

## Tests

`python/tests/` covers config resolution and `.env` handling, captain/team matching
and season selection, HTTP retries and the circuit breaker, the optional-llm
behavior (lean runs in a subprocess with stagehand/openai/httpx imports blocked and
no key), and the `.ics` export (structure, time zone/DST, stable UIDs, escaping and
injection, CLI). No test touches the live network.

## CI

GitHub Actions (`.github/workflows/python-ci.yml`):

- **gate-scraper-pr**: gates on the original scraper PR being merged.
- **check** (Python 3.11 / 3.12): `pip install -e ".[dev,llm]"`, ruff, byte-compile, pytest.
- **build wheels**: builds the wheel and sdist (artifact `league-ninja-scraper-wheels`), then
  smoke-tests a clean install. Checks `--help` for both CLI names, the missing-config
  error, `--check-config`, that stagehand is *not* installed, and `--ics-from` with no key.
- **build shiv binaries**: builds `league-ninja-scraper.pyz` (artifact
  `league-ninja-scraper-shiv`) and smoke-tests it the same way.

## Lean HTTP robustness

`python/lean_http.py` provides:

- Shared keep-alive connection pool per host, separate connect/read timeouts
- Exponential backoff with jitter; honors `Retry-After` on 429/503
- Per-request retry limit plus a total retry budget per run; retries bad/partial JSON
- Circuit breaker after N consecutive host failures (5xx/429/transport only, not other
  4xx), with a half-open probe; repeated failed probes or trips abort the run
- Whole-run wall-clock deadline; bounded concurrency for division fetches
- Run-level stats (retries, failures, circuit trips) reported in output `http`

If the run aborts on the circuit breaker, `games.json` is left untouched. Writes are
atomic (temp file + replace) and refuse to follow a symlink. Defaults (override under
`http:` in config):

```yaml
http:
  connectTimeoutS: 5.0
  readTimeoutS: 20.0
  maxRetries: 4          # per-request attempts
  maxRetriesTotal: 80    # retry budget for the whole run
  backoffBaseS: 0.4
  backoffMaxS: 10.0
  jitterS: 0.3
  circuitFailureThreshold: 5
  circuitCooldownS: 20.0
  maxHalfOpenFailures: 2  # consecutive failed probes → abort run
  maxCircuitTrips: 3      # open events before aborting the run
  runDeadlineS: 120.0     # whole-run wall-clock budget
  concurrency: 4         # parallel division fetches (bounded)
  # userAgent: "league-ninja-scraper/lean"
```
