"""
agent.py
--------

This is the "brain" of the project. It does two things:

  1. EXTRACTION  -> read a plain-text lease request and pull out the
                    structured details (operator, tower, equipment, weight,
                    height) using simple regular expressions.

  2. JUDGMENT    -> cross-reference those details against the tower
                    inventory (JSON) and the regional policies (TXT), then
                    return APPROVED or REJECTED with a clear reason.

The agent intentionally keeps EXTRACTION and JUDGMENT as separate steps,
just like a human would: first understand the request, then decide on it.

Note: this is a lightweight, deterministic "AI-style" agent. The extraction
is rule-based regex (no LLM, no external libraries) and the decision is made
by fixed business rules, so the same input always gives the same output.
"""

import re

from tools import load_towers, load_policies, find_tower


def _parse_number(raw):
    """
    Turn a captured number string into the right Python type:
      - "15"   -> 15    (int, because it is a whole number)
      - "15.5" -> 15.5  (float, because it has a decimal part)

    Keeping whole numbers as int makes the JSON output cleaner (15, not 15.0).
    """
    value = float(raw)
    if value.is_integer():
        return int(value)
    return value


# ---------------------------------------------------------------------------
# STEP 1: EXTRACTION
# ---------------------------------------------------------------------------
def _extract_operator(text):
    """
    Find the operator name across several sentence shapes:

      - label form ............ "Operator: Du"  /  "Operator Du"
      - subject form .......... "Du wants ..."  /  "Etisalat requests ..."

    The label form is tried first (it is the most explicit). The subject form
    is intentionally CASE-SENSITIVE: it only accepts a Capitalized word so we
    pick up a proper operator name ("Du", "Etisalat") and never a lowercase
    filler word like "the" in a phrase such as "the request requires ...".
    """
    # "Operator: Du" or "Operator Du" (the colon is optional).
    label = re.search(r"Operator\b\s*:?\s*([A-Za-z0-9&\-]+)", text, re.IGNORECASE)
    if label:
        return label.group(1)

    # "Du wants ...", "Etisalat requests ...", "Du needs ...", etc.
    subject = re.search(
        r"\b([A-Z][A-Za-z&]+)\s+"
        r"(?:wants|requests?|requires|needs|seeks|would\s+like"
        r"|is\s+requesting|is\s+seeking)\b",
        text,
    )
    if subject:
        return subject.group(1)

    return None


# Where an equipment phrase ends: the next structural word ("at", "on",
# "weighing", "that", "which"), a stray numeric measurement ("35m", "15kg" — so
# we don't swallow a height/weight that trails the equipment), or a piece of
# punctuation / end of string. Used as a lookahead so the phrase is not consumed.
# A measurement needs a UNIT after the number, so equipment like "5G antenna"
# (where "5" is not followed by a unit) is left intact.
_EQUIP_END = (
    r"(?=\s+at\b|\s+on\b|\s+weighing\b|\s+that\b|\s+which\b"
    r"|\s+\d+(?:\.\d+)?\s*(?:kg|meters|metres|meter|metre|m)\b"
    r"|[.,;]|$)"
)


