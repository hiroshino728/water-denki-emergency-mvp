# AGENTS.md — Claude Code / Codex 共同開発運用ルール

このファイルは、このリポジトリで作業するすべてのAIエージェント(Claude Code、Codex、その他将来追加されるAIツール)に共通する運用ルールを定義する。

**対象範囲の注意:** このファイルは「タスク管理・AI間の引き継ぎ・開発プロセス」のルールを扱う。設計判断(データモデル・業務フロー・技術選定)の正は引き続き [`docs/`](docs/) 配下(git submodule、`mizu-denki-emergency-docs`)にある。両者は役割が異なる。

| 何の正か | 参照先 |
|---|---|
| 設計判断(データモデル・業務フロー・ADR) | `docs/` 配下([README.md](README.md)参照) |
| タスクの状態・進捗・AI間の引き継ぎ | GitHub Issues(このファイルで定義) |

---

## 0. 最重要原則:GitHubに記録されていない情報は存在しないものとして扱う

**会話履歴や各AIの記憶(session memory, chat history)を、エージェント間の共有情報として扱ってはいけない。**

- Claude CodeとCodexは、互いの会話履歴・メモリ・セッション内で得た文脈を一切共有しない。
- あるセッションで交わされた口頭の合意・説明・補足は、GitHub(Issueコメント、Issue本文、PR、コミット、コード、`docs/`)に書かれていない限り、他のAIエージェントにとっては**存在しない**。
- 「さっき話した件」「前回説明した通り」といった前提に依存する引き継ぎは無効。次に着手するエージェント(人間を含む)がGitHubの情報だけを読んで再開できる状態を、作業終了時に必ず作ること。
- したがって、作業の意図・判断理由・残タスクは、口頭やチャットではなく **Issue本文・Issueコメント・PR説明・コミットメッセージ** に書く。これが唯一の引き継ぎ手段である。

この原則は第12項の「Current Handoff運用」で具体的な運用手順に落とし込む。

---

## 1. GitHub Issues運用

GitHub Issuesを、タスク管理およびAI間引き継ぎの **Single Source of Truth** とする。`WORK_LOG.md`のような別ファイルは作成しない。

### 1.1 ラベル体系

| カテゴリ | ラベル | 意味 |
|---|---|---|
| status | `status:todo` | 未着手(着手可能 or ブロック解除待ち) |
| status | `status:in-progress` | 作業中 |
| status | `status:review` | PRレビュー待ち/レビュー中 |
| status | `status:blocked` | 依存関係等でブロック中 |
| status | `status:done` | 完了 |
| agent | `agent:claude-code` | Claude Codeが担当中/担当予定 |
| agent | `agent:codex` | Codexが担当中/担当予定 |
| agent | `agent:human` | 人間(篠さん)の対応が必要 |
| priority | `priority:P0` | 最優先 |
| priority | `priority:P1` | 優先 |
| priority | `priority:P2` | 通常 |
| ready | `ready:true` | AIが自律的に着手してよい(status:todoと併用) |

各Issueには `status:*` を必ず1つ、担当が決まっていれば `agent:*` を1つ、`priority:*` を1つ付与する。`ready:true` は「着手条件が揃っている」ことを示すフラグで、`status:todo` と組み合わせて使う。

### 1.2 AIが自律的に着手できる条件

**`status:todo` かつ `ready:true` が付いているIssueのみ**、AIエージェントが自律的に(人間の個別指示なしに)着手してよい。

- どちらか一方でも欠けていれば着手しない(例:`status:todo`だが`ready:true`が無い = まだ要件や前提が固まっていない可能性がある)。
- `status:blocked` のIssueは着手しない。
- 着手する際は `status:todo` → `status:in-progress` に変更し、`agent:*` ラベルを自分自身に付け替える。

### 1.3 依存関係の記法

Issue間に依存関係がある場合、依存元Issue本文に以下の形式で明記する。

```
blocked-by:#12
```

依存先が未完了の間、依存元Issueには `status:blocked` を付与する。依存先(`#12`)が `status:done` になった時点で、依存元を `status:todo`(+ 要件が揃っていれば `ready:true`)に戻せる。

---

## 2. Issue本文の固定セクション:Current Handoff

すべてのタスクIssue(`.github/ISSUE_TEMPLATE/task.md` から作成されたもの)には、以下の固定セクションを設ける。

```markdown
## Current Handoff
Agent:
Updated:
Completed:
Remaining:
Next Action:
Blocker:
Branch:
PR:
```

| フィールド | 内容 |
|---|---|
| `Agent:` | 直前にこのIssueを担当したエージェント(`claude-code` / `codex` / `human`) |
| `Updated:` | このセクションを最後に更新した日時。**必ずISO8601形式**(例: `2026-08-11T14:30:00+09:00`)で記載する。相対表現(「さっき」「今日」等)は禁止 |
| `Completed:` | ここまでに完了した作業を箇条書きで具体的に(ファイルパス・コミットハッシュ等を含める) |
| `Remaining:` | 残っている作業を箇条書きで具体的に |
| `Next Action:` | 次に着手するエージェントが最初に行うべき、具体的で実行可能な1アクション |
| `Blocker:` | 作業を止めている要因があれば記載(無ければ「なし」) |
| `Branch:` | 作業中のブランチ名(未作成なら「未作成」) |
| `PR:` | 関連PRへのリンク(未作成なら「未作成」) |

**セッション終了時(そのタスクから離れる時)には、このCurrent Handoffを必ず最新状態に更新する。** これを更新せずにセッションを終えることは、引き継ぎ情報を破棄する行為に等しいとみなす。

