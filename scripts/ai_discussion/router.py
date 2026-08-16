#!/usr/bin/env python3
"""Select the first AI speaker for an AI discussion run."""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


ROUTING_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "first_mover": {"type": "string", "enum": ["chatgpt", "claude"]},
        "reason": {"type": "string", "minLength": 1},
        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
    },
    "required": ["first_mover", "reason", "confidence"],
    "additionalProperties": False,
}


class ConfigurationError(ValueError):
    """Raised when required non-secret configuration is missing or invalid."""


def required_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise ConfigurationError(f"Required environment variable {name} is not set")
    return value


def positive_int_env(name: str) -> int:
    raw = required_env(name)
    try:
        value = int(raw)
    except ValueError as exc:
        raise ConfigurationError(f"{name} must be an integer") from exc
    if value <= 0:
        raise ConfigurationError(f"{name} must be greater than zero")
    return value


def nonnegative_float_env(name: str) -> float:
    raw = required_env(name)
    try:
        value = float(raw)
    except ValueError as exc:
        raise ConfigurationError(f"{name} must be numeric") from exc
    if value < 0:
        raise ConfigurationError(f"{name} must not be negative")
    return value


def extract_openai_text(response: dict[str, Any]) -> str:
    for item in response.get("output", []):
        if item.get("type") != "message":
            continue
        for content in item.get("content", []):
            if content.get("type") == "output_text" and content.get("text"):
                return str(content["text"])
    raise RuntimeError("OpenAI response did not contain output_text")


def post_json(url: str, payload: dict[str, Any], headers: dict[str, str]) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json", **headers},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            return json.load(response)
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:2000]
        raise RuntimeError(f"OpenAI API returned HTTP {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"OpenAI API request failed: {exc.reason}") from exc


def validate_routing(value: dict[str, Any]) -> dict[str, Any]:
    first_mover = value.get("first_mover")
    reason = value.get("reason")
    confidence = value.get("confidence")
    if first_mover not in {"chatgpt", "claude"}:
        raise RuntimeError("Router returned an invalid first_mover")
    if not isinstance(reason, str) or not reason.strip():
        raise RuntimeError("Router returned an empty reason")
    if not isinstance(confidence, (int, float)) or not 0 <= float(confidence) <= 1:
        raise RuntimeError("Router returned an invalid confidence")
    return {
        "first_mover": first_mover,
        "reason": reason.strip(),
        "confidence": float(confidence),
    }


def route_topic(topic: str, force_first_mover: str = "auto") -> dict[str, Any]:
    topic = topic.strip()
    if not topic:
        raise ValueError("topic must not be empty")
    if force_first_mover not in {"auto", "chatgpt", "claude"}:
        raise ValueError("force_first_mover must be auto, chatgpt, or claude")

    if force_first_mover != "auto":
        return {
            "first_mover": force_first_mover,
            "reason": "CEO-specified force_first_mover override",
            "confidence": 1.0,
            "forced": True,
            "model": None,
            "usage": {"input_tokens": 0, "output_tokens": 0},
            "api_calls": 0,
            "estimated_cost_usd": 0.0,
        }

    model = required_env("ROUTER_MODEL")
    max_output_tokens = positive_int_env("MAX_OUTPUT_TOKENS")
    api_key = required_env("OPENAI_API_KEY")
    input_rate = nonnegative_float_env("ROUTER_INPUT_USD_PER_MTOK")
    output_rate = nonnegative_float_env("ROUTER_OUTPUT_USD_PER_MTOK")
    payload = {
        "model": model,
        "instructions": (
            "You route a two-model decision discussion. Select which model should make the "
            "initial proposal. Do not use a rigid keyword rule. Consider whether the topic "
            "benefits more from broad ideation or from constraint-first technical analysis, "
            "and return only the requested JSON."
        ),
        "input": topic,
        "max_output_tokens": max_output_tokens,
        "text": {
            "format": {
                "type": "json_schema",
                "name": "ai_discussion_routing",
                "strict": True,
                "schema": ROUTING_SCHEMA,
            }
        },
    }
    response = post_json(
        "https://api.openai.com/v1/responses",
        payload,
        {"Authorization": f"Bearer {api_key}"},
    )
    try:
        parsed = json.loads(extract_openai_text(response))
    except json.JSONDecodeError as exc:
        raise RuntimeError("Router returned invalid JSON") from exc
    result = validate_routing(parsed)
    usage = response.get("usage") or {}
    input_tokens = int(usage.get("input_tokens") or 0)
    output_tokens = int(usage.get("output_tokens") or 0)
    estimated_cost = (input_tokens * input_rate + output_tokens * output_rate) / 1_000_000
    result.update(
        {
            "forced": False,
            "model": model,
            "usage": {"input_tokens": input_tokens, "output_tokens": output_tokens},
            "api_calls": 1,
            "estimated_cost_usd": round(estimated_cost, 8),
        }
    )
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--topic", required=True)
    parser.add_argument(
        "--force-first-mover",
        default="auto",
        choices=("auto", "chatgpt", "claude"),
    )
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    try:
        result = route_topic(args.topic, args.force_first_mover)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    except (ConfigurationError, RuntimeError, ValueError) as exc:
        print(f"router error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
