"""
The FitFindr planning loop.

This is the file that makes FitFindr an agent rather than a script. It decides
which tool to run next based on what the last one returned.

If your loop calls all three tools no matter what comes back, you have a list
of function calls. A loop looks at the last result before it picks the next
step. **That branch is the graded part of this unit.**

Build and test your three tools in `tools.py` first. Then come here.

    python agent.py          runs both example paths below
"""

import re

import config
import trace
from tools import search_listings, suggest_outfit, create_fit_card
from generate import ModelUnavailable
from mcp_client import call_tool


# ── session state ─────────────────────────────────────────────────────────────

def new_session(query: str, wardrobe: dict) -> dict:
    """
    A fresh session for one user interaction.

    The session is the single source of truth for a run. Every tool result goes
    in here, and the next tool reads it back out.

    You could pass values straight from one call to the next. It would work,
    and you would not be able to test it — you can't print a variable you have
    already overwritten. Going through the session is what makes the state
    visible, and unit 4 has you write a criterion about exactly that.

    Add fields if you need them.
    """
    return {
        "query": query,              # what the user typed
        "parsed": {},                # description / size / max_price you pulled out of it
        "search_results": [],        # everything search_listings returned
        "selected_item": None,       # the one you chose — goes into suggest_outfit
        "wardrobe": wardrobe,        # the user's wardrobe
        "outfit_suggestion": None,   # what suggest_outfit returned
        "fit_card": None,            # what create_fit_card returned
        "error": None,               # set when the run ended early
    }


# ── query parsing ─────────────────────────────────────────────────────────────
# Regex, not the model: parsing is deterministic, testable on its own, and
# costs no model calls.

# "under $30", "below 30", "up to $45.50", or a bare "$30"
_PRICE_RE = re.compile(
    r"(?:under|below|less than|max(?:imum)?|up to|at most|<=?)\s*\$?\s*(\d+(?:\.\d+)?)"
    r"|\$\s*(\d+(?:\.\d+)?)(?:\s*(?:or less|or under|max))?",
    re.IGNORECASE,
)

# "size M", "size: small", "size US 8.5", "size W30", "size 8" — the word
# "size" is required, so "medium wash" doesn't get read as size M.
_SIZE_RE = re.compile(
    r"\b(?:size|sz)\s*:?\s*("
    r"us\s*\d+(?:\.\d+)?|w\d+(?:\s*l\d+)?|\d+(?:\.\d+)?|one size"
    r"|extra small|extra large|x-?small|x-?large|small|medium|large"
    r"|xxs|xxl|xs|xl|s|m|l"
    r")\b",
    re.IGNORECASE,
)

_SIZE_WORDS = {
    "extra small": "XS", "x-small": "XS", "xsmall": "XS", "small": "S",
    "medium": "M", "large": "L",
    "extra large": "XL", "x-large": "XL", "xlarge": "XL",
}

# Words that describe the asking, not the item. Left in, they'd only add noise
# to the keyword match.
_FILLER = {
    "looking", "for", "i", "im", "i'm", "want", "need", "find", "me", "show",
    "something", "some", "please", "a", "an", "the", "in", "under",
}


def _normalize_size(raw: str) -> str:
    raw = " ".join(raw.lower().split())
    if raw in _SIZE_WORDS:
        return _SIZE_WORDS[raw]
    if raw.startswith("us"):
        return "US " + raw[2:].strip()
    if raw[0].isdigit():
        return f"US {raw}"  # a bare number is a shoe size in this data
    return raw.upper()


def _parse_query(query: str) -> dict:
    """
    Pull a description, a size, and a max_price out of a plain-language query.

    "vintage graphic tee size M under $30"
        → {"description": "vintage graphic tee", "size": "M", "max_price": 30.0}

    size and max_price are None when the query doesn't mention them.
    """
    text = query

    max_price = None
    price_match = _PRICE_RE.search(text)
    if price_match:
        max_price = float(price_match.group(1) or price_match.group(2))
        text = text[:price_match.start()] + " " + text[price_match.end():]

    size = None
    size_match = _SIZE_RE.search(text)
    if size_match:
        size = _normalize_size(size_match.group(1))
        text = text[:size_match.start()] + " " + text[size_match.end():]

    words = re.findall(r"[a-z0-9']+", text.lower())
    description = " ".join(w for w in words if w not in _FILLER)

    return {"description": description, "size": size, "max_price": max_price}


