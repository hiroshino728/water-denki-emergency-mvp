# CLAUDE.md — Claude Code固有の補足

共通ルールは [`AGENTS.md`](AGENTS.md) を参照すること。本ファイルはClaude Code固有の補足のみを扱う。

Issue運用・ラベル・Current Handoff・着手条件(`status:todo` + `ready:true`)・ブランチ/PR運用・Bubble承認境界などは、すべてAGENTS.mdに一本化されている。ここに重複して書かない。

---

## Claude Code固有の注意点

### GitHub操作は `gh` CLI(Bashツール)で行う

このセッションでは `gh` CLIが認証済みで利用できる。Issue/PRの作成・更新・ラベル操作・コメント投稿は `gh issue` / `gh pr` サブコマンドで行う。Current Handoffセクションの更新も、Issue本文を取得(`gh issue view <N> --json body`)→編集→`gh issue edit <N> --body-file <file>` で書き戻す形が確実。

### 日時の扱い

Current Handoffの `Updated:` を書く際は、システムから渡される現在日時を機械的にコピーするのではなく、実際にその更新を行っている時刻をISO8601形式(`+09:00`等のタイムゾーン付き)で記載する。

### Bubbleエディタへのブラウザ操作には既知の制約がある

Claude Code(このリポジトリのセッション)が使うブラウザ拡張(Claude in Chrome)は、`bubble.io` / `*.bubbleapps.io` へのナビゲーションがポリシーでブロックされ、自動操作できないことを確認済み([`docs/poc/LINE-03-liff-bubble-poc.md`](docs/poc/LINE-03-liff-bubble-poc.md) 参照)。「サイトへのアクセス」設定を「すべてのサイト」にしていてもブロックされる。

- Bubbleエディタ上での実際の設定作業(画面操作)は、篠さん本人が手作業で行う前提とする。
- Claude Codeが担当できるのは、変更手順書・実装案・テスト手順の作成、および設計書(`docs/`)の更新までである(AGENTS.md第6項の承認境界とも一致する)。
- LINE Developers Consoleなど、Bubble以外の管理画面については個別に到達可否を確認してから判断する(LINE-03では認証済みセッションでの操作が可能だった実績がある)。

### サブエージェント(Agent tool)の使い方

- ユーザーが明示的に指示した場合、またはタスクが本当に並列化・隔離を要する場合のみサブエージェントを使う。単純なIssue作業を無闇に別セッションへ分割しない。
- 調査だけを広く行いたい場合は `Explore` エージェント、計画立案には `Plan` エージェントを使う分には差し支えない。

### `.claude/settings.json` の既知の不整合

現状の [`.claude/settings.json`](.claude/settings.json) には `Bash(git push origin main)` の許可設定が残っているが、これはAGENTS.md第4項(mainへの直接push禁止)と矛盾する。Branch Rulesetが有効な状態ではこの操作はGitHub側で拒否されるため実害は無いはずだが、設定自体は古い運用の名残であり、削除するかどうかは篠さんの判断を仰ぐこと(このファイルの担当外なので無断で書き換えない)。
