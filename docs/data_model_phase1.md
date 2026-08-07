# データモデル設計書(フェーズ1 MVP)
## 水道・電気トラブル マッチングプラットフォーム

---

## 0. 設計方針

- **実装はBubble、設計思想はRDB前提。** Bubble標準DBで作るが、将来Supabase(PostgreSQL)へ切り出しても違和感のない構造にする。
- **命名規則は将来のSQLテーブル名を意識する。** Bubbleの Thing名は単数形の日本語/英語どちらでも構わないが、本設計書ではAPI・DB共通言語として**英語スネークケース相当**の名称を正とする(Bubble画面上の表示名は日本語でよい)。
- **Bubbleの自動採番ID(unique id)に業務ロジックを依存させない。** 各エンティティに人間可読な業務ID(job_no, invoice_no等)を別フィールドとして持たせる。これによりBubble以外のシステム(n8n, 将来のSupabase, AI Agent)からも一貫した参照が可能になる。
- **Option Set(Bubble機能)は「将来マスタテーブル化できるもの」に限定して使う。** カテゴリ・地域・ステータスなど、将来運用ルールが増える可能性があるものはOption Setではなく「マスタ用Thing(テーブル)」として設計する。
- **すべての主要エンティティに `created_at` `updated_at` `status` `source_channel` を持たせる。** `source_channel` は将来AIエージェント(電話AI/LINE AI/Web/営業AI等)がどの経路でこのレコードを作ったかを記録するための布石。

---

## 1. エンティティ一覧(全体像)

| # | エンティティ名 | 役割 |
|---|---|---|
| 1 | Customer | サービス利用者(顧客) |
| 2 | Partner | 加盟店・提携職人(サプライサイド) |
| 3 | PartnerSkill | 加盟店の対応可能カテゴリ・地域(中間テーブル) |
| 4 | Category | トラブル種別マスタ(水漏れ・漏電など) |
| 5 | Region | 対応地域マスタ |
| 6 | Job | 案件(マッチングの中心エンティティ) |
| 7 | JobStatusLog | 案件のステータス変化履歴(ログ) |
| 8 | Invoice | 請求 |
| 9 | Payment | 決済 |
| 10 | Review | レビュー・評価 |
| 11 | InquiryLog | 問い合わせログ(AI対応・電話・LINE等の一次窓口ログ) |
| 12 | Agent(将来用) | どのAIエージェント/人間オペレーターが対応したかの記録 |

---

## 2. エンティティ詳細

### 2.1 Customer(顧客)

| フィールド名 | 型 | 説明 |
|---|---|---|
| customer_no | text(unique) | 業務ID。例: `C-000123` |
| name | text | 氏名 |
| phone | text | 電話番号(電話AI・SMS連携のキーになる) |
| line_user_id | text(nullable) | LINE公式アカウントのuserId(LINE連携用) |
| email | text(nullable) | メール |
| address | text | 住所(GPS/地図連携の元データ) |
| region_id | Region(ref) | 対応地域マスタへの参照 |
| status | text | active / blocked 等 |
| source_channel | text | web / line / phone_ai / referral 等 |
| created_at / updated_at | datetime | |

**設計メモ:** `phone` を実質的な名寄せキーにする。電話AI・LINE・Webのどこから来た顧客でも、電話番号で同一人物として名寄せできるようにしておくと、将来複数チャネルを統合する際に致命的な手戻りを避けられる。

---

### 2.2 Partner(加盟店・提携職人)

| フィールド名 | 型 | 説明 |
|---|---|---|
| partner_no | text(unique) | 業務ID。例: `P-000045` |
| company_name | text | 屋号・会社名 |
| contact_name | text | 担当者名 |
| phone | text | |
| email | text | |
| license_info | text/file | 資格・許認可情報(審査用) |
| insurance_info | text/file | 保険加入情報 |
| screening_status | text | pending / approved / rejected |
| rating_avg | number | レビュー平均(Review集計値のキャッシュ) |
| commission_rate | number | 手数料率(粗利計算の元) |
| status | text | active / suspended |
| created_at / updated_at | datetime | |

**設計メモ:** `screening_status` を分けることで、審査プロセス(将来AIによる書類読み取り+人の最終承認)をワークフロー化しやすくする。

---

### 2.3 PartnerSkill(中間テーブル: 加盟店 × 対応カテゴリ × 対応地域)

| フィールド名 | 型 | 説明 |
|---|---|---|
| partner_id | Partner(ref) | |
| category_id | Category(ref) | |
| region_id | Region(ref) | |
| priority | number | マッチング優先度(将来の割り当てAIが利用) |

**設計メモ:** BubbleのList機能で済ませず、あえて中間テーブルとして独立させる。将来「このカテゴリ×この地域で対応可能な加盟店を検索」というクエリがRDBでもBubbleでも同じロジックで書けるようにするため。

---

### 2.4 Category(トラブル種別マスタ)

| フィールド名 | 型 | 説明 |
|---|---|---|
| category_code | text(unique) | 例: `water_leak`, `electrical_short` |
| display_name | text | 画面表示名(日本語) |
| parent_category_id | Category(ref, nullable) | 将来の階層化に備える |

---

### 2.5 Region(対応地域マスタ)

| フィールド名 | 型 | 説明 |
|---|---|---|
| region_code | text(unique) | 例: `tokyo_minato` |
| display_name | text | |
| prefecture | text | 都道府県 |
| city | text | 市区町村 |

---

### 2.6 Job(案件)★中核エンティティ

