# Acceptance criteria — FitFindr

Five criteria that say what "working" means for this agent, written in unit 3
**before** any results existed.

An acceptance criterion names a target: a number, a count, a rate, or something
a person could plainly observe. *"The agent handles errors"* is an opinion.
*"When search returns nothing, the agent stops before calling the second tool,
in 5 of 5 tries"* is a criterion.

Under each one, write a sentence or two on **why that target** and not a
stricter one. A reason that says something about your tools, your loop, or the
data earns credit; *"80% seemed reasonable"* does not.

> Missing your own targets next unit costs you nothing. Setting a target so
> easy you can't miss it does.

**Two are written for you. You write three.**

---

## 1. A matching query completes all three tools

Given a query that matches at least one listing, the agent completes all three
tool calls and returns a fit card — in at least 4 of 5 tries.

**Why this target:**
<!-- Why 4 of 5 and not 5 of 5? Something about your search, probably —
     "my search is a plain keyword match and some phrasings will miss" is a
     real answer. -->

---

## 2. An impossible query stops before the second tool

Given a query that matches no listings, the agent stops before calling
`suggest_outfit` and returns a message naming what to change — 5 of 5 tries.

**Why this target:**
<!-- Why is 5 of 5 reasonable here when criterion 1 isn't? What's different
     about this path? -->

---

## 3. The item search picks is the item both later tools receive

For `vintage graphic tee size L under $30`, the listing that search ranks first, the listing saved in `session["selected_item"]`, and the listing that `suggest_outfit` and `create_fit_card` each actually receive (their `in:` lines in the trace) are the same listing, with the same title, price and platform, in 5 of 5 tries.

**Why this target:**
No model touches this hand-off. Parsing is regex, `search_listings` scores keywords and sorts the same way every time (ties stay in data order), and the loop copies `search_results[0]` into the session. So a single mismatch is a bug in the loop, not randomness, and 4 of 5 would excuse a real bug. It isn't a free pass either: unit 4 moves search behind MCP and adds trace and error handling around exactly this hand-off. This query's top two results tie at score 3 with different prices (Graphic Tee — 2003 Tour Bootleg Style at $24, Vintage Band Tee at $19), so passing on the wrong one would show up in both title and price.

**How I'll mark a try:** In `run_agent`, read `item = session["selected_item"]` once, pass that same `item` to each tool, and log `inputs=item` on its trace step, so the trace shows what the tool really got. PASS if the `search_listings` step's `out:` line starts with the `selected_item` title, and the `suggest_outfit` and `create_fit_card` `in:` lines both read exactly like the `selected_item` line. If there are two search steps, use the last one before `suggest_outfit`. FAIL if any check differs, a step is missing, the try says `stopped early: yes`, or it crashed.

---

## 4. The fit card states the real price once and names the platform

For `silk slip dress in midi length under $40` (always the $30 90s Silk Slip Dress on depop), the fit card contains exactly one dollar amount, that amount is the item's real price, and the card names the platform, in at least 4 of 5 tries.

**Why this target:**
`create_fit_card` runs at temperature 0.9 with caching off, and nothing checks the caption before it's returned. One stray sample, such as two caption options each with a price or an invented "retail was $80", goes straight to the user, so I won't promise 5 of 5. But the exact price and the platform are written into the prompt, which asks for each once. Missing more than once in five would point at the prompt rather than luck, so 3 of 5 would be too easy. A wrong or doubled price is also the mistake a shopper would notice first.

**How I'll mark a try:** Look only inside that try's `Fit card:` block, because the `selected_item` line and the trace also contain `$30.0`. PASS if there is exactly one `$`, it's directly followed by 30, 30.0 or 30.00 with no more digits (`$30`, `$30!` and `$30.00` count; `$300`, `$30.50` and "30 bucks" don't), and "depop" appears anywhere in the card, ignoring capitalization ("Depop" and "#depopfinds" count). FAIL if any check fails or there is no fit card.

---

## 5. A broken API key gives a message, not a crash

With `GEMINI_API_KEY` deliberately broken and the query `90s track jacket in size M` (which search can match), the run ends with `session["error"]` containing "API key", no crash, and no outfit suggestion or fit card, in 5 of 5 tries.

**Why this target:**
Nothing here is random. With a bad key, the first model call (`suggest_outfit`) fails the same way every try: `generate()` doesn't retry it, and raises `ModelUnavailable` with a message that already says "API key". So a handler either works every time or never, and 4 of 5 would accept a stack trace for a failure I caused on purpose. It isn't an easy 5 of 5 either: `run_agent` has no handler today, so every try crashes. And because my loop re-runs whichever session field is still empty, a handler that sets `session["error"]` but doesn't `return` calls `suggest_outfit` again every pass until `check_iterations` stops it, which is still a crash.

**How I'll mark a try:** Run this scenario in its own pass with the key broken just for that command: `GEMINI_API_KEY=not-a-real-key python run_eval.py --label badkey` (a key set in the shell wins over `.env`, so `.env` stays untouched). Mark only the criterion 5 row in that file. Don't test with `python app.py ask`, because `app.py` catches every exception and would hide a crash. PASS if there is no `Crashed:` block, the try says `stopped early: yes — ` followed by a message containing "API key", and there is no `Outfit suggestion:` or `Fit card:` block.

---

<!-- ─────────────────────────────────────────────────────────────────────────
     UNIT 4 — read this before you change anything above.

     If a criterion turns out to be BROKEN rather than merely unmet, you can
     revise it, and that earns credit. But never delete or edit the original
     line. Add the revision underneath it, like this:

         ## 4. Something about the fit card

         The fit card is different every time.

         **Why this target:** ...

         > **Revised in unit 4:** For 5 different items, the 5 fit cards share
         > no opening sentence.
         >
         > **Why revised:** "different" wasn't checkable — two cards that
         > differed by one word still counted. The new version is something I
         > can actually score.

     That's a revision because the criterion couldn't be MEASURED.

     Lowering a target because you missed it is not a revision, and it costs
     you the point:

         ✗ "I said the empty search stops it 5 of 5 times, but I got 3 of 5,
            so 3 of 5 is more realistic."

     A number you missed stays where it is, gets diagnosed, and gets a fix
     attempted. That's where the points are.
     ───────────────────────────────────────────────────────────────────────── -->
