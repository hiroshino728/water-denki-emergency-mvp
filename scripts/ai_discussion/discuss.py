#!/usr/bin/env python3
"""Run an alternating Claude/OpenAI discussion with per-round convergence checks."""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Callable


CLASSIFICATIONS = [
    "implementation_task",
    "unresolved",
    "business_decision",
    "architecture_decision",
    "specification_change",
]

ROUND_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "status": {"type": "string", "enum": ["converged", "unresolved"]},
        "position": {"type": "string"},
        "agreements": {"type": "array", "items": {"type": "string"}},
        "unresolved_points": {"type": "array", "items": {"type": "string"}},
        "proposed_synthesis": {"type": ["string", "null"]},
        "decision_classification": {"type": "string", "enum": CLASSIFICATIONS},
        "classification_reason": {"type": "string"},
        "objective": {"type": "string"},
        "scope": {"type": "array", "items": {"type": "string"}},
        "acceptance_criteria": {"type": "array", "items": {"type": "string"}},
        "test_cases": {"type": "array", "items": {"type": "string"}},
    },
    "required": [
        "status",
        "position",
        "agreements",
        "unresolved_points",
        "proposed_synthesis",
        "decision_classification",
        "classification_reason",
        "objective",
        "scope",
        "acceptance_criteria",
        "test_cases",
    ],
    "additionalProperties": False,
}


class ConfigurationError(ValueError):
    """Raised when runtime configuration is missing or invalid."""


def required_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise ConfigurationError(f"Required environment variable {name} is not set")
    return value


def int_env(name: str, *, minimum: int = 1, maximum: int | None = None) -> int:
    raw = required_env(name)
    try:
        value = int(raw)
    except ValueError as exc:
        raise ConfigurationError(f"{name} must be an integer") from exc
    if value < minimum or (maximum is not None and value > maximum):
        suffix = f" and at most {maximum}" if maximum is not None else ""
        raise ConfigurationError(f"{name} must be at least {minimum}{suffix}")
    return value


def rate_env(name: str) -> float:
    raw = required_env(name)
    try:
        value = float(raw)
    except ValueError as exc:
        raise ConfigurationError(f"{name} must be numeric") from exc
    if value < 0:
        raise ConfigurationError(f"{name} must not be negative")
    return value


def post_json(url: str, payload: dict[str, Any], headers: dict[str, str]) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json", **headers},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=180) as response:
            return json.load(response)
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:2000]
        raise RuntimeError(f"Model API returned HTTP {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Model API request failed: {exc.reason}") from exc


def extract_openai_text(response: dict[str, Any]) -> str:
    for item in response.get("output", []):
        if item.get("type") != "message":
            continue
        for content in item.get("content", []):
            if content.get("type") == "output_text" and content.get("text"):
                return str(content["text"])
    raise RuntimeError("OpenAI response did not contain output_text")


def extract_anthropic_text(response: dict[str, Any]) -> str:
    texts = [
        str(block["text"])
        for block in response.get("content", [])
        if block.get("type") == "text" and block.get("text")
    ]
    if not texts:
        raise RuntimeError("Anthropic response did not contain a text block")
    return "\n".join(texts)


def parse_json_text(text: str) -> dict[str, Any]:
    text = text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    try:
        value = json.loads(text)
    except json.JSONDecodeError as exc:
        raise RuntimeError("Discussion model returned invalid JSON") from exc
    if not isinstance(value, dict):
        raise RuntimeError("Discussion model returned a non-object JSON value")
    return value


