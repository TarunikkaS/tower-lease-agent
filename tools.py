"""
tools.py
--------

This file holds the "tools" the agent uses to talk to the outside world:

  1. Loading the tower inventory (a JSON database).
  2. Loading and parsing the regional municipality policies (a TXT file).
  3. Looking up a single tower by its ID.

Keeping these helpers separate from the decision logic (agent.py) means:
  - The agent does not care WHERE the data comes from.
  - We could later swap the JSON file for a real database, or the TXT file
    for an API, and the agent code would not change at all.

Everything here uses only the Python standard library.
"""

import json
import os
import re


# We build absolute file paths based on THIS file's location.
# This way the program works no matter which folder you run it from.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TOWERS_FILE = os.path.join(BASE_DIR, "towers_inventory.json")
POLICIES_FILE = os.path.join(BASE_DIR, "regional_policies.txt")


def load_towers(file_path=TOWERS_FILE):
    """
    Read the tower inventory JSON file and return it as a Python dictionary
    keyed by tower_id, for example:

        {
            "TWR-101": {"tower_id": "TWR-101", "region": "DXB-North", ...},
            "TWR-102": {...},
        }

    Why a dictionary keyed by tower_id?
      - Looking up a tower becomes an instant O(1) operation.
      - This is what lets the project scale to 100+ (or 100,000+) towers
        without slowing down, because we never loop through the whole list
        to find one tower.
    """
    with open(file_path, "r", encoding="utf-8") as f:
        towers_list = json.load(f)

    # Convert the list from the file into a fast lookup dictionary.
    towers_by_id = {tower["tower_id"]: tower for tower in towers_list}
    return towers_by_id


def load_policies(file_path=POLICIES_FILE):
    """
    Read the regional policies TXT file and turn each line into structured
    rules the agent can actually check.

    Each line in the file looks like one of these:

        DXB-North Zone: Maximum equipment height allowed on any structure is 45 meters.
        SHJ-Coastal Zone: ... no single tenant asset may exceed 25kg.

    We return a dictionary keyed by region name, for example:

        {
            "DXB-North":   {"max_height_m": 45,  "max_single_asset_weight_kg": None},
            "SHJ-South":   {"max_height_m": None, "max_single_asset_weight_kg": 15},
            "SHJ-Coastal": {"max_height_m": None, "max_single_asset_weight_kg": 25},
        }

    A region may have a height rule, a single-asset weight rule, or both.
    Missing rules are stored as None so the agent knows "no limit here".
    """
    policies = {}

    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue  # skip blank lines

            # The region name is everything before the word "Zone:".
            # Example: "DXB-North Zone: ..." -> region = "DXB-North"
            region_match = re.match(r"^(.*?)\s+Zone:", line)
            if not region_match:
                continue  # a line we don't understand -> ignore it safely
            region = region_match.group(1).strip()

            # Start with "no limits", then fill in whatever the line mentions.
            rule = {"max_height_m": None, "max_single_asset_weight_kg": None}

            # Look for a height limit, e.g. "... is 45 meters."
            height_match = re.search(r"(\d+)\s*meters", line)
            if height_match:
                rule["max_height_m"] = int(height_match.group(1))

            # Look for a single-asset weight limit, e.g. "may not exceed 25kg".
            weight_match = re.search(r"exceed\s*(\d+)\s*kg", line)
            if weight_match:
                rule["max_single_asset_weight_kg"] = int(weight_match.group(1))

            policies[region] = rule

    return policies


def find_tower(tower_id, towers_by_id):
    """
    Return the tower record for the given tower_id, or None if it does not
    exist. Because towers_by_id is a dictionary, this lookup is instant
    even with thousands of towers.
    """
    return towers_by_id.get(tower_id)
