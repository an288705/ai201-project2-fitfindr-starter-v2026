# FitFindr

> ### 👋 Start here
>
> **New to this repo? Read [RUNNING.md](RUNNING.md) first** — setup, every
> command, and what to do when something breaks.
>
> Once `python test.py` passes:
>
> ```bash
> python app.py listings --full -n 6      # read the data (Milestone 1)
> python app.py fields                    # what you can filter on
> python app.py ask 'vintage graphic tee under $30'
> ```
>
> All three tools are stubs, so that last command will do nothing useful yet.
> That's the starting position.
>
> **The rest of this file is your submission.** Fill it in as you go.

---

<!-- ─────────────────────────────────────────────────────────────────────────
     HOW TO USE THIS FILE

     This is your submission. Fill each section in as you finish the milestone
     it belongs to — don't leave it all to the end.

     Unit 3 asks for the first five sections. Unit 4 adds the five below them.
     Leave the unit 4 sections alone until then; they're here so you know
     what's coming.

     Everything is pasted as TEXT. No screenshots, no images, no video links.
     A typed block of output gets full credit; a picture of the same output
     gets none.
     ───────────────────────────────────────────────────────────────────────── -->

<!-- ═══════════════════════ UNIT 3 — THE BUILD ═══════════════════════ -->

## What This Does

<!-- Three or four sentences: what a user asks for, and what they get back. -->

FitFindr helps someone shop for secondhand clothes. They type what they want in plain language, like `vintage graphic tee under $30` or `platform sneakers size 8`. The agent pulls a description, size, and price limit out of the query, searches the thrift listings, and picks the best match. It then suggests one or two outfits that pair the find with pieces from the user's wardrobe (or general styling advice if the wardrobe is empty), and writes a short caption they could post about it. If nothing matches, it stops and tells them what to change, such as raising the price limit or dropping the size.

---

## Tool Inventory

<!-- Four lines per tool. This is worth 2 points and it's the single most
     common place students lose them.

     "Returns a list" earns NOTHING. The description has to say what is IN
     the list.

     The empty case isn't optional either — it's the thing your loop branches
     on, and if you don't decide it here you'll discover it as a crash in
     Milestone 5. -->

### `search_listings`

- **What it does:**
Search the listings data for items matching a description, and optionally a size and a price ceiling.
- **Inputs:** <!-- name and type each: `max_price` (float), not "a price" -->
    description: str,
    size: str | None = None,
    max_price: float | None = None,
- **Returns:**
list[dict]
- **When it has nothing:**

### `suggest_outfit`

- **What it does:**
Given a thrifted item and the user's wardrobe, suggest one or two outfits.
- **Inputs:**
new_item: dict, wardrobe: dict
- **Returns:**
str
- **When it has nothing:**

### `create_fit_card`

- **What it does:**
Write a short caption someone would actually post about the find.
- **Inputs:**
outfit: str, new_item: dict
- **Returns:**
str
- **When it has nothing:**

---

## Planning Loop

<!-- Your branch rule, stated as a rule — the condition AND both paths — plus
     the file and function that holds it.

     Like this:
       "If search_listings returns an empty list, put a message in the session
        and stop. Otherwise take the first result and go to suggest_outfit."
        — agent.py::run_agent

     The grader checks your code against what you claim here, so the file and
     function have to be real. -->

**Branch rule:** If `search_listings` returns an empty list, put a message in `session["error"]` that says what the user searched for and what to change (raise the price limit, drop the size, or use broader words), and return the session without calling `suggest_outfit` or `create_fit_card`. Otherwise, take the first result as `session["selected_item"]` and go to `suggest_outfit`.

**Where it lives:** `agent.py::run_agent`

**How the query is parsed:** Regex, in `agent.py::_parse_query`. One pattern finds the price limit (`under $30`, `below 30`, `up to $45`, or a bare `$30`). Another finds the size, but only after the word "size" (`size M`, `size: small`, `size US 8.5`, `size 8`), so phrases like "medium wash" aren't read as a size. Whatever is left, minus filler words like "looking for", becomes the description. A query with no price or size gets `None` for that field. I chose regex over asking the model because it gives the same answer every time, can be tested on its own, and doesn't use up model calls.

