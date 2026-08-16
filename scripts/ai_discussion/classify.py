#!/usr/bin/env python3
"""Normalize the final Decision Classification from a discussion record."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


CLASSIFICATIONS = {
    "implementation_task",
    "unresolved",
    "business_decision",
    "architecture_decision",
    "specification_change",
}


def classify_discussion(discussion: dict[str, Any]) -> dict[str, Any]:
    rounds = discussion.get("rounds")
    if not isinstance(rounds, list) or not rounds:
        raise ValueError("discussion must contain at least one round")
    final = rounds[-1]
    status = discussion.get("status")
    if status not in {"converged", "unresolved"}:
        raise ValueError("discussion status is invalid")

    if status == "unresolved":
        classification = "unresolved"
        reason = "最大ラウンド内で重要な対立点が解消されなかったため"
    else:
        classification = final.get("decision_classification")
        reason = final.get("classification_reason")
        if classification not in CLASSIFICATIONS - {"unresolved"}:
            raise ValueError("converged discussion has an invalid classification")
        if not isinstance(reason, str) or not reason.strip():
            raise ValueError("classification_reason is missing")

    return {
        "classification": classification,
        "reason": reason,
        "discussion_status": status,
        "objective": final.get("objective", ""),
        "scope": final.get("scope", []),
        "acceptance_criteria": final.get("acceptance_criteria", []),
        "test_cases": final.get("test_cases", []),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--discussion", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    try:
        discussion = json.loads(args.discussion.read_text())
        result = classify_discussion(discussion)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"classification error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