def validate_round(value: dict[str, Any], round_number: int) -> dict[str, Any]:
    required = set(ROUND_SCHEMA["required"])
    if set(value) != required:
        missing = sorted(required - set(value))
        extra = sorted(set(value) - required)
        raise RuntimeError(f"Round JSON has missing={missing} extra={extra}")
    if value["status"] not in {"converged", "unresolved"}:
        raise RuntimeError("Round JSON has invalid status")
    if value["decision_classification"] not in CLASSIFICATIONS:
        raise RuntimeError("Round JSON has invalid decision_classification")
    for field in ("position", "classification_reason", "objective"):
        if not isinstance(value[field], str) or not value[field].strip():
            raise RuntimeError(f"Round JSON has invalid {field}")
        value[field] = value[field].strip()
    for field in ("agreements", "unresolved_points", "scope", "acceptance_criteria", "test_cases"):
        if not isinstance(value[field], list) or not all(isinstance(item, str) for item in value[field]):
            raise RuntimeError(f"Round JSON has invalid {field}")
        value[field] = [item.strip() for item in value[field] if item.strip()]

    # A single opening statement cannot establish agreement between two models.
    if round_number == 1:
        value["status"] = "unresolved"
        value["proposed_synthesis"] = None
    # A model cannot claim convergence while leaving the downstream decision
    # path unresolved. Preserve the paid result as an unresolved round instead
    # of failing the pipeline in classify.py.
    if value["status"] == "converged" and value["decision_classification"] == "unresolved":
        value["status"] = "unresolved"
        value["proposed_synthesis"] = None
    # Structured output guarantees the field exists, but it deliberately allows
    # null for unresolved rounds. If a model combines converged with an empty
    # synthesis, keep the paid response as unresolved instead of aborting the run.
    if value["status"] == "converged" and (
        not isinstance(value["proposed_synthesis"], str)
        or not value["proposed_synthesis"].strip()
    ):
        value["status"] = "unresolved"
        value["proposed_synthesis"] = None
    if value["status"] == "converged" and value["unresolved_points"]:
        value["status"] = "unresolved"
        value["proposed_synthesis"] = None
    if value["status"] == "converged":
        value["proposed_synthesis"] = value["proposed_synthesis"].strip()
    else:
        value["proposed_synthesis"] = None
        if not value["unresolved_points"]:
            value["unresolved_points"] = ["相手AIによる検証または追加討議が必要"]
    return value


def build_prompt(topic: str, history: list[dict[str, Any]], speaker: str, round_number: int, max_rounds: int) -> str:
    prior = json.dumps(history, ensure_ascii=False, indent=2) if history else "[]"
    return f"""議題: {topic}

あなたは {speaker} として、ClaudeとChatGPTの交互討議の第{round_number}/{max_rounds}ラウンドを担当します。
過去ラウンド:
{prior}

役割:
- 第1ラウンドは初案を提示し、statusは必ずunresolvedとする。
- 第2ラウンド以降は直前までの主張を具体的に批評し、合意点と未解決点を更新する。
- 重要な対立がすべて解消した場合だけconvergedとし、統合案をproposed_synthesisへ記載する。
- unresolvedでは統合案を作らず、未解決点をunresolved_pointsへ両論が分かる形で残す。
- DecisionはAIが確定しない。decision_classificationはCEO承認後の処理経路を示す候補分類にすぎない。
- 実装タスクなら、後続Issueに使えるobjective/scope/acceptance_criteria/test_casesを具体化する。

指定されたJSON Schemaに厳密に従って返答してください。"""


def call_openai(prompt: str, model: str, max_output_tokens: int, api_key: str) -> tuple[dict[str, Any], dict[str, int]]:
    response = post_json(
        "https://api.openai.com/v1/responses",
        {
            "model": model,
            "instructions": "Act as the ChatGPT participant in a structured decision discussion.",
            "input": prompt,
            "max_output_tokens": max_output_tokens,
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": "ai_discussion_round",
                    "strict": True,
                    "schema": ROUND_SCHEMA,
                }
            },
        },
        {"Authorization": f"Bearer {api_key}"},
    )
    usage = response.get("usage") or {}
    return parse_json_text(extract_openai_text(response)), {
        "input_tokens": int(usage.get("input_tokens") or 0),
        "output_tokens": int(usage.get("output_tokens") or 0),
    }


def call_anthropic(prompt: str, model: str, max_output_tokens: int, api_key: str) -> tuple[dict[str, Any], dict[str, int]]:
    response = post_json(
        "https://api.anthropic.com/v1/messages",
        {
            "model": model,
            "max_tokens": max_output_tokens,
            "system": "Act as the Claude participant in a structured decision discussion.",
            "messages": [{"role": "user", "content": prompt}],
            "output_config": {"format": {"type": "json_schema", "schema": ROUND_SCHEMA}},
        },
        {"x-api-key": api_key, "anthropic-version": "2023-06-01"},
    )
    usage = response.get("usage") or {}
    return parse_json_text(extract_anthropic_text(response)), {
        "input_tokens": int(usage.get("input_tokens") or 0),
        "output_tokens": int(usage.get("output_tokens") or 0),
    }