| フィールド名 | 型 | 説明 |
|---|---|---|
| job_no | text(unique) | 業務ID。例: `J-2026-000789` |
| customer_id | Customer(ref) | |
| partner_id | Partner(ref, nullable) | マッチング成立後に確定 |
| category_id | Category(ref) | |
| region_id | Region(ref) | |
| description | text | 症状・依頼内容(将来AIが自然文から自動分類する対象) |
| urgency | text | emergency / normal |
| status | text | new → matched → in_progress → completed → cancelled |
| requested_amount | number(nullable) | 見積金額 |
| final_amount | number(nullable) | 最終金額(粗利計算のベース) |
| gross_profit | number(nullable) | 粗利(final_amount - partner支払額) ※フェーズ2データ分析の核 |
| source_channel | text | web / line / phone_ai / repeat |
| assigned_by | text | manual / auto_match / ai_agent |
| created_at / updated_at | datetime | |
| completed_at | datetime(nullable) | |

**設計メモ:** ここがフェーズ2で言及されていた「どの地域で、どんなトラブルが、いくらで解決され、粗利がどれくらい出たか」のログの中心。`gross_profit` を集計しやすい形で持たせておくことが、フェーズ2の意思決定データの生命線になる。

---

### 2.7 JobStatusLog(案件ステータス変化履歴)

| フィールド名 | 型 | 説明 |
|---|---|---|
| job_id | Job(ref) | |
| from_status | text | |
| to_status | text | |
| changed_by | text | customer / partner / admin / ai_agent |
| changed_at | datetime | |

**設計メモ:** Jobのstatusを直接上書きするのではなく、変化のたびにログを残す設計にする。将来「AIエージェントがどこで介入したか」を分析する際の生データになる。

---

### 2.8 Invoice(請求)

| フィールド名 | 型 | 説明 |
|---|---|---|
| invoice_no | text(unique) | 例: `INV-2026-000456` |
| job_id | Job(ref) | |
| customer_id | Customer(ref) | |
| amount | number | |
| tax_amount | number | |
| issue_date | date | |
| due_date | date | |
| status | text | draft / issued / paid / overdue / cancelled |

---

### 2.9 Payment(決済)

| フィールド名 | 型 | 説明 |
|---|---|---|
| payment_no | text(unique) | |
| invoice_id | Invoice(ref) | |
| amount | number | |
| method | text | credit_card / bank_transfer / cash |
| status | text | pending / succeeded / failed / refunded |
| paid_at | datetime(nullable) | |
| external_transaction_id | text(nullable) | 決済代行会社(Stripe等)のID。**外部システムとの紐付けキー** |

**設計メモ:** 決済・請求は事業の信頼性に直結する部分。ここは前回お伝えした通り、実装前に一度、決済・会計に詳しい専門家のレビューを推奨。

---

### 2.10 Review(レビュー)

| フィールド名 | 型 | 説明 |
|---|---|---|
| job_id | Job(ref) | |
| customer_id | Customer(ref) | |
| partner_id | Partner(ref) | |
| rating | number(1-5) | |
| comment | text | |
| is_flagged | yes/no | 不正レビュー検知(将来AIで自動フラグ)用 |
| created_at | datetime | |

---

### 2.11 InquiryLog(問い合わせログ)★AI接続の入口

| フィールド名 | 型 | 説明 |
|---|---|---|
| inquiry_no | text(unique) | |
| customer_id | Customer(ref, nullable) | 未登録者の問い合わせもあるためnullable |
| channel | text | web_chat / line / phone_ai / sms / email |
| raw_content | text | 問い合わせの生データ(音声書き起こし/チャット文面) |
| ai_summary | text(nullable) | AIによる要約(将来のAI受付が生成) |
| resulted_job_id | Job(ref, nullable) | 案件化した場合のリンク |
| handled_by | text | ai_agent / human |
| created_at | datetime | |

**設計メモ:** これが将来の「電話AI」「AI受付」「LINE AI」の共通着地点。チャネルが増えても、このテーブル1つに集約しておけば、n8n側の実装もシンプルになる。

---

## 3. API設計原則(n8n / 将来のAI Agentとの接続)

1. **書き込み系(Job作成・ステータス更新・InquiryLog登録)はBubbleのWorkflow APIを主に使う。**
   理由: Workflow API側でバリデーション・権限チェック・通知処理をワークフローとして一元管理できるため、n8n側のロジックを薄く保てる。
2. **読み取り系(加盟店検索・案件一覧取得)はBubbleのData APIを使う。**
3. **すべての外部連携エンドポイントは `/api/1.1/wf/xxx` のように機能単位で命名し、n8n側では1つのAIエージェント/チャネルにつき「呼び出すエンドポイントのリスト」をドキュメント化しておく。**
   → 将来Supabaseへ移行する際、この「呼び出し一覧」がそのまま移行チェックリストになる。
4. **認証はAPIトークンではなく、可能な限りチャネルごとの発行キーを分ける。**(電話AI用、LINE用など)漏洩時の影響範囲を限定するため。

---

## 4. 命名規則まとめ(将来のRDB移行チェックリスト)

- テーブル(Thing)名: 単数形・英語ベース(Job, Customer, Partner...)
- フィールド名: スネークケース相当(created_at, job_no...)
- 参照フィールド: `◯◯_id` という名前で統一
- 業務ID: 各エンティティに `◯◯_no` を持たせ、Bubble内部IDに依存しない
- ステータス系: 自由記述にせず、必ず決まった選択肢(new/matched/completed等)に統一し、どこかにステータス一覧表を別途保持する

---

## 5. 次のアクション(提案)

- [ ] 上記モデルをレビューいただき、フィールドの過不足を確認
- [ ] `Job.status` の状態遷移図(ステートマシン)を別途作成
- [ ] Bubble上での実装順序(Customer→Partner→Category/Region→Job→Invoice→Payment→Reviewの順を想定)を確認
- [ ] InquiryLogとJobの紐付けロジック(問い合わせ→案件化のワークフロー)を詳細設計