---

## 3. Current Handoff運用:スタック検知とセッション引き継ぎ

AIエージェントのセッションは、利用制限・クラッシュ・タイムアウト等で予告なく停止することがある。停止したセッションが `status:in-progress` のままIssueを占有し続けないよう、以下のルールを設ける。

### 3.1 放棄セッションの判定

`status:in-progress` のIssueについて、`Current Handoff` の `Updated:` から**目安4時間以上経過している**場合、他のエージェント(Claude Code・Codex・人間の誰でも)はそのセッションを「放棄された」とみなしてよい。

### 3.2 引き継ぎ手順

放棄されたと判断したエージェントは、以下の手順でIssueを引き継ぐ。

1. Issueに「前回セッションが停止したため引き継ぎます」という趣旨のコメントを残す(判定根拠となった`Updated:`の日時も明記する)。
2. `agent:*` ラベルを、引き継ぐエージェント自身のものに付け替える。
3. `status` は `in-progress` のまま継続してよい(`todo` には戻さない。せっかく積み上がった`Completed:`の情報を無駄にしないため)。
4. 引き継いだエージェントは、`Current Handoff` の `Completed:` / `Remaining:` / `Next Action:` を読み、そこに書かれている情報だけを頼りに再開する。それ以前の会話履歴・記憶には一切依存しない(第0項)。

### 3.3 補足

- 4時間はあくまで目安であり、機械的な自動失効タイマーではない。明らかに作業が続いている痕跡(直近のコミット等)があれば、`Updated:` がやや古くても引き継ぎを見合わせる判断をしてよい。
- 引き継ぎ後に元のセッションが復帰した場合、Issueコメントで状況を確認してから作業を再開する(二重着手を避ける)。

---

## 4. ブランチ・PR運用

**mainブランチへの直接pushは禁止する。** 必ず `ブランチ作成 → PR → レビュー → マージ` の手順を踏む。

- ブランチ名に決まった命名規則は強制しないが、Issue番号を含めると追跡しやすい(例: `line-04-channel-identity`, `issue-23-fix-xxx`)。
- PRは `.github/pull_request_template.md` のテンプレートに従い、関連Issue番号を必ず記載する(例: `Closes #23` またはレビュー段階では `Refs #23`)。
- mainブランチにはRuleset(直接push禁止・PR経由必須)を設定している。ローカルで `git push origin main` を実行しても拒否される想定で運用する。
- PRをマージできるのは、レビュー(人間によるレビューが基本。将来的にAI間レビューを追加する可能性はあるが、現時点では篠さんの確認を経ることを原則とする)を経た後のみ。
- マージ後は、関連Issueの `status` を `status:review` → `status:done` に更新し、`Current Handoff` の `PR:` を最終状態に更新する。

---

## 5. Claude CodeとCodexの役割分担について

**固定的な担当分けは行わない。** Claude Code・Codexのどちらも、原則としてすべてのIssueに着手可能とする。

- 「このタスクは必ずCodexが担当する」といった静的なルールは設けない。実際にどちらが着手するかは、その時点でどちらが動けるか(利用制限・セッション状況)によって決まる。
- これは第0項・第3項の「GitHubの情報だけで引き継げる」設計と表裏一体である。担当が固定されていると、担当エージェントが停止した時点でタスク全体が止まってしまう。

---

## 6. Bubbleに関する運用ルール

- **設計書の作成・修正、実装案の作成、テスト手順の作成、変更手順書の作成までは、AIが自律的に行ってよい。**
- **Bubble Production環境の構造変更(データモデル変更、Workflow変更、既存ページの破壊的変更等)は、人間の明示的な承認なしに実行してはいけない。** AIは変更手順書・実装案を作るところまでを担当し、実際の変更操作(Bubbleエディタでの実行)は承認を得てから行う。
  - 承認は、対象のIssue上でのコメント、またはチャットでの明示的な指示によって行われる。
  - この承認境界は、既存の [`docs/poc/LINE-03-liff-bubble-poc.md`](docs/poc/LINE-03-liff-bubble-poc.md) にある「認証境界」(初回ログイン・MFA・OAuth本人確認は篠さん本人、それ以降の認証済みセッションでの操作はAI可)とは別の軸のルールである。認証境界は「誰がログインするか」、本ルールは「Production構造変更に承認が要るか」を定めている。
- **テストデータ投入等の低リスク操作は、将来的に個別のIssue・ADRで自動化を許可できるよう設計を残す。** 現時点では一律「承認が必要」側に倒し、リスクの低い操作カテゴリが具体的に特定できた時点で、都度このセクションを更新して許可範囲を明記する形をとる(一括で「低リスクは全部自動化可」とはしない)。

---

## 7. 新しいIssueの作り方

`.github/ISSUE_TEMPLATE/task.md` を使って作成する。作成時に最低限:

- `status:todo` を付与する(着手条件が揃っていなければ`ready:true`は付けない)
- `priority:*` を付与する
- 依存関係があれば本文に `blocked-by:#XX` を記載し、`status:blocked` を付与する
- `Current Handoff` セクションは空欄(または `Agent: (未着手)` 等のプレースホルダ)のまま作成してよい。実際に着手したエージェントが最初の更新を行う。

---

## 8. このファイルとCLAUDE.mdの関係

このAGENTS.mdが、Claude Code・Codex共通のルールを一本化したものである。`CLAUDE.md` にはClaude Code固有の補足(サブエージェント運用、Claude Code特有のツール利用方法等)のみを記載し、共通ルールの重複記載は行わない。
