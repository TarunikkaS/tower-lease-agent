<div align="center">

```
╔════════════════════════════════════════════════════════════════╗
║                                                                  ║
║          T O W E R   L E A S E   R E Q U E S T   A G E N T       ║
║                                                                  ║
║        plain-text request  ──►  structured JSON verdict          ║
║                                                                  ║
╚════════════════════════════════════════════════════════════════╝
```

A backend Python agent that reads an operator's **plain-English** request to
lease space on a telecom tower, understands it, checks it against the company's
rules, and replies with a clear **APPROVED / REJECTED** verdict as structured JSON.

![Python](https://img.shields.io/badge/Python-3.8+-3776AB?style=flat-square&logo=python&logoColor=white)
![Dependencies](https://img.shields.io/badge/dependencies-none-success?style=flat-square)
![Std Library](https://img.shields.io/badge/built%20with-standard%20library-blue?style=flat-square)
![Tests](https://img.shields.io/badge/tests-15%20passing-brightgreen?style=flat-square)

</div>

---

## Overview

A telecom infrastructure company rents physical space on its towers to mobile
operators (Du, Etisalat, ...). Operators don't fill in tidy forms — they simply
**write a sentence** describing what they want to install.

A human used to read each message, look up the tower, recall the regional rules,
do the math, and reply yes or no. **This agent does that job automatically.**

```
   "Operator Du wants to mount a 15kg 5G antenna
    at a height of 40 meters on Tower TWR-101."
                       |
                       v
   +--------------------------------------------+
   |   1.  READ     the sentence                |
   |   2.  EXTRACT  operator/tower/equipment... |
   |   3.  CHECK    tower DB + regional policy  |
   |   4.  JUDGE    approve / reject + reason   |
   +--------------------------------------------+
                       |
                       v
             { "status": "APPROVED", ... }
```

### What this is (and isn't)

This is a **lightweight, deterministic backend agent**. It works in an
"AI-style" pipeline — *understand the request, then reason over tools/rules* —
but the understanding is **rule-based regex extraction** and the decision is made
by **fixed business rules**. There is **no LLM, no LangChain, and no external
dependency** — just the Python standard library. The same input always produces
the same output, which makes it predictable, fast, and easy to test.

---

## How it works

| Step | Job | Lives in |
|:----:|-----|----------|
| 1 | **Read** the plain-text request (any supported sentence shape) | `main.py` |
| 2 | **Extract** operator, tower, equipment, weight, height (regex) | `agent.py` |
| 3 | **Cross-reference** the tower DB + regional policies | `tools.py` |
| 4 | **Judge** -> APPROVED / REJECTED + reason + rule checks | `agent.py` |

---

## The agent workflow (and why this design)

This is best described as a **deterministic backend AI-style agent with
tool-based rule checking**. The "AI" here is not a trained model — it is the
**agent workflow**: the system perceives natural language, structures it,
retrieves facts through tools, reasons over rules, and produces a decision.

```
   natural-language request
            |
            v
   [ 1. structured extraction ]   regex turns the sentence into fields
            |                      (operator, tower, equipment, weight, height)
            v
   [ 2. tool / data lookup ]      tools.py reads the tower DB + policy file
            |                      (load_towers / load_policies / find_tower)
            v
   [ 3. rule-based reasoning ]    sequential business rules, stop at first failure
            |                      (capacity, regional height, single-asset weight)
            v
   [ 4. structured decision ]     APPROVED / REJECTED + reason + per-rule checks
```

**Why a deterministic, rule-based agent — not a machine-learning model or an
LLM?** Because this is a *compliance / vetting* task, and for that the rule-based
design is the **correct** engineering choice, not a shortcut:

| Property | Why it matters for lease vetting |
|----------|----------------------------------|
| **Deterministic** | The same request always yields the same verdict — essential when a decision must be defended to a regulator or operator. |
| **Auditable** | Every verdict ships with a `checks` object showing exactly which rule passed, failed, or did not apply. You can trace *why*. |
| **No hallucination** | A probabilistic model could approve an over-weight tower on a bad day. Fixed rules cannot. |
| **Fast & free** | No model inference, no API calls, no network — it runs instantly offline. |
| **Easy to test** | Deterministic logic means the 8 unit tests fully pin the behavior. |

In short: the **language understanding** is rule-based extraction, and the
**judgment** is a transparent rule engine — exactly the separation you want when
a wrong "APPROVED" has real-world structural consequences. (An LLM extraction
layer could be added in front of step 1 for messier free-text, but the
rule-based decision core should stay deterministic.)

---

## Project structure

```
tower-lease-agent/
|
|-- main.py                 # Entry point   - feeds requests in, prints JSON out
|-- agent.py                # The brain     - regex extraction + decision rules
|-- tools.py                # Data layer    - loads the JSON DB + the policies TXT
|-- test_agent.py           # Tests         - 15 unittest cases, no dependencies
|
|-- towers_inventory.json   # Tower database (120 towers; scales to thousands)
|-- regional_policies.txt   # Municipality rules per region
|
|-- sample_outputs.txt      # Captured output of every case (proof it works)
|-- requirements.txt        # Dependencies  - none, pure standard library
|-- .gitignore              # Keeps cache / OS noise out of git
`-- README.md               # You are here
```

**Design principle — one job per file.** `tools.py` knows *where data lives*,
`agent.py` knows *how to decide*, `main.py` knows *how to talk to the user*. The
brain never opens a file directly, so swapping the JSON for a real database later
would change **only** `tools.py`.

---

## Getting started

Requires **Python 3.8+**. Nothing to install — pure standard library.

**Step 1 — open a terminal in the project folder**

```bash
cd path/to/tower-lease-agent
```

**Step 2 — run one of the three commands below.** `main.py` is the only file
you ever run directly; it loads the data and drives the agent for you.

```bash
# (A) Run all 7 built-in demo cases  (1 approved + 6 rejected)
python3 main.py

# (B) Judge ONE request of your own   (write any sentence in quotes)
python3 main.py "Operator Du wants to mount a 15kg 5G antenna at a height of 40 meters on Tower TWR-101."

# (C) Run the test suite              (15 unittest cases)
python3 -m unittest test_agent.py
```

> On Windows, use `python` instead of `python3`.

### What each command prints

**(A) and (B)** print the request followed by the structured JSON judgment:

```text
INPUT:
  Operator Du wants to mount a 15kg 5G antenna at a height of 40 meters on Tower TWR-101.
OUTPUT:
{
  "status": "APPROVED",
  ...
  "final_tower_weight_kg": 475
}
----------------------------------------------------------------------
```

**(C)** prints the test results — a row of dots, one per passing test:

```text
...............
----------------------------------------------------------------------
Ran 15 tests in 0.002s

OK
```

> Prefer not to run anything? The captured output of all 7 demo cases is saved
> in [`sample_outputs.txt`](sample_outputs.txt).

### How the pieces fit together (what runs under the hood)

```
   you type:  python3 main.py "Operator Du wants ... TWR-101."
                       |
                       v
   main.py            -> receives the text, calls the agent
                       |
                       v
   agent.py           -> 1) extract_request_details()  reads the sentence (regex)
                          2) evaluate_request()         applies the rules
                       |          |
                       |          v
                       |   tools.py  -> load_towers()    reads towers_inventory.json
                       |               load_policies()  reads regional_policies.txt
                       |               find_tower()      instant lookup by tower_id
                       v
   main.py            -> prints the final JSON judgment to your terminal
```

You only ever call `main.py`. It calls `agent.py` (the decision logic), which in
turn calls `tools.py` (the data layer) to read the JSON and TXT files.

---

## The rules it enforces

The agent runs five checks **in order and stops at the first failure** — just
like a careful human reviewer.

```
  request --> [ 0. parsed ok?        ] --no--> REJECTED  (request_parse_check)
                     |
                    yes
                     v
              [ 1. tower exists?      ] --no--> REJECTED  (tower_exists)
                     |
                    yes
                     v
              [ 2. weight capacity?   ] --no--> REJECTED  (weight_capacity_check)
                     |
                    yes
                     v
              [ 3. regional height?   ] --no--> REJECTED  (regional_height_check)
                     |
                    yes
                     v
        [ 4. regional asset weight?   ] --no--> REJECTED  (regional_single_asset_weight_check)
                     |
                    yes
                     v
                  APPROVED  (+ final_tower_weight_kg)
```

| # | Check key | Rule |
|:-:|-----------|------|
| 0 | `request_parse_check` | Tower ID, weight, **and** height must all be readable from the text. |
| 1 | `tower_exists` | The tower ID must be in `towers_inventory.json`. |
| 2 | `weight_capacity_check` | `current_weight + requested_weight <= max_allowed_weight` |
| 3 | `regional_height_check` | Requested height <= the region's height limit. |
| 4 | `regional_single_asset_weight_check` | A single asset <= the region's per-asset limit. |

Each check reports one of four states, so the JSON tells the **full story** of a
decision:

| State | Meaning |
|-------|---------|
| `PASSED` | The rule was checked and satisfied. |
| `FAILED` | The rule was checked and broken (this is why it was rejected). |
| `NOT_APPLICABLE` | The region has no such rule, so there's nothing to enforce. |
| `NOT_RUN` | An earlier check failed, so this one was never reached. |

---

## Example: approved request

**Input**

```
Operator Du wants to mount a 15kg 5G antenna at a height of 40 meters on Tower TWR-101.
```

**Output**

```json
{
  "status": "APPROVED",
  "operator": "Du",
  "tower_id": "TWR-101",
  "equipment_type": "5G antenna",
  "requested_weight_kg": 15,
  "requested_height_m": 40,
  "region": "DXB-North",
  "checks": {
    "request_parse_check": "PASSED",
    "tower_exists": true,
    "weight_capacity_check": "PASSED",
    "regional_height_check": "PASSED",
    "regional_single_asset_weight_check": "NOT_APPLICABLE"
  },
  "reason": "Request approved. Tower TWR-101 has enough remaining capacity (475kg of 500kg used) and the request satisfies all DXB-North regional policies.",
  "final_tower_weight_kg": 475
}
```

> 460kg current + 15kg = 475kg <= 500kg, and 40m <= the DXB-North 45m limit.
> DXB-North has no single-asset weight rule, so that check is `NOT_APPLICABLE`.

## Example: every rejection path

| Scenario | Example request | Why it's rejected |
|----------|-----------------|-------------------|
| **Unreadable request** | `... mount a 15kg 5G antenna on TWR-101.` (no height) | Height could not be parsed. |
| **Tower not found** | `... on Tower TWR-999.` | TWR-999 isn't in the inventory. |
| **Weight capacity exceeded** | `20kg dish ... on TWR-104` (595/600kg) | 595 + 20 = 615 > 600. |
| **Regional height limit (DXB-North)** | `... at a height of 50 meters on TWR-101` | 50m > DXB-North's 45m cap. |
| **Single-asset weight (SHJ-Coastal)** | `30kg antenna ... on TWR-102` | 30kg > SHJ-Coastal's 25kg/asset cap. |
| **Single-asset weight (SHJ-South)** | `20kg antenna ... on TWR-103` | 20kg > SHJ-South's 15kg/asset cap. |

> The full, real output for the demo cases lives in
> [`sample_outputs.txt`](sample_outputs.txt) — generated by running `python3 main.py`.

---

## Input flexibility

The same facts are extracted **even when the sentence structure or word order
changes**. Instead of assuming one fixed sentence shape, operator and equipment
are each matched against several ordered patterns (first confident match wins),
while tower / weight / height are matched position-independently anywhere in the
text. All five styles below extract the **identical** structured fields:

| # | Prompt style | Example |
|:-:|--------------|---------|
| 1 | Original assignment style | `Operator Du wants to mount a 15kg 5G antenna at a height of 40 meters on Tower TWR-101.` |
| 2 | Reordered (tower stated first) | `Tower TWR-101 request: Operator Du wants to install a 15kg 5G antenna at 40m.` |
| 3 | Label / comma form | `Operator: Du, Tower: TWR-101, Equipment: 5G antenna, Weight: 15kg, Height: 40 meters.` |
| 4 | Split across two sentences | `Du wants to place a 5G antenna on Tower TWR-101. The equipment weighs 15kg and will be installed at 40m.` |
| 5 | "<Operator> requests ..." wording | `Etisalat requests approval for a 20kg radio unit at 30 meters on TWR-104.` |

**Field-level forms it accepts:**

| Field | Accepted forms |
|-------|----------------|
| Operator | `Operator Du`, `Operator: Du`, `Du wants ...`, `Etisalat requests ...` |
| Equipment | `Equipment: 5G antenna`, `15kg 5G antenna`, `5G antenna weighing 15kg`, `place a 5G antenna`, `mount a 15kg 5G antenna`, `install a 20kg radio unit` |
| Weight | `15kg`, `15 kg`, `15KG`, `15.5kg` (decimals kept as floats) |
| Height | `40 meters`, `40 meter`, `40m`, `40 m`, `40.5m` |
| Tower ID | `TWR-101` or lowercase `twr-101` (normalized to uppercase) |

Whole numbers stay `int` (e.g. `15`); decimals stay `float` (e.g. `15.5`).

> **Equipment is optional.** If the equipment type can't be read confidently it
> stays `null` and the request is **not** rejected for that alone. A request is
> only rejected at the parse stage when the **tower ID, weight, or height** is
> missing.

---

## Built to scale (5 towers or 100,000)

This project ships with **120 towers**, but the real point is that the *code*
scales:

- Towers are loaded into a **dictionary keyed by `tower_id`**, so looking up any
  tower is **instant — O(1)** — it never loops through the whole list.
- Add 10 towers or 100,000; lookup speed doesn't change.
- The inventory is validated so every tower has `current_weight_kg <=
  max_allowed_weight_kg`.

---

## Tests

Fifteen `unittest` cases cover the success path, every rejection path, and the
flexible sentence shapes:

```bash
python3 -m unittest test_agent.py
```

| Test | Verifies |
|------|----------|
| `test_standard_approved_case` | The assignment's headline approved case. |
| `test_tower_not_found` | Unknown tower is rejected. |
| `test_weight_capacity_exceeded` | Over-capacity is rejected; later checks `NOT_RUN`. |
| `test_regional_height_exceeded` | Height over the regional cap is rejected. |
| `test_regional_single_asset_weight_exceeded` | SHJ-Coastal 25kg/asset cap enforced. |
| `test_missing_height_rejected` | Missing height fails `request_parse_check`. |
| `test_lowercase_tower_id` | `twr-101` is normalized and still works. |
| `test_extraction_variants` | Spacing and decimal parsing (`15.5 kg`, `40m`). |
| `test_format_reordered_sentence` | Tower-first reordered sentence (format 2). |
| `test_format_label_based` | Comma-separated label form (format 3). |
| `test_format_natural_split_sentence` | Facts split across two sentences (format 4). |
| `test_format_operator_requests_wording` | "`Etisalat requests ...`", bare tower ID (format 5). |
| `test_equipment_weighing_form` | "`5G antenna weighing 15kg`" wording. |
| `test_equipment_stops_before_trailing_measurement` | Equipment doesn't swallow a trailing height (`sensor 35m up` → `sensor`). |
| `test_missing_equipment_still_approved` | Null equipment alone does not reject. |

The tests pass controlled fixtures into the agent, so they check the **logic**
and never break just because the inventory file changes.

---

## Assumptions

- **Flexible but bounded sentence shapes.** The extractor handles several
  common phrasings (see [Input flexibility](#input-flexibility)) — reordered,
  label, split, and "<operator> requests" forms — not just the original
  template. It is still regex-based, so a wildly different phrasing may not
  parse; in that case, if a key fact (tower / weight / height) can't be read,
  the agent **safely rejects** (via `request_parse_check`) rather than guessing.
- **Region names match** between the JSON (`DXB-North`) and the policy file
  (`DXB-North Zone:`).
- **A region with no policy on file** simply has no extra restriction — the
  relevant check is reported as `NOT_APPLICABLE`.
- **Inventory is read-only.** An approval *reports* the projected final weight
  but doesn't write it back to the JSON — persisting state would be the natural
  next step.

---

## Tech

| | |
|---|---|
| **Language** | Python 3.8+ (standard library only — `re`, `json`, `os`, `sys`, `unittest`) |
| **Extraction** | Rule-based regular expressions (deterministic, no LLM) |
| **Data** | JSON tower database + TXT regional policies |
| **Output** | Structured JSON |
| **Tests** | `unittest`, 15 cases, zero dependencies |

<div align="center">

---

*Built as a backend internship assignment.*

</div>