def run_discussion(
    topic: str,
    routing: dict[str, Any],
    callers: dict[str, Callable[[str, str, int, str], tuple[dict[str, Any], dict[str, int]]]] | None = None,
) -> dict[str, Any]:
    first_mover = routing.get("first_mover")
    if first_mover not in {"chatgpt", "claude"}:
        raise ValueError("routing.first_mover is invalid")
    # One round is one model response (and therefore one API call). At least two
    # rounds are required so both models participate in the first exchange.
    max_rounds = int_env("MAX_ROUNDS", minimum=2, maximum=10)
    max_output_tokens = int_env("MAX_OUTPUT_TOKENS", minimum=1)
    models = {
        "chatgpt": required_env("OPENAI_DISCUSSION_MODEL"),
        "claude": required_env("ANTHROPIC_DISCUSSION_MODEL"),
    }
    keys = {
        "chatgpt": required_env("OPENAI_API_KEY"),
        "claude": required_env("ANTHROPIC_API_KEY"),
    }
    rates = {
        "chatgpt": (
            rate_env("OPENAI_DISCUSSION_INPUT_USD_PER_MTOK"),
            rate_env("OPENAI_DISCUSSION_OUTPUT_USD_PER_MTOK"),
        ),
        "claude": (
            rate_env("ANTHROPIC_DISCUSSION_INPUT_USD_PER_MTOK"),
            rate_env("ANTHROPIC_DISCUSSION_OUTPUT_USD_PER_MTOK"),
        ),
    }
    callers = callers or {"chatgpt": call_openai, "claude": call_anthropic}
    order = [first_mover, "claude" if first_mover == "chatgpt" else "chatgpt"]
    rounds: list[dict[str, Any]] = []
    call_records: list[dict[str, Any]] = []

    for index in range(max_rounds):
        round_number = index + 1
        speaker = order[index % 2]
        prompt = build_prompt(topic, rounds, speaker, round_number, max_rounds)
        value, usage = callers[speaker](prompt, models[speaker], max_output_tokens, keys[speaker])
        value = validate_round(value, round_number)
        round_record = {"round": round_number, "speaker": speaker, **value}
        rounds.append(round_record)
        input_rate, output_rate = rates[speaker]
        cost = (
            int(usage.get("input_tokens", 0)) * input_rate
            + int(usage.get("output_tokens", 0)) * output_rate
        ) / 1_000_000
        call_records.append(
            {
                "provider": "openai" if speaker == "chatgpt" else "anthropic",
                "speaker": speaker,
                "model": models[speaker],
                "input_tokens": int(usage.get("input_tokens", 0)),
                "output_tokens": int(usage.get("output_tokens", 0)),
                "estimated_cost_usd": round(cost, 8),
            }
        )
        if value["status"] == "converged":
            break

    status = rounds[-1]["status"]
    unresolved_points: list[str] = []
    if status == "unresolved":
        seen: set[str] = set()
        for round_record in rounds:
            for point in round_record["unresolved_points"]:
                if point not in seen:
                    seen.add(point)
                    unresolved_points.append(point)
    return {
        "topic": topic.strip(),
        "first_mover": first_mover,
        "status": status,
        "rounds_completed": len(rounds),
        "max_rounds": max_rounds,
        "rounds": rounds,
        "unresolved_points": unresolved_points,
        "calls": call_records,
        "api_calls": len(call_records),
        "estimated_cost_usd": round(sum(item["estimated_cost_usd"] for item in call_records), 8),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--topic", required=True)
    parser.add_argument("--routing", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    try:
        routing = json.loads(args.routing.read_text())
        result = run_discussion(args.topic, routing)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    except (ConfigurationError, OSError, RuntimeError, ValueError, json.JSONDecodeError) as exc:
        print(f"discussion error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
