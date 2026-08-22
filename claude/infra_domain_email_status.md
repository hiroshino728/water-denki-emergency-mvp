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

## フェーズ2〜7

フェーズ2（XServer DNSレコード変更）の作業方法について篠さんに確認中。確認後、このファイルに追記しながら進める。