**What moves through the session:** `query` → `parsed` (description, size, max_price) → `search_results` → `selected_item` → `outfit_suggestion` → `fit_card`. Each pass of the loop fills in the first missing field, and each tool reads its inputs from the session. If the search is empty, `error` is set and the later fields stay `None`.

---

## Sample Run

<!-- Two things go here.

     1. One FULL query and its output, pasted as text.
     2. Your three per-tool terminal tests — the command and what it printed. -->

**One full query**

```
python app.py ask 'vintage graphic tee under $30'

  Found:    Y2K Baby Tee — Butterfly Print — $18.0 on depop

  Outfit:   **Outfit 1: Casual Y2K Streetwear**
*   **New Item:** Butterfly Baby Tee
*   **Bottoms:** Baggy straight-leg jeans (dark wash)
*   **Shoes:** Chunky white sneakers
*   **Outerwear:** Black cropped zip hoodie
*   **Accessories:** Black crossbody bag

**Outfit 2: Contrast Mix (Soft & Edgy)**
*   **New Item:** Butterfly Baby Tee
*   **Bottoms:** Wide-leg khaki trousers
*   **Shoes:** Black combat boots
*   **Accessories:** Brown leather belt, black crossbody bag

  Fit card: Scored this literal dream Y2K butterfly baby tee for just $18 on Depop and I’m obsessed! Giving major casual streetwear energy with baggy jeans and chunky sneakers, but I can't wait to toughen it up with wide-leg trousers and combat boots next. Thrift gods truly delivered on this one. 🦋✨

1 model calls this session, 1 served from cache, 203 prompt + 69 output tokens

```

**The three tools, tested one at a time**

```
$ python -c "from tools import search_listings; print(search_listings('graphic tee', max_price=30))"

```

```
$ python -c "from tools import suggest_outfit; ..."

```

```
$ python -c "from tools import create_fit_card; ..."

```

---

## How I Used AI

<!-- Two specific moments. What you asked, what came back, what you changed.

     "I used Claude to help me code" is not enough.

     "I gave Claude my search_listings spec. It returned None on no match
     instead of an empty list, so I changed it" is the level we want. -->

**Moment 1**

- *What I asked for:* I asked Claude to fix the bugs in my `search_listings` and its helper functions.
- *What came back:* It found four bugs. `_size_tokens` used `.upper` without parentheses, so it stored the method instead of the uppercased text and no size could ever match. My filter used `listing` instead of `listings` and compared against `size` and `max_price` even when they were `None`, which would crash. I built `(listing, score)` pairs but unpacked them as `(score, listing)`, so the sort used the wrong value. And `re` wasn't imported.
- *What I changed:* I kept the fixes. The filter now skips the price and size checks when they're `None` and uses `<=`, because the price limit is inclusive. Everything is `(score, listing)` now, so results sort by score.

**Moment 2**

- *What I asked for:* I asked Claude to rate my first version of `suggest_outfit`.
- *What came back:* It gave it about 5/10. I was also putting the raw list of wardrobe dicts into the prompt, IDs and all. It also said the prompt only included the title and never asked for 1–2 outfits that name pieces from the wardrobe.
- *What I changed:* I wrote a `wardrobe_text` line per item (name, category, colors) myself. Then Claude added the item's category, colors, and style tags to the prompt, the instruction to name specific wardrobe pieces, a short system prompt, and a fallback message so the tool never returns an empty string.

Claude also wrote most of `create_fit_card` and the `run_agent` loop. I asked why the loop uses `elif` instead of separate `if`s. The answer: `elif` makes each pass run exactly one step, so the loop decides the next step from the session instead of running everything in order. I kept it that way and renamed `parse_query` to `_parse_query`.

<!-- ═══════════════════════ UNIT 4 — THE TEST ═══════════════════════

     Don't fill these in during unit 3.
     ═══════════════════════════════════════════════════════════════════ -->

---

## Run Log — Before

<!-- Five criteria, five tries each, in this exact format.

     Five, because your criteria are written out of five. Mark each try PASS
     or FAIL, count the passes, and read that count against your target — a
     row targeting 4 of 5 with three PASS cells is MISSED (3/5).

     `python run_eval.py --label before` runs everything and writes the table
     into results/. Paste it here and fill in the verdicts. -->

