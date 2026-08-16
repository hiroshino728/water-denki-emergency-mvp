# AGENTS.md — Claude Code / Codex 共同開発運用ルール

このファイルは、このリポジトリで作業するすべてのAIエージェント(Claude Code、Codex、その他将来追加されるAIツール)に共通する運用ルールを定義する。

**このリポジトリの運用ルールは3つのファイルに分かれている。役割を混同しないこと。**

| ファイル | 置き場所 | 役割 |
|---|---|---|
| `AGENTS.md`(このファイル) | 親リポジトリ直下 | ブランチ保護・PR運用、記憶非共有の原則、エージェント間の役割分担、Handoffのスタック検知(セッション引き継ぎ) |
| `docs/ai_collaboration_rules_v2.1.md` | docsサブモジュール | GitHub IssueのSSOT分離、Label/本文の役割分離、Bubble操作の3段階実行優先順位、レースコンディション方針、IssueのClose条件 |
| `docs/AI_COLLABORATION.md` | docsサブモジュール | サブモジュール(docs)と親リポジトリの関係・公開境界、ADR優先順位、Assumption/Decision/Factの区別、個人情報の取り扱い |

Issueに着手する前に、このAGENTS.mdに加えて**必ず`docs/ai_collaboration_rules_v2.1.md`を読むこと**。以下は要点のみを転記した参照であり、詳細な運用ルール(ラベル体系・Bubble実行優先順位・Close条件・引き継ぎ手順)はそちらが正。

**対象範囲の注意:** 設計判断(データモデル・業務フロー・技術選定)の正は引き続き`docs/`配下(git submodule、`mizu-denki-emergency-docs`)にある。このファイルおよび`docs/ai_collaboration_rules_v2.1.md`は「タスク管理・AI間の引き継ぎ・開発プロセス」のルールを扱う。

---

## 0. 最重要原則:GitHubに記録されていない情報は存在しないものとして扱う

**会話履歴や各AIの記憶(session memory, chat history)を、エージェント間の共有情報として扱ってはいけない。**

- Claude CodeとCodexは、互いの会話履歴・メモリ・セッション内で得た文脈を一切共有しない。
- あるセッションで交わされた口頭の合意・説明・補足は、GitHub(Issueコメント、Issue本文、PR、コミット、コード、`docs/`)に書かれていない限り、他のAIエージェントにとっては**存在しない**。
- 「さっき話した件」「前回説明した通り」といった前提に依存する引き継ぎは無効。次に着手するエージェント(人間を含む)がGitHubの情報だけを読んで再開できる状態を、作業終了時に必ず作ること。
- したがって、作業の意図・判断理由・残タスクは、口頭やチャットではなく **Issue本文(特にLatest Handoff)・Issueコメント・PR説明・コミットメッセージ** に書く。これが唯一の引き継ぎ手段である。

---

## 1. Issue運用の要点(詳細は `docs/ai_collaboration_rules_v2.1.md`)

- 機械判定項目(`status:*` / `ready:*` / `owner:*` / `execution:*`)はGitHub LabelがSSOT。Issue本文に重複記載しない。
- AIが自律的に着手できるのは、**`ready:true`かつ`blocked-by`がすべてclose済みのIssue**のみ。
- Issue本文中の文脈的フィールド(`objective` / `scope` / `acceptance_criteria` / `test_cases` / `current_state` / `completed` / `remaining` / `next_action` / `latest_handoff`)がSSOT。
- 依存関係は本文に`blocked-by:#XX`の形式で明記する。

新規Issueは `.github/ISSUE_TEMPLATE/task_issue_v2.md` から作成する。

---

## 2. Handoffのスタック検知とセッション引き継ぎ

AIエージェントのセッションは、利用制限・クラッシュ・タイムアウト等で予告なく停止することがある。停止したセッションが`status:in_progress`のままIssueを占有し続けないよう、以下のルールを設ける(`docs/ai_collaboration_rules_v2.1.md` 7節の引き継ぎ手順を補完するルール)。

### 2.1 放棄セッションの判定

`status:in_progress`のIssueについて、`Latest Handoff`に記載された最終更新の日時から**目安4時間以上経過している**場合、他のエージェント(Claude Code・Codex・人間の誰でも)はそのセッションを「放棄された」とみなしてよい。`Latest Handoff`には日時をISO8601形式(例: `2026-08-11T14:30:00+09:00`)で記載する。相対表現(「さっき」「今日」等)は使わない。

### 2.2 引き継ぎ手順

放棄されたと判断したエージェントは、以下の手順でIssueを引き継ぐ。

1. Issueに「前回セッションが停止したため引き継ぎます」という趣旨のコメントを残す(判定根拠となった日時も明記する)。
2. `owner:*`ラベルを、引き継ぐエージェント自身のものに付け替える。
3. `status`は`in_progress`のまま継続してよい(`todo`には戻さない。せっかく積み上がった`Completed`の情報を無駄にしないため)。
4. 引き継いだエージェントは、Issue本文(`Latest Handoff`含む)を読み、そこに書かれている情報だけを頼りに再開する。それ以前の会話履歴・記憶には一切依存しない(第0項)。

### 2.3 補足

