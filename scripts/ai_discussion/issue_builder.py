#!/usr/bin/env python3
"""Build Decision Proposal and follow-up implementation Issue payloads."""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


RECORD_START = "<!-- ai-discussion-record:start -->"
RECORD_END = "<!-- ai-discussion-record:end -->"
PROPOSAL_MARKER = "<!-- ai-discussion-proposal:v1 -->"


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text())
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def clean_title(value: str, limit: int = 220) -> str:
    value = " ".join(value.split())
    return value if len(value) <= limit else value[: limit - 1].rstrip() + "…"


def bullets(values: list[str], empty: str = "（なし）") -> str:
    cleaned = [str(value).strip() for value in values if str(value).strip()]
    return "\n".join(f"- {value}" for value in cleaned) if cleaned else empty


def checks(values: list[str], empty: str = "- [ ] CEOが具体化する") -> str:
    cleaned = [str(value).strip() for value in values if str(value).strip()]
    return "\n".join(f"- [ ] {value}" for value in cleaned) if cleaned else empty


def numbered(values: list[str], empty: str = "1. CEOが具体化する") -> str:
    cleaned = [str(value).strip() for value in values if str(value).strip()]
    return "\n".join(f"{index}. {value}" for index, value in enumerate(cleaned, 1)) if cleaned else empty


def build_proposal(
    topic: str,
    routing: dict[str, Any],
    discussion: dict[str, Any],
    classification: dict[str, Any],
) -> dict[str, Any]:
    topic = topic.strip()
    if not topic:
        raise ValueError("topic must not be empty")
    classification_name = classification.get("classification")
    if classification_name not in {
        "implementation_task",
        "unresolved",
        "business_decision",
        "architecture_decision",
        "specification_change",
    }:
        raise ValueError("classification is invalid")

    round_sections = []
    for item in discussion.get("rounds", []):
        round_sections.append(
            f"### Round {item['round']} — {item['speaker']}\n\n"
            f"**主張**\n\n{item['position']}\n\n"
            f"**合意点**\n\n{bullets(item.get('agreements', []))}\n\n"
            f"**未解決点**\n\n{bullets(item.get('unresolved_points', []))}"
        )
    final_round = discussion["rounds"][-1]
    if discussion.get("status") == "converged":
        outcome_heading = "## 統合案（CEO承認前）"
        outcome = final_round.get("proposed_synthesis") or "（統合案なし）"
    else:
        outcome_heading = "## 未解決の論点"
        outcome = bullets(discussion.get("unresolved_points", []), "- 追加討議が必要")

    record = {
        "version": 1,
        "topic": topic,
        "classification": classification,
    }
    record_json = json.dumps(record, ensure_ascii=False, indent=2)
    body = f"""{PROPOSAL_MARKER}
<!-- decision-classification:{classification_name} -->

## Meta

- blocked-by: なし
- related-docs: `docs/ai_collaboration_rules_v2.1.md`, `docs/AI_COLLABORATION.md`, `AGENTS.md`
- source: GitHub Actions AI discussion pipeline

## Objective

議題「{topic}」について、ClaudeとChatGPTの討議結果をCEOが確認し、採用・却下または追加指示を判断する。

## ルーティング

- 先攻: `{routing.get('first_mover')}`
- confidence: `{routing.get('confidence')}`
- 強制指定: `{routing.get('forced')}`
- 理由: {routing.get('reason')}

## 討議結果

- 状態: `{discussion.get('status')}`
- 実施ラウンド: `{discussion.get('rounds_completed')} / {discussion.get('max_rounds')}`

{chr(10).join(round_sections)}

{outcome_heading}

{outcome}

## Decision Classification

- 分類: `{classification_name}`
- 理由: {classification.get('reason')}

この分類は後続処理の候補であり、Decisionを確定するものではありません。Decisionを下すのは常にCEOです。

## CEO Action

- 採用: `/approve`
- 却下: `/reject`（続く行に理由を記載可能）

`unresolved`は承認できません。追加討議または直接指示を行ってください。

## Current State

CEO判断待ち。実装・設計変更は開始されていない。

## Completed

- 先攻AIの判定
- Claude / ChatGPTの交互討議と収束判定
- Decision Classification

## Remaining

- [ ] CEOによる `/approve`、`/reject`、または追加指示

## Next Action

CEOが討議結果と分類を確認する。`implementation_task`を承認した場合のみ、正式な実装Issueが別途自動生成される。

## Latest Handoff

- **日時**: {datetime.now(timezone.utc).isoformat()}
- **作業者**: GitHub Actions AI discussion pipeline
- **要点**: 討議と分類が完了し、CEO判断待ち。

{RECORD_START}
```json
{record_json}
```
{RECORD_END}
"""
    return {
        "title": clean_title(f"[AI Discussion] {topic}"),
        "body": body,
        "labels": ["status:hold", "ready:false", "owner:human", "execution:tbd"],
    }


def extract_record(body: str) -> dict[str, Any]:
    if PROPOSAL_MARKER not in body:
        raise ValueError("Issue is not an AI Discussion proposal")
    pattern = re.escape(RECORD_START) + r"\s*```json\s*(.*?)\s*```\s*" + re.escape(RECORD_END)
    match = re.search(pattern, body, flags=re.DOTALL)
    if not match:
        raise ValueError("AI Discussion record is missing")
    value = json.loads(match.group(1))
    if not isinstance(value, dict) or value.get("version") != 1:
        raise ValueError("AI Discussion record version is invalid")
    return value


