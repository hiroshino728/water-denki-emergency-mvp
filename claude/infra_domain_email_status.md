# mizudenki-kyukyu.jp インフラ・メール基盤 状況記録

このファイルは `mizudenki-kyukyu.jp` のDNS・メール基盤に関する作業記録のSSOT。作業の節目ごとに追記する。

## 移行の背景・ゴール

- 受信メール基盤を ImprovMX（無料転送）から Purelymail（$10/年・Simple pricing）へ移行する。
- Gmail（`shino0728@gmail.com`）から `info@mizudenki-kyukyu.jp` として送受信できる状態にする。
- 実行順序：フェーズ0（DNS委任確認）→ フェーズ1（Purelymailアカウント作成・人間作業）→ フェーズ2（XServer DNSレコード変更）→ フェーズ3（DNS反映検証）→ フェーズ4（Purelymailメールボックス作成）→ フェーズ5（Gmail送信設定・人間作業）→ フェーズ6（動作確認）→ フェーズ7（後片付け）。

## フェーズ0：DNS委任確認（完了）

- **懸念事項**：直近の調査で、ネームサーバー設定がXServerレンタルサーバー用（`ns1〜5.xserver.jp`）のままで、DNSレコードを実際に登録しているXServerドメイン側DNS（`ns1〜3.xdomain.ne.jp`）に委任されていない疑い（"lame delegation"）が指摘されていた。
- **2026-08-22 実施の確認結果**：Google Public DNS (`dns.google/resolve`) に対する以下のクエリはすべて `Status: 0`（正常）で、SERVFAILは再現しなかった。

  | レコード | 結果 |
  |---|---|
  | NS | `ns1.xdomain.ne.jp` / `ns2.xdomain.ne.jp` / `ns3.xdomain.ne.jp`（正しく委任済み） |
  | MX | `10 mx1.improvmx.com` / `20 mx2.improvmx.com`（ImprovMX設定通り、正常稼働中） |
  | TXT (SPF) | `v=spf1 include:spf.improvmx.com ~all` |
  | A | `185.199.108.153` / `.109.153` / `.110.153` / `.111.153`（GitHub Pages） |

- **判定**：フェーズ0の完了条件（NSクエリがSERVFAILではなく `ns1〜3.xdomain.ne.jp` を正しく返す）は満たされている。ネームサーバー設定変更の作業は不要と判断し、完了扱いとしてフェーズ1へ進む。
- 備考：以前の診断時点から状況が変わった経緯（誰がいつ直したか等）は本セッションでは特定していない。

## フェーズ1：Purelymailアカウント作成・ドメイン追加（人間作業・篠さん専任）

**ステータス：完了（篠さんによりアカウント作成・ドメイン追加済み）。**

Purelymail管理画面から以下の値を取得済み：

- `purelymail_ownership_proof`（TXTレコード用）：
  `ad9b0698242f909ba8f894d69e941b146f7344343f9bbcea184d7e73252ebd2bb139915d2da6b4771127468c18a535275ad684d20853757a827235581a7eaafe`
- DKIM用CNAMEレコード3件：

  | Name | Content |
  |---|---|
  | `purelymail1._domainkey` | `key1.dkimroot.purelymail.com` |
  | `purelymail2._domainkey` | `key2.dkimroot.purelymail.com` |
  | `purelymail3._domainkey`（※篠さんからの共有時は`purelymail3_domainkey`とドット抜けで届いたため、1・2件目のパターンに合わせて訂正。要最終確認） | `key3.dkimroot.purelymail.com` |

## フェーズ2：XServer DNSレコードの変更（完了）

**2026-08-22 実施。** XServerドメイン管理画面（DNSレコード設定、`id_domain=22785435`）を、篠さんの認証済みセッション（Claude in Chrome経由）で操作した。

実施内容：

1. 以下7件を新規追加：

   | ホスト名 | 種別 | 内容 | TTL | 優先度 |
   |---|---|---|---|---|
   | `@` | MX | `mailserver.purelymail.com` | 3600 | 50 |
   | `@` | TXT | `v=spf1 include:_spf.purelymail.com ~all` | 3600 | - |
   | `@` | TXT | `purelymail_ownership_proof=ad9b0698242f909ba8f894d69e941b146f7344343f9bbcea184d7e73252ebd2bb139915d2da6b4771127468c18a535275ad684d20853757a827235581a7eaafe` | 3600 | - |
   | `purelymail1._domainkey` | CNAME | `key1.dkimroot.purelymail.com` | 3600 | - |
   | `purelymail2._domainkey` | CNAME | `key2.dkimroot.purelymail.com` | 3600 | - |
   | `purelymail3._domainkey` | CNAME | `key3.dkimroot.purelymail.com` | 3600 | - |
   | `_dmarc` | TXT | `v=DMARC1; p=none; rua=mailto:info@mizudenki-kyukyu.jp` | 3600 | - |

