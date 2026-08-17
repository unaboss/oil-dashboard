# Design — Officials & Military Tracker (Tab 9)

**Date:** 2026-08-15
**Status:** Approved
**App:** Oil Dashboard (`oil_dashboard/`)

## Goal

Track public statements by US government officials whose work touches oil, plus
military activity that mentions Iran. Integrated as a fourth inner tab,
"Officials & Military", inside the existing **Tab 9 — Research & Narrative**.

Original ask was a Truth Social API, but Truth Social's public endpoints return
no post content (all status/account/timeline routes are 403 without a session
token, and TMTG has no developer program). **Decision: pivot to mirror sources**
— Google News RSS + official agency RSS feeds.

## Sources (Approach 1 — approved)

| Source | Type | Coverage |
|---|---|---|
| `https://news.google.com/rss/search?q=<QUERY>&hl=en-US&gl=US&ceid=US:en` | Google News RSS | One query per official; catches news of every public statement |
| `https://www.energy.gov/rss/press-releases.xml` | DOE press-release RSS | Primary source — DOE statements |
| `https://www.defense.gov/DesktopModules/ArticleCS/RSS.ashx?max=20&ContentType=1&Site=945` | DoD press-releases RSS | Primary source — military statements |
| `https://www.state.gov/rss-feed/press-releases/feed/` | State press-release RSS | Primary source — State/sanctions statements |

Note: CENTCOM RSS is blocked (403) — military coverage uses the DoD feed plus
Google News military queries instead.

## Watch list

### Officials (Google News query per person)

- Secretary of Energy
- Secretary of the Interior (BLM / offshore leasing authority)
- Secretary of State (sanctions, Iran)
- Secretary of Defense
- EPA Administrator (emissions / pipeline rulings)
- FERC Chair (pipeline approvals)
- EIA Administrator (outlook / forecasts)

### Military (Google News queries + DoD feed), Iran-specific

- "Pentagon Iran"
- "CENTCOM Iran"
- "Department of Defense Iran"
- "military oil"

## Architecture

Follows the existing fetcher + cache + UI + test pattern.

### 1. `config.py` — additions

- `OFFICIALS_WATCH: list[dict]` — each `{name, query, category: "officials"}` for Google News.
- `MILITARY_WATCH: list[dict]` — each `{name, query, category: "military", keywords: ["Iran"]}`.
- `AGENCY_FEEDS: list[dict]` — each `{name, url, category}` for DOE/DoD/State
  (`category` ∈ `"energy"`, `"military"`, `"state"` — the DoD feed is
  `category: "military"` so agency military items are caught by the Iran filter).
- `CACHE_TTL_STATEMENTS = 3 * 60 * 60` — single cache TTL for the whole tracker
  feed (one cache key, `statements_officials`).
- `OFFICIAL_KEYWORDS` — oil-relevance keywords for officials filter
  (`oil`, `crude`, `gasoline`, `refinery`, `pipeline`, `sanction`, `energy`, `Iran`, …).

### 2. `data/fetcher_statements.py` — new

Single public entry point:

```python
def get_officials_statements() -> dict
```

Behaviour:

1. Read cache `statements_officials` via `data.cache.get`; return if fresh.
2. Fetch every RSS source via a shared `_fetch_and_parse_rss(url)` helper
   (`requests` + `xml.etree.ElementTree`, wrapped in `try/except`), used for
   both Google News queries and agency feeds — no duplicated parse logic.
3. Normalise every `<item>` to `{title, link, source, category, date, description}`:
   - `source` = watch entry name (official/military name) or agency feed name.
   - `category` = the watch entry / feed's category (see config additions).
   - `date` parsed from the RSS `pubDate` (RFC-2822, e.g.
     `Fri, 14 Aug 2026 09:40:42 GMT`) via `email.utils.parsedate_to_datetime`
     (UTC), then ISO-formatted. Do NOT use `datetime.fromisoformat`.
   - `description` HTML-unescaped + tags stripped via a small `_strip_html()`
     helper.
