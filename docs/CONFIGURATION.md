# Configuration

[← Back to README](../README.md)

## The config file

`config.yaml` is **local only** (gitignored). Start from the public template at the repo root:

```bash
cp config.example.yaml config.yaml
# edit captainName / levels / siteUrl / mode / …
```

If `config.yaml` is missing, the scraper exits with an error that includes that `cp`
hint. It does **not** fall back to the example file. Validate a config without
scraping:

```bash
league-ninja-scraper --config config.yaml --check-config
```

## Config lookup order

The scraper resolves `config.yaml` in this order:

1. `--config PATH` on the CLI
2. `$LEAGUE_NINJA_CONFIG` (legacy alias: `$STAGEHAND_VOLLEYBALL_CONFIG`, used only when the new variable is unset)
3. `./config.yaml` in the current working directory
4. Repo-root `config.yaml` (and optional `python/config.yaml`) **only when running from a source checkout**

An explicit `--config` or env-var path that doesn't exist is a hard error. It
does not silently fall through to the cwd. Installed wheels and shiv binaries do
**not** look next to the package in site-packages, so put `config.yaml` in the
directory you run from or pass `--config` / `$LEAGUE_NINJA_CONFIG`. If nothing is
found, the error lists every path tried and reminds you to
`cp config.example.yaml config.yaml`.

## Config keys

| Field | Required | Purpose |
|---|---|---|
| `captainName` | one of captain/team | String or YAML list. Exact after normalizing punctuation/case (`"J Pike"` ≡ `"J. Pike"`; no substrings). |
| `teamName` | one of captain/team | Exact match; used only when `captainName` is empty. |
| `mode` | no | `lean` (default) or `llm`. See [LLM_MODE.md](LLM_MODE.md). |
| `levels` | no | Name substrings for multi-division discovery (e.g. `Beer A`, `Beer B`). |
| `siteUrl` | with levels | Club origin, e.g. `https://example.league.ninja`. |
| `apiBaseUrl` | no | Override pub API base (inferred for known clubs). |
| `season` | no | Optional season **name or uid** override. When empty, auto-pick prefers in-range seasons that have **posted** data for `levels` (skips "not posted yet"). |
| `http` | no | Lean HTTP knobs: timeouts, retries, Retry-After, circuit breaker, `concurrency` (default 4). See [DEVELOPMENT.md](DEVELOPMENT.md#lean-http-robustness). |
| `leagueUrl` | single-div | Division URL when `levels` is empty. |
| `day` / `league` | no | Notes for single-division; multi-division uses API fields. |
| `model` | no | xAI Grok id (default `grok-4-fast-reasoning`). llm mode only. |
| `schedulePathSuffix` | no | Default `"/schedule"` (llm mode). |
| `llmFallback` | no | Default `false`. Retry with llm mode if lean fails on a site/API error. |
| `httpTrustEnv` | no | Default `false`. Set `true` only if you intentionally want the xAI client to honor `HTTP(S)_PROXY` env vars. |

Keep string values in double quotes so characters like `:` or `#` are never misread.

### Multi-division and seasons

Multi-division: `levels: ["Beer A", "Beer B"]` plus `siteUrl`. Auto-pick prefers an
in-range season with **posted** data for those levels and skips seasons that exist
but aren't posted yet (no matching divisions or no teams). Output includes
`seasonStatus`. Empty team schedules are reported as "schedule not posted yet". Set
`season` to force a name or uid. Single-division `leagueUrl` still works when
`levels` is empty.

### Team resolution

`captainName` is preferred (exact after normalizing punctuation/case); otherwise the
exact `teamName` is used. Multi-division: a miss in one division is OK. It only
fails if nothing matches across all scanned divisions. Resolve errors name the
season scanned and hint at the `season` override.

## Environment variables

| Variable | Required | Purpose |
|---|---|---|
| `LEAGUE_NINJA_CONFIG` | optional | Path to config.yaml (see lookup order). Legacy alias `STAGEHAND_VOLLEYBALL_CONFIG`. |
| `XAI_API_KEY` | llm mode / fallback only | xAI key (`https://api.x.ai/v1`). Never needed for lean. |
| `BROWSERBASE_API_KEY` | optional | Cloud browser (+ Model Gateway if no xAI key). |
| `STAGEHAND_MODEL` | optional | Overrides `config.model`. |
| `SCRAPE_MODE` | optional | Overrides `config.mode`. |
| `SCRAPE_LLM_FALLBACK` | optional | `1`/`0` overrides `config.llmFallback`. |
| `SCRAPE_LLM_PREFILTER` | optional | Multi-division llm: default `1` HTTP-prefilters standings; `0` disables. |
| `HEADLESS` | optional | `false` to show Chrome (llm). |

## `.env` files

- Load order (first wins): **shell exports → `python/.env` → repo-root `.env`**.
- `.env` files are **not** auto-loaded from the cwd for installed binaries. Use
  `--env-file PATH`, or rely on `python/.env` / repo-root `.env` in a source checkout.
- Only allow-listed keys (the variables above plus `BROWSERBASE_*`) are imported
  from `.env` files. Shell exports always win and are unrestricted.
- `.env` files are gitignored; `.env.example` shows the format.

## Output

Stdout is JSON, and the run also writes `games.json`: `python/games.json` from a
source checkout, or `./games.json` in the cwd for installed binaries. Null keys are
omitted. `scrapedAt` is UTC with millisecond precision
(`YYYY-MM-DDTHH:MM:SS.mmmZ`). The file is written atomically, and the tool refuses
to write through a symlink. Each run logs LLM usage (calls, tokens, estimated USD),
which is zero in lean mode.
