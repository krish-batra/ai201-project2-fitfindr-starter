# FitFindr 🛍️

FitFindr is an AI styling assistant for secondhand shopping. Describe what you're
looking for in plain language — including size and price if you want — and the
agent searches a mock listings dataset, suggests outfits that pair the find with
your existing wardrobe, and writes a shareable "fit card" caption for it.

It runs a small, deterministic **planning loop** over three tools: a local
keyword search and two LLM-backed generators (outfit ideas + caption), wired up
behind a [Gradio](https://www.gradio.app/) web UI.

## Project Structure

```
ai201-project2-fitfindr-starter/
├── data/
│   ├── listings.json          # 40 mock secondhand listings
│   └── wardrobe_schema.json   # Wardrobe format + example/empty wardrobes
├── utils/
│   └── data_loader.py         # Helpers for loading listings & wardrobes
├── tests/
│   └── test_tools.py          # Pytest tests for the three tools
├── tools.py                   # The three tools: search / suggest / fit card
├── agent.py                   # Planning loop (run_agent) + query parsing
├── app.py                     # Gradio web interface
├── planning.md                # Design doc: tool specs, loop, architecture
└── requirements.txt           # Python dependencies
```

## Setup

1. Install dependencies (`groq`, `python-dotenv`, `gradio`, `pytest`):

   ```bash
   pip install -r requirements.txt
   ```

2. Get a free Groq API key at [console.groq.com](https://console.groq.com) and add
   it to a `.env` file in the project root:

   ```
   GROQ_API_KEY=your_key_here
   ```

   `search_listings` works without a key (it's pure local filtering), but
   `suggest_outfit` and `create_fit_card` need it. Without a key they return a
   descriptive error string rather than crashing.

## Running the App

```bash
python app.py
```

Open the localhost URL printed in the terminal (usually
<http://localhost:7860>). Type a query, pick **Example wardrobe** or **Empty
wardrobe**, and hit **Find it**. The three panels show the top listing, an outfit
idea, and a fit-card caption.

You can also drive the agent directly from the command line:

```bash
python agent.py
```

This runs a happy-path query and a deliberate no-results query so you can see
both branches of the planning loop.

## How It Works

```
User query + wardrobe choice
        │
        ▼
  handle_query (app.py)  ── picks example/empty wardrobe ──┐
        │                                                  │
        ▼                                                  │
  run_agent (agent.py)                                     │
        │                                                  │
        1. parse query  → {description, size, max_price}   │
        2. search_listings(...)                            │
        3. no results? → set session["error"], return ────┤ (error path)
        4. select top result                               │
        5. suggest_outfit(item, wardrobe)  ── Groq LLM     │
        6. create_fit_card(outfit, item)   ── Groq LLM     │
        7. return session                                  │
        │                                                  │
        ▼                                                  ▼
  Three output panels:  listing · outfit · fit card / error message
```

State for a single interaction lives in one `session` dict (created by
`_new_session` in `agent.py`), which is the single source of truth — each step
writes its output to a dedicated key and the next step reads from it. See
[planning.md](planning.md) for the full design.

### The Tools

| Tool | What it does | Backed by |
|------|--------------|-----------|
| `search_listings(description, size, max_price)` | Filters listings by size/price and ranks them by keyword overlap. Returns a list of listing dicts (`[]` if none match). | Local data |
| `suggest_outfit(new_item, wardrobe)` | Suggests 1–2 outfits naming real wardrobe pieces, or general styling advice if the wardrobe is empty. Returns a string. | Groq LLM |
| `create_fit_card(outfit, new_item)` | Writes a casual 2–4 sentence OOTD caption mentioning the item, price, and platform. Returns a string. | Groq LLM |

## The Mock Listings Dataset

`data/listings.json` contains 40 mock secondhand listings across categories
(tops, bottoms, outerwear, shoes, accessories) and styles (vintage, y2k, grunge,
cottagecore, streetwear, and more).

Each listing has: `id`, `title`, `description`, `category`, `style_tags`, `size`,
`condition`, `price`, `colors`, `brand`, and `platform`.

```python
from utils.data_loader import load_listings
listings = load_listings()
```

## The Wardrobe Schema

`data/wardrobe_schema.json` defines the format used to represent a user's existing
wardrobe. It includes:

- `schema`: field definitions for a wardrobe item (`id`, `name`, `category`,
  `colors`, `style_tags`, `notes`)
- `example_wardrobe`: a sample wardrobe with 10 items, for testing
- `empty_wardrobe`: a starting template for a new user

```python
from utils.data_loader import get_example_wardrobe, get_empty_wardrobe
wardrobe = get_example_wardrobe()
```

## Testing

```bash
pytest
```

`tests/test_tools.py` covers all three tools: search result/empty/filter cases,
and that the LLM tools always return a non-empty string (they pass whether the
Groq call succeeds or falls back to the error string, so tests run without a key).

> Note: pytest and the other dependencies install into your environment via
> `requirements.txt`. If you're using the project's `.venv`, run tests with
> `./.venv/Scripts/python -m pytest` on Windows.

## Planning Loop

`run_agent(query, wardrobe)` in `agent.py` runs one deterministic pass — it does
not let the LLM choose tools. The conditional logic, in plain English:

1. Create the session with `_new_session(query, wardrobe)`.
2. Parse the query into `{description, size, max_price}` using regex
   (`_parse_query`): pull a `size M` / `size S/M` token, pull a price from
   `under $30` / `under 30` / `below`/`less than`/`max`, and treat the leftover
   text as the description.
3. Call `search_listings(description, size, max_price)` and store the list in
   `session["search_results"]`.
4. **If `search_results` is empty:** set `session["error"]` to a message naming
   the filters that failed (description, size, price), and **return the session
   early — do not call `suggest_outfit`.**
5. **Otherwise:** set `session["selected_item"]` to the top-ranked result
   (`search_results[0]`).
6. Call `suggest_outfit(selected_item, wardrobe)` and store the string in
   `session["outfit_suggestion"]`.
7. Call `create_fit_card(outfit_suggestion, selected_item)` and store the string
   in `session["fit_card"]`.
8. Return the session. The caller (`handle_query` in `app.py`) checks
   `session["error"]` first; if it's `None`, it reads the three output fields.

The loop terminates either at the early return in step 4 (no results) or after
step 7 (all outputs populated).

## State Management

A single `session` dict (built by `_new_session`) is the single source of truth
for one interaction. Each step writes to a dedicated key; the next step reads it.
Tools never call each other directly — everything flows through the session.

| Key | Stores | Written by | Read by |
|-----|--------|-----------|---------|
| `query` | The raw user query | `_new_session` | parse step |
| `parsed` | `{description, size, max_price}` | step 2 (`_parse_query`) | `search_listings` |
| `search_results` | List of matching listing dicts | step 3 (`search_listings`) | empty-check / selection |
| `selected_item` | The top-ranked listing dict | step 5 | `suggest_outfit`, `create_fit_card` |
| `wardrobe` | The user's wardrobe dict | `_new_session` | `suggest_outfit` |
| `outfit_suggestion` | Outfit ideas string | step 6 (`suggest_outfit`) | `create_fit_card`, output |
| `fit_card` | Caption string | step 7 (`create_fit_card`) | output |
| `error` | Early-exit message (starts `None`) | step 4 on no-results | caller, checked first |

Data flow: `query → parsed → selected_item (from search_results) → outfit_suggestion → fit_card`.
`wardrobe` is injected at session creation and read once by `suggest_outfit`.

## Error Handling

| Tool | Failure mode | What the agent does |
|------|-------------|---------------------|
| `search_listings` | No listing matches the keywords/size/price | Returns `[]` (never raises). The loop detects the empty list, sets `session["error"]` naming the failed filters, and returns early without calling the LLM tools. |
| `suggest_outfit` | Wardrobe is empty (`items == []`) | Not an error: branches to a general-styling-advice prompt and still returns a non-empty string, so the pipeline continues. (Any Groq/API error returns a descriptive error string instead of raising.) |
| `create_fit_card` | `outfit` is empty or whitespace-only | Returns a descriptive error string *before* calling the LLM. (Any Groq/API error likewise returns an error string.) |

**Concrete example from testing:** Running `python agent.py` with the query
`"designer ballgown size XXS under $5"` parsed to
`{description: "designer ballgown", size: "XXS", max_price: 5.0}`.
`search_listings` returned `[]`, so the loop set:

```
No listings matched 'designer ballgown', size XXS, under $5. Try loosening your
filters — a higher price, a different size, or broader keywords.
```

…and returned immediately, leaving `outfit_suggestion` and `fit_card` as `None` —
`suggest_outfit` was never called. Separately, `test_fit_card_empty_outfit`
confirmed `create_fit_card("", item)` returns the guard string with no API call.

## Spec Reflection

- **One way the spec helped:** Writing the Tool 1 spec in `planning.md` first
  (filter → score → drop-zero → sort, "return `[]`, never raise") meant
  `search_listings` had an exact contract before any code existed. The empty-list
  contract is what let the planning loop rely on a simple `if not search_results`
  check instead of wrapping the call in try/except — the no-results path fell out
  of the design cleanly.
- **One way implementation diverged:** The `app.py` step referenced a
  `session["listing_text"]` key, but the session dict defined in `_new_session`
  never had one. Rather than add a key, `handle_query` formats the listing block
  directly from `session["selected_item"]` (title, price, condition, platform,
  size, brand, colors, tags, description). The formatting lives in the UI layer
  instead of the agent — a reasonable place for presentation logic.

## AI Usage

1. **Implementing `search_listings`:** I gave Claude Code the Tool 1 spec from
   `planning.md` (inputs, the filter→score→sort steps, the "return `[]`, never
   raise" contract) and the existing stub/docstring in `tools.py`. It produced the
   filtering + keyword-overlap scoring implementation. I had it **add the missing
   `import re`** after the IDE flagged `"re" is not defined`, and I noted that its
   scoring counts *distinct* keyword presence (a repeated term counts once) rather
   than frequency — I kept that behavior since it matches the "keyword overlap"
   spec. I then verified it against three queries (a vintage-tee match, a price
   filter, and a no-match query returning `[]`).
2. **Implementing `run_agent` + query parsing:** I gave Claude Code the 8-step
   planning-loop spec and the `_new_session` structure. It implemented the loop and
   factored the regex parsing into a `_parse_query` helper (the spec had it inline
   in step 2). I verified both branches by running `python agent.py`: the happy
   path filled all three panels, and the no-results query produced the early-exit
   error. I confirmed the size regex requires the literal word "size" (e.g.
   `"size M"`) — a bare "M" won't be parsed — which matches the spec's examples.
