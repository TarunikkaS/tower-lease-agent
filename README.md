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
![Status](https://img.shields.io/badge/status-working-brightgreen?style=flat-square)

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

---

## How it works

| Step | Job | Lives in |
|:----:|-----|----------|
| 1 | **Read** the plain-text request | `main.py` |
| 2 | **Extract** operator, tower, equipment, weight, height (regex) | `agent.py` |
| 3 | **Cross-reference** the tower DB + regional policies | `tools.py` |
| 4 | **Judge** -> APPROVED / REJECTED + reason + rule checks | `agent.py` |

---

## Project structure

```
tower-lease-agent/
|
|-- main.py                 # Entry point   - feeds requests in, prints JSON out
|-- agent.py                # The brain     - regex extraction + decision rules
|-- tools.py                # Data layer    - loads the JSON DB + the policies TXT
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

```bash
# Run all built-in demo cases (1 approved + 4 rejected)
python3 main.py

# Or judge your own request - just write a sentence in quotes
python3 main.py "Operator Du wants to mount a 15kg 5G antenna at a height of 40 meters on Tower TWR-101."
```

---

## The rules it enforces

The agent checks rules **in order and stops at the first failure** — just like a
careful human reviewer.

```
  request --> [ 1. tower exists? ] --no--> REJECTED
                     |
                    yes
                     v
              [ 2. weight capacity? ] --no--> REJECTED
                     |
                    yes
                     v
              [ 3. regional height? ] --no--> REJECTED
                     |
                    yes
                     v
           [ 4. regional asset weight? ] --no--> REJECTED
                     |
                    yes
                     v
                  APPROVED  (+ final_tower_weight_kg)
```

| # | Check | Rule |
|:-:|-------|------|
| 1 | **Tower exists** | The tower ID must be in `towers_inventory.json`. |
| 2 | **Weight capacity** | `current_weight + requested_weight <= max_allowed_weight` |
| 3 | **Regional height** | Requested height <= the region's height limit (if any). |
| 4 | **Regional asset weight** | A single asset <= the region's per-asset limit (if any). |

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
    "tower_exists": true,
    "weight_capacity_check": "PASSED",
    "regional_policy_check": "PASSED"
  },
  "reason": "Request approved. The tower has enough remaining capacity and the requested height follows the DXB-North regional policy.",
  "final_tower_weight_kg": 475
}
```

## Example: every rejection path

| Scenario | Example request | Why it's rejected |
|----------|-----------------|-------------------|
| **Tower not found** | `... on Tower TWR-999.` | TWR-999 isn't in the inventory. |
| **Weight capacity exceeded** | `20kg dish ... on TWR-104` (595/600kg) | 595 + 20 = 615 > 600. |
| **Regional height limit** | `... at a height of 50 meters on TWR-101` | 50m > DXB-North's 45m cap. |
| **Single-asset weight limit** | `30kg antenna ... on TWR-102` | 30kg > SHJ-Coastal's 25kg/asset cap. |

> The full, real output for all of these lives in
> [`sample_outputs.txt`](sample_outputs.txt) — generated by running `python3 main.py`.

---

## Built to scale (5 towers or 100,000)

The assignment ships with sample towers; this project includes **120**. The real
point is that the *code* scales:

- Towers are loaded into a **dictionary keyed by `tower_id`**, so looking up any
  tower is **instant — O(1)** — it never loops through the whole list.
- Add 10 towers or 100,000; lookup speed doesn't change.

---

## Assumptions

- **Predictable sentence shape.** Requests roughly follow
  *"Operator X wants to mount a Nkg \<equipment\> at a height of M meters on Tower TWR-###."*
  That's what the regex targets. Very different phrasing may not extract cleanly —
  in which case the agent **safely rejects** rather than guessing.
- **Whole-number** kg and meters (e.g. `15kg`, `40 meters`).
- **Tower IDs** look like `TWR-101` (capitals, dash, digits); the lookup itself
  works for any ID string.
- **Region names match** between the JSON (`DXB-North`) and the policy file
  (`DXB-North Zone:`).
- **A region with no policy on file** simply has no extra restriction.
- **Inventory is read-only.** An approval *reports* the projected final weight but
  doesn't write it back to the JSON — persisting state would be the natural next step.

---

## Tech

| | |
|---|---|
| **Language** | Python 3 (standard library only — `re`, `json`, `os`, `sys`) |
| **Extraction** | Rule-based regular expressions |
| **Data** | JSON tower database + TXT regional policies |
| **Output** | Structured JSON |

<div align="center">

---

*Built as a backend internship assignment.*

</div>