def _no_results_message(parsed: dict) -> str:
    """The empty-search message: what was searched, and what to change."""
    description = parsed["description"]
    size = parsed["size"]
    max_price = parsed["max_price"]

    if not description:
        return (
            "I couldn't tell what item you're looking for. Describe it in a few "
            "words, like 'graphic tee' or 'denim jacket'."
        )

    searched = f'"{description}"'
    if size:
        searched += f" in size {size}"
    if max_price is not None:
        searched += f" under ${max_price:g}"

    tips = []
    if max_price is not None:
        tips.append("raise your price limit")
    if size:
        tips.append(f"drop the size {size}")
    tips.append("use broader words, like 'dress', 'jacket', or 'tee'")

    if len(tips) == 1:
        advice = tips[0]
    else:
        advice = ", ".join(tips[:-1]) + ", or " + tips[-1]
    return f"No listings matched {searched}. To find something, {advice}."


# ── planning loop ─────────────────────────────────────────────────────────────

def run_agent(query: str, wardrobe: dict) -> dict:
    """
    Run the loop once and return the finished session.

    Args:
        query:    what the user asked for, in plain language
                  (e.g. "vintage graphic tee under $30, size M").
        wardrobe: a wardrobe dict — get_example_wardrobe() or
                  get_empty_wardrobe() from utils/data_loader.py.

    Returns:
        The session dict. **Check session["error"] first** — if it isn't None,
        the run ended early and the later fields will still be None.

    ─────────────────────────────────────────────────────────────────────────
    TODO — build this, following the branch rule you wrote in Milestone 2.

      1. Start a session with new_session().

      2. Count the times round the loop, and call trace.check_iterations(count)
         on each one before you go again. It raises when the count passes
         MAX_ITERATIONS in config.py — see trace.py.

      3. Parse the query into a description, a size, and a max_price. Regex,
         string splitting, or asking the model are all fine — say which you
         chose in your README. Put the result in session["parsed"].

      4. Call search_listings() with what you parsed.
         Put the results in session["search_results"].

         ⚠️ THIS IS THE BRANCH. If nothing came back:
              - put a message in session["error"] saying what the user could
                change — "No results" is not that message
              - return the session
              - do NOT call suggest_outfit with nothing

      5. Choose an item — the first result is fine. Put it in
         session["selected_item"].

      6. Call suggest_outfit() with the selected item and the wardrobe.
         Put the result in session["outfit_suggestion"].

      7. Call create_fit_card() with the outfit and the item.
         Put the result in session["fit_card"].

      8. Return the session.

    ─────────────────────────────────────────────────────────────────────────
    IN UNIT 4 you come back and add two things:

      • Trace calls. One per step. `trace.step("search_listings", inputs=...,
        returned=...)` — see trace.py. Your README needs the output.

      • A handler for ModelUnavailable, so a bad key produces a message rather
        than a stack trace. The import is already at the top of this file.
    """
    session = new_session(query, wardrobe)

    # Each pass looks at what the session holds so far and runs the one step
    # that's missing. Every tool reads its inputs from the session and writes
    # its result back.
    count = 0
    while True:
        count += 1
        trace.check_iterations(count)

        if not session["parsed"]:
            session["parsed"] = _parse_query(session["query"])

        elif session["selected_item"] is None:
            parsed = session["parsed"]
            session['search_results'] = call_tool('search_listings', {
                'description': parsed['description'],
                'size': parsed['size'],
                'max_price': parsed['max_price'],
            })
            trace.step('search_listings', inputs=str(parsed), returned=session['search_results'], note=f'{len(session['search_results'])} matches')

            # THE BRANCH: nothing found → explain what to change, and stop
            # before suggest_outfit ever sees an empty result.
            if not session["search_results"]:
                session["error"] = _no_results_message(parsed)
                return session

            session["selected_item"] = session["search_results"][0]
            trace.step('Criteria 3', note=f'selected item is {session["selected_item"]}.')
        elif session["outfit_suggestion"] is None:
            session["outfit_suggestion"] = suggest_outfit(
                session["selected_item"], session["wardrobe"]
            )

        elif session["fit_card"] is None:
            session["fit_card"] = create_fit_card(
                session["outfit_suggestion"], session["selected_item"]
            )

        else:
            return session


# ── running it directly ───────────────────────────────────────────────────────

def _show(session: dict) -> None:
    if session["error"]:
        print(f"  stopped: {session['error']}")
        print(f"  fit_card is {session['fit_card']!r} — it should still be None here")
        return

    item = session["selected_item"] or {}
    print(f"  found:    {item.get('title')} — ${item.get('price')} on {item.get('platform')}")
    print(f"  outfit:   {session['outfit_suggestion']}")
    print(f"  fit card: {session['fit_card']}")


if __name__ == "__main__":
    from utils.data_loader import get_example_wardrobe

    print("=== A query the data can match ===")
    _show(run_agent(
        query="looking for a vintage graphic tee under $30",
        wardrobe=get_example_wardrobe(),
    ))

    print("\n=== A query it can't ===")
    _show(run_agent(
        query="designer ballgown size XXS under $5",
        wardrobe=get_example_wardrobe(),
    ))

    print(
        "\nThe second one should stop before the fit card. If both paths look "
        "the same,\nthe branch isn't doing anything yet."
    )
