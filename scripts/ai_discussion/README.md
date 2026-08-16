# AI Discussion Pipeline

Issue #35 のV1実装です。Claude APIとOpenAI APIを交互に1回ずつ呼び出し、各ラウンドで収束判定を行います。結果は通常の実装Issueではなく、CEO判断待ちのDecision Proposal Issueとして起票されます。

このパイプラインでは、**1ラウンドを1モデルの応答（1 API call）**と定義します。両AIが1回ずつ発言する最初の往復（first exchange）はRound 1とRound 2で構成されるため、2AI間の一致を確認できる最短時点はRound 2終了時です。Round 1は初案として必ず`unresolved`になり、`MAX_ROUNDS`の最小値は2です。

この仕組みがDecisionを確定することはありません。`/approve`または`/reject`を実行できるのはリポジトリ所有者だけで、`implementation_task`を承認した場合に限り、正式な後続Issueが生成されます。

## 構成

- `router.py`: OpenAIの軽量モデルで先攻を選択する。`force_first_mover`指定時はAPIを呼ばず指定を優先する。
- `discuss.py`: 先攻からClaude / ChatGPTを交互に呼び、各API呼び出しを1ラウンドとして収束判定する。
- `classify.py`: 最終ラウンドの候補分類をV1の処理経路へ正規化する。非収束は常に`unresolved`になる。
- `issue_builder.py`: Decision Proposal、正式な実装Issue、Actions Summaryを生成する。
- `ai_discussion_pipeline.yml`: 手動起動からDecision Proposal起票までを行う。
- `ai_discussion_approval.yml`: Issueコメントの承認・却下コマンドを処理する。

## Actions Secrets

リポジトリの **Settings → Secrets and variables → Actions → Secrets** に次を登録します。

| Secret | 用途 |
|---|---|
| `OPENAI_API_KEY` | 先攻判定およびChatGPT討議ラウンド |
| `ANTHROPIC_API_KEY` | Claude討議ラウンド |

値はworkflowのログ、Actions Summary、Issue本文へ出力しません。未設定の場合はAPI呼び出し前に、欠けている設定名だけを示して失敗します。

## Actions Variables

同じ画面の **Variables** に次を登録します。モデル名と料金はコードへ固定せず、実行時設定を使用します。

| Variable | 内容 |
|---|---|
| `ROUTER_MODEL` | OpenAIの先攻判定モデル |
| `OPENAI_DISCUSSION_MODEL` | ChatGPT討議モデル |
| `ANTHROPIC_DISCUSSION_MODEL` | Claude討議モデル（`output_config.format`のstructured outputs対応モデルを指定） |
| `MAX_OUTPUT_TOKENS` | 1 API callあたりの最大出力token数 |
| `MAX_ROUNDS` | 最大討議ラウンド数。1ラウンドは1 API call、最小値は`2`、未設定時は`3` |
| `ROUTER_INPUT_USD_PER_MTOK` | ルーターモデルの入力100万tokenあたりUSD |
| `ROUTER_OUTPUT_USD_PER_MTOK` | ルーターモデルの出力100万tokenあたりUSD |
| `OPENAI_DISCUSSION_INPUT_USD_PER_MTOK` | ChatGPT討議モデルの入力100万tokenあたりUSD |
| `OPENAI_DISCUSSION_OUTPUT_USD_PER_MTOK` | ChatGPT討議モデルの出力100万tokenあたりUSD |
| `ANTHROPIC_DISCUSSION_INPUT_USD_PER_MTOK` | Claude討議モデルの入力100万tokenあたりUSD |
| `ANTHROPIC_DISCUSSION_OUTPUT_USD_PER_MTOK` | Claude討議モデルの出力100万tokenあたりUSD |

料金は各プロバイダーの最新価格を設定してください。静的な見積額は保持せず、レスポンスの実token usageと、その実行時のVariableを使って概算costを計算します。

## 実行方法

1. Actionsから **AI discussion pipeline** を選ぶ。
2. `topic`を入力する。
3. 通常は`force_first_mover: auto`を選ぶ。CEOが先攻を指定する場合だけ`chatgpt`または`claude`を選ぶ。
4. 完了後、Actions Summaryでモデル、API call数、token usage、概算costを確認する。
5. 起票された`[AI Discussion]` Issueの討議結果と分類を確認する。
6. CEO本人がIssueへ単独行の`/approve`または`/reject`をコメントする。`/reject`の次の行以降は理由として記録される。

`workflow_dispatch`と`issue_comment`はworkflowがdefault branchに存在するときだけ起動します。PR上のworkflowはローカル・静的テストまでとし、実機E2Eはレビュー・マージ後に行います。

## V1の承認結果

| Classification | `/approve`の結果 |
|---|---|
| `implementation_task` | `task_issue_v2.md`と同じ見出し構造の別Issueを生成し、Proposalを`status:done`でclose |
| `unresolved` | 状態を維持し、追加討議または直接指示を求める |
| `business_decision` | 実装Issueを作らず、`status:todo` / `ready:false` / `owner:human`へ更新 |
| `architecture_decision` | 同上 |
| `specification_change` | 同上 |

`/reject`では`status:hold`を維持してProposalをcloseし、後続Issueを作りません。GitHub EnvironmentsやRequired Reviewersは使用しません。

## 安全性と再実行

- 承認workflowは、リポジトリ所有者のコメント、Proposal識別マーカー、Decision Classificationを再検証します。
- 通常IssueやPull Requestへの同名コメントは処理しません。
- Issue単位の`concurrency`とコメントIDマーカーで同一コマンドの二重処理を防ぎます。
- 実装Issueは元Proposal番号のマーカーで検索し、再実行時に重複生成しません。
- APIキーはHTTP Authorization headerだけに設定し、生成AIへのpromptには含めません。

## ローカルテスト

実APIを呼ばない単体テストは標準ライブラリだけで実行できます。

```bash
python3 -m unittest discover -s scripts/ai_discussion/tests -v
```

実機テストではIssue #35のTC-01〜TC-11を使います。特にTC-09はリポジトリ所有者以外のコメントでjobがskipされること、TC-11はSecret値ではなく未設定のSecret名だけがログへ出ることを確認してください。APIを使うE2Eは課金を伴うため、CEOが任意の軽い議題を1件選んだうえで実行します。
