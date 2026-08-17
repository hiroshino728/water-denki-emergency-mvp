# AI Discussion Pipeline

Issue #35 のV1実装です。Claude APIとOpenAI APIを交互に1回ずつ呼び出し、各ラウンドで収束判定を行います。結果は通常の実装Issueではなく、CEO判断待ちのDecision Proposal Issueとして起票されます。

このパイプラインでは、通常時の**1ラウンドを1モデルの採用応答（1 API call）**と定義します。両AIが1回ずつ発言する最初の往復（first exchange）はRound 1とRound 2で構成されるため、2AI間の一致を確認できる最短時点はRound 2終了時です。Round 1は初案として必ず`unresolved`になり、`MAX_ROUNDS`の最小値は2です。JSON解析失敗時の回復用API callは同一ラウンド内の再試行として別途数えます。

この仕組みがDecisionを確定することはありません。`/approve`または`/reject`を実行できるのはリポジトリ所有者だけで、`implementation_task`を承認した場合に限り、正式な後続Issueが生成されます。

## ⚠️ 議題(topic)の取り扱いに関する運用ルール(必読)

**このリポジトリ(`water-denki-emergency-mvp`)は現在Publicです。** GitHub Actionsのログ・生成されるDecision Proposal Issue・実装Issueは、Publicリポジトリでは認証不要で誰でも閲覧できます。2026-08-16、篠さん(CEO)はこのPublic設定を維持したうえで本パイプラインの運用を継続する判断をしました(Issue #35参照)。この判断は「Actionsログや生成Issueが公開される」というリスクそのものを許容するものであり、「入力内容の機密性への配慮が不要になる」という意味ではありません。

したがって、`topic`(および`force_first_mover`以外の入力全般)には、**以下を絶対に含めないでください**:

- 実在する顧客・加盟店の氏名、電話番号、住所等の個人情報
- 未公開の契約条件・料率・紹介料・金額等の商用機密
- APIキー、トークン、パスワード等の認証情報
- その他、公開されると事業上・法務上の不利益になりうる情報

`topic`は、`議題: {topic}`という形でそのままAIへのプロンプトに埋め込まれ、AIの応答(討議内容)は生成されるDecision Proposal Issue本文へ、JSON解析失敗時は生レスポンスの一部(既定4000文字、APIキー一致文字列のみ伏せ字化)がActionsログへ、それぞれ**Publicな形で残ります**。APIキー自体の伏せ字化は実装されていますが、議題の機密性そのものを守る仕組みではありません。

機密情報を含む、または含む可能性を否定できない実業務の議題は、本パイプラインだけでなく、PublicなIssue・PR・commit・Actionsへも書き込まないでください。詳細をGitHubへ転記せず、必要最小限の非機密情報だけで篠さん(CEO)へrouting判断を求めます。現時点では新しいprivate control repositoryやconfidential control planeは設けません。テスト・検証目的の議題を使う場合は、`(合成テスト議題、実プロジェクトとは無関係)`等、テスト由来であることが分かる注記を`topic`本文に含める運用とします(過去のTC実施ではこの慣行が徹底されており、2026-08-17時点で過去の全Actions run・生成Issueを監査した結果、機密情報の混入は確認されていません)。

Workflow実行画面の`public_content_confirmed`は、上記確認を実行前に明示するためのfail-closed gateです。未確認のままではAPI呼び出しもIssue起票も行いません。この確認は機密情報を自動検出するscannerではないため、入力者による事前確認を代替しません。

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
| `DISCUSSION_JSON_MAX_ATTEMPTS` | 討議モデルのJSON解析失敗時を含む最大試行回数。`1`〜`3`、未設定時は`2`（1回だけ再試行） |
| `INVALID_JSON_LOG_MAX_CHARS` | JSON解析失敗時にログへ残すモデル生レスポンスの最大文字数。`100`〜`20000`、未設定時は`4000` |
| `ROUTER_INPUT_USD_PER_MTOK` | ルーターモデルの入力100万tokenあたりUSD |
| `ROUTER_OUTPUT_USD_PER_MTOK` | ルーターモデルの出力100万tokenあたりUSD |
| `OPENAI_DISCUSSION_INPUT_USD_PER_MTOK` | ChatGPT討議モデルの入力100万tokenあたりUSD |
| `OPENAI_DISCUSSION_OUTPUT_USD_PER_MTOK` | ChatGPT討議モデルの出力100万tokenあたりUSD |
| `ANTHROPIC_DISCUSSION_INPUT_USD_PER_MTOK` | Claude討議モデルの入力100万tokenあたりUSD |
| `ANTHROPIC_DISCUSSION_OUTPUT_USD_PER_MTOK` | Claude討議モデルの出力100万tokenあたりUSD |

料金は各プロバイダーの最新価格を設定してください。静的な見積額は保持せず、レスポンスの実token usageと、その実行時のVariableを使って概算costを計算します。

## 実行方法

1. Actionsから **AI discussion pipeline** を選ぶ。
2. `topic`が公開可能であり、禁止情報を含まないことを入力前に確認する。
3. `topic`を入力し、`public_content_confirmed`を有効にする。確認できない場合は実行しない。
4. 通常は`force_first_mover: auto`を選ぶ。CEOが先攻を指定する場合だけ`chatgpt`または`claude`を選ぶ。
5. 完了後、Actions Summaryでモデル、API call数、token usage、概算costを確認する。
6. 起票された`[AI Discussion]` Issueの討議結果と分類を確認する。
7. CEO本人がIssueへ単独行の`/approve`または`/reject`をコメントする。`/reject`の次の行以降は理由として記録される。

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
- 討議モデルの応答がJSONとして解析できない場合だけ、同じラウンドを既定で1回再試行します。再試行は討議ラウンドを増やしませんが、実API call数・token usage・概算costには失敗した試行も含めます。HTTP認証・quota・通信エラーは自動再試行しません。
- JSON解析失敗時は、原因調査のためモデル生レスポンスとプロバイダーの停止理由（`status` / `incomplete_details` / `stop_reason`）を1行JSONとして標準エラーへ出力します。改行はエスケープし、APIキーに一致する文字列は伏せ字にし、生レスポンスは既定で先頭4000文字までに制限します。**議題の取り扱いルールは上記「⚠️ 議題(topic)の取り扱いに関する運用ルール」を必ず参照してください。**

## ローカルテスト

実APIを呼ばない単体テストは標準ライブラリだけで実行できます。

```bash
python3 -m unittest discover -s scripts/ai_discussion/tests -v
```

実機テストではIssue #35のTC-01〜TC-11を使います。特にTC-09はリポジトリ所有者以外のコメントでjobがskipされること、TC-11はSecret値ではなく未設定のSecret名だけがログへ出ることを確認してください。APIを使うE2Eは課金を伴うため、CEOが任意の軽い議題を1件選んだうえで実行します。