| Criterion | Target | Try 1 | Try 2 | Try 3 | Try 4 | Try 5 | Verdict |
|---|---|---|---|---|---|---|---|
| 1.  |  |  |  |  |  |  |  |
| 2.  |  |  |  |  |  |  |  |
| 3.  |  |  |  |  |  |  |  |
| 4.  |  |  |  |  |  |  |  |
| 5.  |  |  |  |  |  |  |  |

**Real output from one try**, pasted as text, naming the file and function
that produced it:

```

```

---

## Verdicts and Diagnoses

<!-- MET or MISSED per criterion against LAST UNIT's target, plus a sentence on
     how you decided.

     Then, for every miss: which of the four places it happened — a tool, the
     loop's branch, the session, or the model's output — AND the mechanism.

     Not a diagnosis:  "The fit card was bad."
     A diagnosis:      "The fit card criterion missed on 2 of 5 items. Both had
                        an empty brand field. My prompt puts the brand in the
                        first sentence, so the card opened with a blank and read
                        like a fragment. The tool worked; the prompt assumed a
                        field that isn't always there."

     Look for a pattern. Three misses on the same tool is one problem, not
     three. -->

| # | Criterion | Target | Verdict | How I decided |
|---|---|---|---|---|
| 1 | matching query completes | 4/5 | MET | saw run |
| 2 | impossible query stops early  | 4/5 | MET | saw run |
| 3 | The item search picks is the item both later tools receive | MET | 5/5 | saw run |
| 4 | The fit card states the real price once and names the platform | MET | 5/5 | saw run |
| 5 | A broken API key gives a message, not a crash | 4/5 | MET  | I saw on Loop Trace |

**Diagnoses**



---

## Loop Trace

**Happy path**

```
[1] search_listings
      in:  {'description': 'vintage graphic tee', 'size': None, 'max_price': 30.0}
      out: 10 items: Y2K Baby Tee — Butterfly Print, Graphic Tee — 2003 Tour Bootleg Style, Vintage Band Tee — Faded Grey … +7 more
      →    10 matches
```

**Empty search**

```
[1] search_listings
      in:  {'description': 'vintage graphic tee', 'size': None, 'max_price': 0.0}
      out: [] (empty)
      →    0 matches
```

**Empty wardrobe**
(running with an empty wardrobe)
[1] search_listings
      in:  {'description': 'vintage graphic tee', 'size': None, 'max_price': 30.0}
      out: 10 items: Y2K Baby Tee — Butterfly Print, Graphic Tee — 2003 Tour Bootleg Style, Vintage Band Tee — Faded Grey … +7 more
      →    10 matches

**Model unavailable**
[1] search_listings
      in:  {'description': 'vintage graphic tee', 'size': None, 'max_price': 30.0}
      out: 10 items: Y2K Baby Tee — Butterfly Print, Graphic Tee — 2003 Tour Bootleg Style, Vintage Band Tee — Faded Grey … +7 more
      →    10 matches
1 model calls this session, 1 served from cache

ModelUnavailable: The model rejected your API key. Check GEMINI_API_KEY in your .env file, or create a fresh key at aistudio.google.com.

**On the MCP move:** <!-- what changed in your code, and whether anything
behaved differently afterwards. If the rewire didn't work, say exactly where it
broke — the error text and the last thing that worked. That earns the point in
full. -->



---

## The Improvement

<!-- What you changed, why your diagnosis pointed at it, and the after-run in
     the same table format. One change, measured properly.

     `python run_eval.py --label after` -->

**What I changed:**

**Which failure it was meant to fix:**

### Run Log — After

| # | Criterion | Target | Verdict | How I decided |
|---|---|---|---|---|
| 1 | matching query completes | 4/5 | MET | saw run |
| 2 | impossible query stops early  | 4/5 | MET | saw run |
| 3 | The item search picks is the item both later tools receive | 4/5 | MET | saw run |
| 4 | The fit card states the real price once and names the platform | 4/5 | MET | saw run |
| 5 | A broken API key gives a message, not a crash | 4/5 | MET  | I saw on Loop Trace |

**Did it help, and how do I know:**

<!-- If it made things worse, say that. Honestly reported, that earns full
     credit and is more interesting than one that worked. -->



---

## What's Still Broken

First run was perfect

---

📖 **How to run this project: [RUNNING.md](RUNNING.md)**
