"""
main.py
-------

This is the entry point you actually run. It feeds lease requests into the
agent and prints the structured JSON judgment.

Two ways to use it:

  1. No arguments -> runs a built-in set of demo requests that show both
     APPROVED and REJECTED cases:

         python main.py

  2. Your own request as a command-line argument:

         python main.py "Operator Du wants to mount a 15kg 5G antenna at a height of 40 meters on Tower TWR-101."
"""

import json
import sys

from agent import evaluate_request


# A handful of demo requests that exercise every code path:
#   - the happy path (APPROVED)
#   - tower not found
#   - tower weight capacity exceeded
#   - regional height limit exceeded
#   - regional single-asset weight limit exceeded
DEMO_REQUESTS = [
    # APPROVED: 460 + 15 = 475 <= 500, height 40 <= 45.
    "Operator Du wants to mount a 15kg 5G antenna at a height of 40 meters on Tower TWR-101.",

    # REJECTED: tower does not exist in the inventory.
    "Operator Etisalat wants to mount a 10kg radio at a height of 20 meters on Tower TWR-999.",

    # REJECTED: 595 + 20 = 615 > 600 (tower weight capacity exceeded).
    "Operator Du wants to mount a 20kg dish at a height of 30 meters on Tower TWR-104.",

    # REJECTED: height 50 > 45 (DXB-North regional height limit).
    "Operator Du wants to mount a 5kg sensor at a height of 50 meters on Tower TWR-101.",

    # REJECTED: 30kg > 25kg single-asset limit in SHJ-Coastal.
    "Operator Du wants to mount a 30kg 5G antenna at a height of 15 meters on Tower TWR-102.",

    # REJECTED: 20kg > 15kg single-asset limit in SHJ-South.
    "Operator Du wants to mount a 20kg 5G antenna at a height of 30 meters on Tower TWR-103.",

    # REJECTED: no height in the sentence, so the request cannot be parsed.
    "Operator Du wants to mount a 15kg 5G antenna on Tower TWR-101.",
]


def run_and_print(request_text):
    """Evaluate one request and print it as nicely-formatted JSON."""
    judgment = evaluate_request(request_text)
    print("INPUT:")
    print(f"  {request_text}")
    print("OUTPUT:")
    # indent=2 makes the JSON readable; it is still valid JSON.
    print(json.dumps(judgment, indent=2))
    print("-" * 70)


def main():
    # If the user passed their own request, evaluate just that one.
    if len(sys.argv) > 1:
        request_text = sys.argv[1]
        run_and_print(request_text)
        return

    # Otherwise, run all the built-in demo requests.
    for request_text in DEMO_REQUESTS:
        run_and_print(request_text)


if __name__ == "__main__":
    main()