2. 既存のImprovMX用レコードを削除：
   - MX `mx1.improvmx.com`（優先度10）
   - MX `mx2.improvmx.com`（優先度20）
   - TXT (SPF) `v=spf1 include:spf.improvmx.com ~all`

- A/CNAME（`www` → GitHub Pages）は変更していない。
- 削除操作は1件ずつ確認画面で対象レコードを確認したうえで実行した。

## フェーズ3：DNS反映の検証

**2026-08-22 実施。dns.google経由の検証は完了。** フェーズ2のレコード変更直後に確認したところ、想定していた反映待ち時間（数時間〜24-48時間）よりも早く、すべて期待通りに解決した。

```
MX:              50 mailserver.purelymail.com
TXT (ownership): purelymail_ownership_proof=ad9b0698...（フェーズ1の値と一致）
TXT (SPF):       v=spf1 include:_spf.purelymail.com ~all
CNAME (DKIM1):   purelymail1._domainkey → key1.dkimroot.purelymail.com
TXT (DMARC):     v=DMARC1; p=none; rua=mailto:info@mizudenki-kyukyu.jp
```

- **篠さんによるPurelymail側「Check DNS records」実施結果（2026-08-22）**：DNSレコードは受理（acceptable）。ただし以下の警告あり：
  - `No DMARC record found.`（警告）
  - MX record found. / SPF record found. / DKIM record purelymail1〜3._domainkey found.（いずれも正常）
- DMARC警告の原因調査：`dns.google` / Cloudflare DNS (`cloudflare-dns.com`) / XServer権威ネームサーバー(`ns1.xdomain.ne.jp`)に直接問い合わせたところ、いずれも `_dmarc.mizudenki-kyukyu.jp TXT` = `v=DMARC1; p=none; rua=mailto:info@mizudenki-kyukyu.jp` を正しく返しており、レコード自体に問題はない。Purelymail側の一時的なキャッシュ(レコード追加前の結果が残っている可能性)によるものと推測され、時間を置いた再チェックで解消する見込み。ブロッカーではないと判断し、フェーズ4に進む。

## フェーズ4：Purelymail側メールボックス作成・受信設定（完了）

- **メールボックス作成**：篠さんご自身が実施（パスワード設定を伴うため、エージェントの安全ルール上、アカウント作成・パスワード入力は代行不可と判断し、人間作業とした）。
- **管理画面へのログイン不具合**：エージェント(Claude in Chrome)からPurelymail管理画面(`https://purelymail.com/manage`)にアクセスした際、篠さんのアカウント(`shino0728@purelymail.com`、Chrome保存パスワードで自動入力済み)でログインしようとしたところ、パスワードは合っているにも関わらずログイン画面に戻る現象が発生。原因未特定(Cookie/拡張機能/2段階認証等の可能性を提示したが、切り分けは未実施)。エージェントはパスワードでの認証操作自体を代行できないため、この時点で引き継ぎ、篠さんご自身がログインして手動で設定を完了した。
- **受信転送設定**：篠さんご自身がPurelymail管理画面のRouting Rules(想定)で、`info@mizudenki-kyukyu.jp` 宛のメールを `shino0728@gmail.com` へ転送するルールを設定し、完了を確認。エージェント側では画面を直接確認できていないため、実際のルール内容(Also send/Forwardのどちらを選んだか等)の詳細記録はなし。

## フェーズ5：Gmail「名前を付けて送信」設定【人間作業・篠さん専任】（完了）

篠さんご自身がGmail設定でSMTP (`smtp.purelymail.com`) を使った `info@mizudenki-kyukyu.jp` の送信元追加・確認メールでの確認を完了。

## フェーズ6：動作確認（完了）

篠さんにより、外部アドレスからの `info@mizudenki-kyukyu.jp` 宛送信→Gmail受信、およびGmailから `info@` を送信元とした送信の両方向を確認いただき、結果はOK。SPF/DKIM/DMARCの詳細な判定結果（mail-tester.com等でのスコア等）は本セッションでは個別に受け取っていない。

## フェーズ7：後片付け・記録更新（完了）

- ImprovMX側の設定：フェーズ2でXServer DNS上のImprovMX関連レコード（MX×2、SPF TXT）はすでに削除済み。ImprovMXアカウント自体は無料枠のため解約不要（篠さんの判断に委ねる）。
- 本記録ファイル（`claude/infra_domain_email_status.md`）への追記・GitHubへのコミットは各フェーズ完了時に都度実施済み。
- PR: [#58](https://github.com/hiroshino728/water-denki-emergency-mvp/pull/58)。AGENTS.md第3項に基づき、マージは篠さんのレビュー・判断を経て実施する（エージェントはPR作成までを担当し、自動マージしない）。

## 移行ステータス：完了

ImprovMX → Purelymailへのメール基盤移行、およびGmailからの `info@mizudenki-kyukyu.jp` 送受信設定は、フェーズ0〜7すべて完了。