def _extract_equipment(text):
    """
    Find the equipment description across several sentence shapes. Each pattern
    is tried in order and the first confident match wins:

      1. label form ........... "Equipment: 5G antenna"
      2. weighing form ........ "a 5G antenna weighing 15kg"
      3. verb form ............ "mount a 15kg 5G antenna", "place a 5G antenna",
                                 "install a 20kg radio unit"
      4. weight-prefix form ... "15kg 5G antenna", "20kg radio unit"

    If none match confidently the equipment stays None — that is allowed, the
    request is NOT rejected for a missing equipment type alone.
    """
    patterns = [
        # 1. Label form. The colon is required so we don't accidentally grab the
        #    bare word "equipment" in a sentence like "The equipment weighs ...".
        r"Equipment\b\s*:\s*(.+?)" + _EQUIP_END,
        # 2. "<equipment> weighing 15kg" (anchored on an article).
        r"(?:a|an|the)\s+(.+?)\s+weighing\s+\d",
        # 3. Verb + article + optional weight + equipment.
        r"(?:mount|install|place|add|fit|deploy|put|attach|erect|set\s*up)\s+"
        r"(?:a|an|the)\s+(?:\d+(?:\.\d+)?\s*kg\s+)?(.+?)" + _EQUIP_END,
        # 4. "15kg 5G antenna". The negative lookahead stops us from capturing a
        #    structural word (e.g. "15kg at 40m" must NOT yield "at 40m").
        r"\d+(?:\.\d+)?\s*kg\s+(?!at\b|on\b|in\b|to\b|of\b)(.+?)" + _EQUIP_END,
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            value = match.group(1).strip(" .,;")
            if value:
                return value
    return None


def extract_request_details(text):
    """
    Take a plain-text lease request and return a dictionary of the structured
    fields we managed to find. Any field we cannot find is set to None.

    Example input:
        "Operator Du wants to mount a 15kg 5G antenna at a height of
         40 meters on Tower TWR-101."

    Example output:
        {
            "operator": "Du",
            "tower_id": "TWR-101",
            "equipment_type": "5G antenna",
            "requested_weight_kg": 15,
            "requested_height_m": 40,
        }

    We use regex (regular expressions) because the requests follow a fairly
    predictable set of sentence patterns. Rather than assume ONE sentence shape,
    operator and equipment are extracted by trying several ordered patterns and
    taking the first confident match, so the same facts are found even when the
    word order changes (label form, reordered sentence, split sentence, ...).
    The tower / weight / height patterns stay deliberately position-independent.
    """
    details = {
        "operator": None,
        "tower_id": None,
        "equipment_type": None,
        "requested_weight_kg": None,
        "requested_height_m": None,
    }

    # --- Operator name --- (handles "Operator Du", "Operator: Du",
    # "Du wants ...", "Etisalat requests ...").
    details["operator"] = _extract_operator(text)

    # --- Tower ID ---
    # Tower IDs look like "TWR-101" (letters, a dash, then digits). We accept
    # lowercase too (e.g. "twr-101") and normalize the result to UPPERCASE so
    # it always matches the keys in the inventory. This is independent of where
    # the tower ID appears in the sentence.
    tower_match = re.search(r"\b([A-Za-z]{2,}-\d+)\b", text)
    if tower_match:
        details["tower_id"] = tower_match.group(1).upper()

    # --- Equipment weight (kg) ---
    # Matches "15kg", "15 kg", "15KG", and decimals like "15.5kg" anywhere in
    # the text (e.g. "weighs 15kg" or "a 15kg antenna").
    weight_match = re.search(r"(\d+(?:\.\d+)?)\s*kg", text, re.IGNORECASE)
    if weight_match:
        details["requested_weight_kg"] = _parse_number(weight_match.group(1))

    # --- Installation height (meters) ---
    # Matches "40 meters", "40 meter", "40m", "40 m", and decimals like "40.5m".
    # The unit alternation lists the long spellings first so "meters" wins over
    # the bare "m" when both could apply.
    height_match = re.search(
        r"(\d+(?:\.\d+)?)\s*(?:meters|metres|meter|metre|m)\b",
        text,
        re.IGNORECASE,
    )
    if height_match:
        details["requested_height_m"] = _parse_number(height_match.group(1))

    # --- Equipment type --- (handles "Equipment: 5G antenna", "15kg 5G antenna",
    # "5G antenna weighing 15kg", "place a 5G antenna", "install a 20kg radio
    # unit"). May stay None; that alone never rejects the request.
    details["equipment_type"] = _extract_equipment(text)

    return details


# ---------------------------------------------------------------------------
# STEP 2: JUDGMENT
# ---------------------------------------------------------------------------
def evaluate_request(text, towers_by_id=None, policies=None):
    """
    The main entry point. Give it a plain-text lease request and it returns
    the full structured judgment as a Python dictionary (ready to be printed
    as JSON).

    The optional towers_by_id / policies arguments let us pass data in
    directly (useful for tests). If they are not given, we load them from
    the files via tools.py.

    The "checks" object tells the full story of the decision:
      - "PASSED"          the rule was checked and satisfied
      - "FAILED"          the rule was checked and broken (causes REJECTED)
      - "NOT_APPLICABLE"  the region has no such rule, so nothing to enforce
      - "NOT_RUN"         an earlier check failed, so we never reached this one
    """
    if towers_by_id is None:
        towers_by_id = load_towers()
    if policies is None:
        policies = load_policies()

    # First, understand the request.
    details = extract_request_details(text)

    # We will fill in this result as we go and return it at the end.
    result = {
        "status": None,
        "operator": details["operator"],
        "tower_id": details["tower_id"],
        "equipment_type": details["equipment_type"],
        "requested_weight_kg": details["requested_weight_kg"],
        "requested_height_m": details["requested_height_m"],
        "region": None,
        "checks": {
            "request_parse_check": "PASSED",
            "tower_exists": False,
            "weight_capacity_check": "NOT_RUN",
            "regional_height_check": "NOT_RUN",
            "regional_single_asset_weight_check": "NOT_RUN",
        },
        "reason": None,
        "final_tower_weight_kg": None,
    }

    # -- CHECK 0: did we understand the request? --
    # We need all three key facts to make a fair decision: which tower, how
    # heavy the equipment is, and how high it will be mounted.
    if (
        details["tower_id"] is None
        or details["requested_weight_kg"] is None
        or details["requested_height_m"] is None
    ):
        result["status"] = "REJECTED"
        result["checks"]["request_parse_check"] = "FAILED"
        result["reason"] = (
            "Request rejected. Could not read the tower ID, equipment weight, "
            "and/or installation height from the text."
        )
        return result

    # -- CHECK 1: does the tower exist? --
    tower = find_tower(details["tower_id"], towers_by_id)
    if tower is None:
        result["status"] = "REJECTED"
        result["reason"] = (
            f"Request rejected. Tower {details['tower_id']} was not found "
            f"in the inventory."
        )
        return result

    # The tower exists -> record its region and mark the check as passed.
    result["checks"]["tower_exists"] = True
    result["region"] = tower["region"]

    # -- CHECK 2: weight capacity of the tower --
    # current weight + new equipment must stay within the tower's maximum.
    current = tower["current_weight_kg"]
    maximum = tower["max_allowed_weight_kg"]
    requested_weight = details["requested_weight_kg"]
    requested_height = details["requested_height_m"]
    projected_weight = current + requested_weight

    if projected_weight > maximum:
        result["status"] = "REJECTED"
        result["checks"]["weight_capacity_check"] = "FAILED"
        result["reason"] = (
            f"Request rejected. Adding {requested_weight}kg to the current "
            f"{current}kg would reach {projected_weight}kg, which exceeds "
            f"tower {tower['tower_id']}'s maximum of {maximum}kg."
        )
        return result

    result["checks"]["weight_capacity_check"] = "PASSED"

    # -- CHECK 3 & 4: regional municipality policy --
    # A region may limit (a) the installation height and/or (b) the weight of
    # any single tenant asset. We check whichever rules exist; if a rule does
    # not exist for the region we mark it NOT_APPLICABLE.
    region_policy = policies.get(tower["region"])
    max_height = region_policy["max_height_m"] if region_policy else None
    max_asset_weight = (
        region_policy["max_single_asset_weight_kg"] if region_policy else None
    )

    # (a) Regional height limit.
    if max_height is None:
        result["checks"]["regional_height_check"] = "NOT_APPLICABLE"
    elif requested_height > max_height:
        result["status"] = "REJECTED"
        result["checks"]["regional_height_check"] = "FAILED"
        result["reason"] = (
            f"Request rejected. Requested height of {requested_height} meters "
            f"exceeds the {tower['region']} regional limit of {max_height} "
            f"meters."
        )
        return result
    else:
        result["checks"]["regional_height_check"] = "PASSED"

    # (b) Regional single-asset weight limit.
    if max_asset_weight is None:
        result["checks"]["regional_single_asset_weight_check"] = "NOT_APPLICABLE"
    elif requested_weight > max_asset_weight:
        result["status"] = "REJECTED"
        result["checks"]["regional_single_asset_weight_check"] = "FAILED"
        result["reason"] = (
            f"Request rejected. A single asset of {requested_weight}kg exceeds "
            f"the {tower['region']} regional limit of {max_asset_weight}kg per "
            f"tenant asset."
        )
        return result
    else:
        result["checks"]["regional_single_asset_weight_check"] = "PASSED"

    # -- All checks passed -> APPROVED --
    result["status"] = "APPROVED"
    result["final_tower_weight_kg"] = projected_weight
    result["reason"] = (
        f"Request approved. Tower {tower['tower_id']} has enough remaining "
        f"capacity ({projected_weight}kg of {maximum}kg used) and the request "
        f"satisfies all {tower['region']} regional policies."
    )

    return result