4. **Filtering:**
   - Officials items (`category == "officials"`): keep only if
     `title + description` contains an `OFFICIAL_KEYWORDS` term (noise cut —
     the query already targets the person).
   - Military items (`category == "military"`): keep only if text contains
     `Iran`. Google News military queries already include "Iran" in the query
     string, so this filter's real job is the **DoD agency feed**
     (`category: "military"`); it is applied uniformly and harmlessly.
   - Agency items in other categories (`energy`, `state`): keep only if text
     contains an `OFFICIAL_KEYWORDS` term.
5. Dedupe by `(title, source)`, sort newest-first (ISO date string sorts
   lexicographically = chronologically).
6. `data.cache.set(...)` and return.

Output shape (derived aggregates live in analysis, not here — no duplication):

```python
{
    "items": [ {title, link, source, category, date, description} ],
    "available": bool,
    "fetched_at": str,          # ISO UTC
}
```

Error handling: every fetch wrapped in `try/except: pass` (matches
`fetcher_bots.py`). A dead feed never breaks the tab. Empty result still gets
cached with `available: False`.

### 3. `analysis/officials_tracker.py` — new (pure, testable)

Only functions the UI actually consumes — no speculative abstractions:

- `count_mentions_per_source(items)` → per-source / per-category counts
  (feeds the metrics row).
- `group_mentions_by_date(items)` → date series per category (feeds the
  over-time chart).
- `extract_iran_mentions(items)` → military items whose text mentions Iran
  (feeds the highlighted Iran feed + count badge).

No I/O — unit-testable offline.

### 4. `ui/charts_research.py` — modify

- Add a 4th inner tab **"Officials & Military"**, rendered by a new private
  helper `_render_officials(statements_data)` (mirrors the existing
  `_render_trump` / `_render_bots` / `_render_traders` helpers).
- Render:
  - Metrics row (from `count_mentions_per_source`): officials statements,
    military-Iran mentions, agency statements, last fetched.
  - Bar/line chart (from `group_mentions_by_date`): mentions over time per
    category (grouped).
  - **Military / Iran feed** (from `extract_iran_mentions`): highlighted list
    (red badge) of military items mentioning Iran, newest first.
  - Searchable `st.dataframe` of all tracked items with a category column.
  - "How to Read This Tab" expander section.

Signature change: `render_research_tab(market_data, bot_trends_data, start, end)`
→ add `statements_data` param (kept backward-compatible ordering).

### 5. `app.py` — modify

- `@st.cache_data(ttl=1800)` loader `load_statements_data()` wrapping the fetcher.
- Spinner block in `main()`.
- Pass `statements_data` into `render_research_tab(...)`.

## Data flow

```
app.py  →  load_statements_data() (cached 30 min, streamlit cache)
        →  fetcher_statements.get_officials_statements() (disk cache)
        →  Google News RSS + agency feeds (try/except per feed)
        →  normalize → filter (oil keywords / Iran) → dedupe → sort
        →  analysis.officials_tracker (pure functions)
        →  ui.charts_research._render_officials()
```

## Error handling

- Every network call wrapped in try/except — individual feed failure never
  raises; result keeps whatever feeds succeeded.
- No API keys, no secrets added.
- Rate limiting: Google News RSS is lightweight (one request per official +
  per military query, cached for 3h).

## Testing

- `tests/test_officials_tracker.py` — pure-function tests:
  `count_mentions_per_source`, `group_mentions_by_date`,
  `extract_iran_mentions` with hand-built fixtures.
- `tests/test_fetcher_statements.py` — feed parsing + filtering with mocked RSS
  XML strings (no network), following `test_cache.py` / `test_trump_study.py`
  conventions (`monkeypatch` + `tmp_path` via the `sample_cache_dir` fixture).
- Cover: oil-keyword filter, Iran-only military filter, dedupe, empty feed,
  malformed XML, cache round-trip.

## Out of scope

- Truth Social (blocked without auth — see Goal).
- Historical backfill; data starts fresh on first fetch.
- Email/push alerts.