def build_implementation(proposal_body: str, source_issue: int) -> dict[str, Any]:
    record = extract_record(proposal_body)
    classification = record.get("classification") or {}
    if classification.get("classification") != "implementation_task":
        raise ValueError("Only implementation_task proposals can create an implementation Issue")
    topic = clean_title(str(record.get("topic", "AI discussion follow-up")), limit=180)
    source_marker = f"<!-- ai-discussion-source:#{source_issue} -->"
    body = f"""{source_marker}
## Meta

- Label(status / ready / owner / execution): GitHub Labelを参照。本文には転記しない。
- blocked-by: なし
- related-docs: 元Decision Proposal #{source_issue}、`docs/ai_collaboration_rules_v2.1.md`、`docs/AI_COLLABORATION.md`

## Objective

{classification.get('objective') or topic}

## Scope

{bullets(classification.get('scope', []))}

## Acceptance Criteria

{checks(classification.get('acceptance_criteria', []))}

## Test Cases

{numbered(classification.get('test_cases', []))}

## Current State

Decision Proposal #{source_issue} がCEOに承認され、実装着手可能なIssueとして自動生成された。未着手。

## Completed

- Decision Proposal #{source_issue} で討議・分類・CEO承認が完了

## Remaining

- [ ] Scopeの実装
- [ ] Acceptance Criteriaの検証
- [ ] Test Casesの実行と結果記録

## Next Action

着手可能なエージェントがLabel、本文全体、関連設計書を確認し、設計変更を伴わないことを再確認してから着手する。

## Bubble Manual Action Required

なし。Bubble変更が必要だと判明した場合は、このIssueを進めずCEOへエスカレーションする。

## Latest Handoff

- **日時**: {datetime.now(timezone.utc).isoformat()}
- **作業者**: GitHub Actions AI discussion approval pipeline
- **要点**: Decision Proposal #{source_issue} の承認を受けて実装Issueを生成。未着手。
"""
    return {
        "title": clean_title(f"[IMPLEMENTATION] {topic}"),
        "body": body,
        "labels": ["status:todo", "ready:true", "owner:unassigned", "execution:tbd"],
    }


def build_summary(routing: dict[str, Any], discussion: dict[str, Any]) -> str:
    router_usage = routing.get("usage") or {}
    records = []
    if int(routing.get("api_calls") or 0):
        records.append(
            {
                "provider": "openai",
                "speaker": "router",
                "model": routing.get("model"),
                "input_tokens": int(router_usage.get("input_tokens") or 0),
                "output_tokens": int(router_usage.get("output_tokens") or 0),
                "api_calls": int(routing.get("api_calls") or 0),
                "retry_count": 0,
                "estimated_cost_usd": float(routing.get("estimated_cost_usd") or 0),
            }
        )
    records.extend(discussion.get("calls", []))
    total_input = sum(int(record.get("input_tokens") or 0) for record in records)
    total_output = sum(int(record.get("output_tokens") or 0) for record in records)
    total_api_calls = sum(int(record.get("api_calls") or 1) for record in records)
    total_cost = sum(float(record.get("estimated_cost_usd") or 0) for record in records)
    rows = [
        f"| {record.get('speaker')} | {record.get('provider')} | `{record.get('model')}` | "
        f"{int(record.get('api_calls') or 1)} | {int(record.get('retry_count') or 0)} | "
        f"{record.get('input_tokens')} | {record.get('output_tokens')} | ${float(record.get('estimated_cost_usd') or 0):.8f} |"
        for record in records
    ]
    rows_text = "\n".join(rows) if rows else "| forced router | none | n/a | 0 | 0 | 0 | 0 | $0.00000000 |"
    return f"""## AI discussion usage

- Discussion status: `{discussion.get('status')}`
- API calls: `{total_api_calls}`
- Input tokens: `{total_input}`
- Output tokens: `{total_output}`
- Estimated cost: `${total_cost:.8f}`

| Role | Provider | Model | API calls | Retries | Input tokens | Output tokens | Estimated cost (USD) |
|---|---|---|---:|---:|---:|---:|---:|
{rows_text}

Cost is calculated from actual API token usage and the repository-variable rates configured for this run.
"""


def write_payload(payload: dict[str, Any], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)

    proposal = subparsers.add_parser("proposal")
    proposal.add_argument("--topic", required=True)
    proposal.add_argument("--routing", required=True, type=Path)
    proposal.add_argument("--discussion", required=True, type=Path)
    proposal.add_argument("--classification", required=True, type=Path)
    proposal.add_argument("--output", required=True, type=Path)

    implementation = subparsers.add_parser("implementation")
    implementation.add_argument("--proposal-body", required=True, type=Path)
    implementation.add_argument("--source-issue", required=True, type=int)
    implementation.add_argument("--output", required=True, type=Path)

    summary = subparsers.add_parser("summary")
    summary.add_argument("--routing", required=True, type=Path)
    summary.add_argument("--discussion", required=True, type=Path)
    summary.add_argument("--output", required=True, type=Path)

    args = parser.parse_args()
    try:
        if args.command == "proposal":
            payload = build_proposal(
                args.topic,
                read_json(args.routing),
                read_json(args.discussion),
                read_json(args.classification),
            )
            write_payload(payload, args.output)
        elif args.command == "implementation":
            payload = build_implementation(args.proposal_body.read_text(), args.source_issue)
            write_payload(payload, args.output)
        else:
            text = build_summary(read_json(args.routing), read_json(args.discussion))
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(text)
    except (KeyError, OSError, TypeError, ValueError, json.JSONDecodeError) as exc:
        print(f"issue builder error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
