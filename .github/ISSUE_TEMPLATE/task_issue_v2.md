---
name: "AI協働タスク v2.1"
about: "Claude Code / Codex共同開発用タスクIssue(実行状態のSSOT)"
title: "[AREA] タスク名"
labels: ["status:todo", "ready:false", "owner:unassigned", "execution:tbd"]
---

<!--
このIssueは「実行状態のSSOT」です。仕様そのものはここに書かず、設計書(vision.md /
assumptions.md / data_model_phase1.md / business_workflow.md / adr/*)を参照してください。

機械判定項目(status/ready/owner/execution)はGitHub LabelがSSOTです。本文に重複記載しないでください。
Labelを変更するときは、必ず対応する本文(Current State等)も同時に更新してください。

Claude Code / Codexは作業開始時に「Label(現在の状態)」＋「このIssue本文全体」＋「関連設計書」
の3つを読んでください。latest_handoffは再開のための要約に過ぎず、それ単体では判断しないでください。
中断・完了時は、Labelと本文(特にLatest Handoff)の両方を必ず更新してください。

詳細な運用ルールは docs/ai_collaboration_rules_v2.1.md を参照。
-->

## Meta

- Label(status / ready / owner / execution): GitHub Labelを参照。本文には転記しない。
  - ownerとexecutionは独立した軸です。execution:human-bubbleになっても、
    このIssueを完遂させる責任(owner)はAIエージェント側に残ります。
- blocked-by: #(なければ空欄)
- related-docs: (例: data_model_phase1.md#jobstatuslog, business_workflow.md#4.5)

## Objective

<!-- このIssueで何を達成するか。1〜2文。 -->

## Scope

<!-- 対象ワークフロー / データ型 / フィールド / ファイル -->

## Acceptance Criteria

- [ ]
- [ ]

## Test Cases

<!-- 手動実行手順を含む。競合テストが必要な場合は明記(rules v2.1の4節参照) -->

1.

## Current State

<!-- 現時点の状態。作業のたびに更新。 -->

## Completed

-

## Remaining

-

## Next Action

<!-- 次に「誰が」「何を」やるか。具体的に。 -->

## Bubble Manual Action Required

<!-- execution: human-bubble または ai-semi-auto の場合のみ記載。
Step 1: ...
Step 2: ...
Only when: ...
Expected result: ...
-->

## Latest Handoff

<!-- 直近の担当者が次の担当者(別エージェントの可能性あり)に向けて書く。
[日時] [担当者(claude-code/codex/human)]
要点:
-->
