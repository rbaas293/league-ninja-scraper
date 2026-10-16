# LLM mode (optional Stagehand + Grok fallback)

[← Back to README](../README.md)

## Lean is the default

**Lean mode needs nothing but Python.** It reads the club's public league.ninja JSON
API over plain HTTP: **no API key, no LLM calls, no Chrome, and the Stagehand package
doesn't need to be installed.** A full week across Beer A + Beer B takes about 3 seconds.

| `mode` | What it does | Needs |
|---|---|---|
| **`lean`** (default) | Club public LMS API for seasons, division nav, standings, and schedules. | Python only |
| **`llm`** (optional) | [Stagehand v4](https://docs.stagehand.dev/v4/first-steps/quickstart) + xAI Grok BYO callback: browser `extract()` on standings and each schedule week. | `pip install ".[llm]"`, Chrome (or Browserbase), `XAI_API_KEY` |

Set `mode: lean|llm` in `config.yaml` or override with `SCRAPE_MODE`.

## The API key is only needed when llm actually runs

Stagehand and the openai client live in the optional `[llm]` extra. They're
imported, and `XAI_API_KEY` is checked, only at the moment llm mode actually runs.
If you never use it you never need a key. If you use it without the extra installed,
or without a key, you get a one-line error saying exactly what to install or set.
Lean runs are never affected.

```bash
cd python
pip install ".[llm]"                    # or: pip install -r requirements-llm.txt
SCRAPE_MODE=llm XAI_API_KEY=… python main.py
```

Requirements for llm mode: the `[llm]` extra, **Google Chrome** for a local browser
(`HEADLESS=false` to watch it), and `XAI_API_KEY`, or `BROWSERBASE_API_KEY` for a
Browserbase cloud browser plus Model Gateway.

### Why Grok via a callback?

Stagehand v4's first-class providers are openai/anthropic/google/groq/cerebras. xAI
Grok is reached through Stagehand's documented "bring your own LLM" callback, using
the OpenAI-compatible client pointed at `https://api.x.ai/v1`. The default model is
`grok-4-fast-reasoning` (override with `model:` or `STAGEHAND_MODEL`; an `xai/`
prefix is accepted). The xAI HTTP client ignores proxy env vars unless
`httpTrustEnv: true`.

## Automatic fallback (opt-in)

Set `llmFallback: true` in `config.yaml` (or `SCRAPE_LLM_FALLBACK=1`). Then, if a lean
run fails on a site/API error (outage, circuit breaker, standings probe error), the
scraper retries once with llm mode. Config and team-resolution errors never trigger
it. The key and the `[llm]` extra are only required if the fallback actually fires.

Note: with `levels` configured, llm mode still uses the club API to *discover*
divisions (and, by default, to prefilter standings, see `SCRAPE_LLM_PREFILTER`). So
the fallback helps when the standings or schedule endpoints fail or change shape,
but not during a full API outage. Single-division `leagueUrl` configs are scraped
entirely through the browser.

## Token usage and A/B comparison

Every run's output includes `tokenUsage` (calls, prompt/completion/total, reasoning
and cached tokens, estimated USD) and `runtimeSeconds`, and the run logs a usage
summary. Estimates use published xAI rates (see `python/token_usage.py`, e.g.
grok-4-fast at $0.20 / 1M input and $0.50 / 1M output).

To A/B the two modes on the same config:

```bash
SCRAPE_MODE=lean python main.py > lean.json
SCRAPE_MODE=llm  python main.py > llm.json
jq '{mode, runtimeSeconds, tokenUsage, games: (.games|length)}' lean.json llm.json
```

Lean always reports zero LLM calls and tokens. llm mode makes one or more extract
calls per standings page and schedule week, so its cost grows with the number of
divisions and weeks scanned.