- 4時間はあくまで目安であり、機械的な自動失効タイマーではない。明らかに作業が続いている痕跡(直近のコミット・PR等)があれば、記載日時がやや古くても引き継ぎを見合わせる判断をしてよい。
- 引き継ぎ後に元のセッションが復帰した場合、Issueコメントで状況を確認してから作業を再開する(二重着手を避ける)。

---

## 3. ブランチ・PR運用

**mainブランチへの直接pushは禁止する。** 必ず`ブランチ作成 → PR → レビュー → マージ`の手順を踏む。

- ブランチ名に決まった命名規則は強制しないが、Issue番号を含めると追跡しやすい(例: `line-04-channel-identity`, `issue-23-fix-xxx`)。
- PRは `.github/pull_request_template.md` のテンプレートに従い、関連Issue番号を必ず記載する(例: `Closes #23` またはレビュー段階では `Refs #23`)。
- mainブランチにはRuleset(直接push禁止・PR経由必須)を設定している。ローカルで`git push origin main`を実行しても拒否される想定で運用する。
- PRをマージできるのは、レビュー(人間によるレビューが基本。将来的にAI間レビューを追加する可能性はあるが、現時点では篠さんの確認を経ることを原則とする)を経た後のみ。
- **新規ADRの追加、または既存の設計判断(Decision)を変更するPRは、内容にBubble実装が含まれていなくても、篠さんのレビュー・マージ判断を経てから反映する。** AIはPRを開くところまでを担当し、自動マージしない。PR作成時は `.github/pull_request_template.md` の `Does this PR change a Decision?` に `Yes` / `No` を明記し、`Yes`の場合は自動マージしない。
- マージ後は、関連Issueの`status`を`status:review`→`status:done`に更新し、`Latest Handoff`を最終状態に更新する。

**PRのマージ方式はTier 1(自動マージ)とTier 2(篠さんの承認必須)に分かれる。**

- **Tier 2(原則・デフォルト)**: 上記の手順(レビュー・篠さんの確認を経てマージ)。`Does this PR change a Decision?`が`Yes`のPR、ADR新規・変更、Gate判定に関わるPR、Production変更を伴うPR、法務・契約・金銭・責任分界に関わるPRは常にTier 2とする。
- **Tier 1(自動マージ、限定的)**: docs submodule参照のみを更新するPR等、機械的で安全性を検証可能な種別に限り、`.github/workflows/auto-merge-docs-submodule-sync.yml`による自動マージを許可する。判定条件・fail-closed設計は`docs/ai_collaboration_rules_v2.1.md`第8節を参照。Tier 1の対象範囲拡張には、都度篠さんの承認を要する。

---

## 4. Claude CodeとCodexの役割分担について

**固定的な担当分けは行わない。** Claude Code・Codexのどちらも、原則としてすべてのIssueに着手可能とする。

- 「このタスクは必ずCodexが担当する」といった静的なルールは設けない。実際にどちらが着手するかは、その時点でどちらが動けるか(利用制限・セッション状況)によって決まる。
- これは第0項・第2項の「GitHubの情報だけで引き継げる」設計と表裏一体である。担当が固定されていると、担当エージェントが停止した時点でタスク全体が止まってしまう。

---

## 5. Bubbleに関する運用ルール

実行手段の判定(AI直接実行 / AI半自動実行 / Human-in-the-loop)は`docs/ai_collaboration_rules_v2.1.md` 3節の3段階優先順位に従う。そのうえで、以下は本リポジトリとして譲らない一線とする。

- **Bubble Production環境の構造変更(データモデル変更、Workflow変更、既存ページの破壊的変更等)は、`execution`の判定結果に関わらず、実行前に人間の明示的な承認を得る。** AIがBubble Editorを直接操作できる(`execution:ai-direct`)と判定された場合でも、Production構造変更を伴う操作の実行そのものは承認を経てから行う。承認は、対象のIssue上でのコメント、またはチャットでの明示的な指示によって行われる。
  - 「Bubble AI操作能力検証」Issueにおける操作能力の**検証**(ログイン可否・画面遷移可否等の確認)自体も、実施前にチャットで明示的な了承を得てから着手する。
- この承認境界は、`docs/poc/LINE-03-liff-bubble-poc.md`にある「認証境界」(初回ログイン・MFA・OAuth本人確認は篠さん本人、それ以降の認証済みセッションでの操作はAI可)とは別の軸のルールである。認証境界は「誰がログインするか」、本ルールは「Production構造変更に承認が要るか」を定めている。
- テストデータ投入等の低リスク操作は、「Bubble AI操作能力検証」Issueの結果を踏まえ、個別に自動化を許可できるよう設計を残す。一律で「低リスクは全部自動化可」とはしない。

---

## 6. このファイルと他ドキュメントの関係

- `CLAUDE.md`: Claude Code固有の補足(サブエージェント運用、Claude Code特有のツール利用方法等)のみを記載し、共通ルールの重複記載は行わない。
- `docs/ai_collaboration_rules_v2.1.md`: Issue運用(SSOT分離・ラベル・Bubble実行優先順位・Close条件・引き継ぎ手順)の正。
- `docs/AI_COLLABORATION.md`: サブモジュール運用・ADR優先順位・Assumption/Decision/Factの区別・個人情報取り扱いの正。
