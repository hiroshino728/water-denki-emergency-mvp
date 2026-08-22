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

**ステータス：未着手。篠さんの作業待ち。**

Claude Codeは以下を代行しない（アカウント作成・支払いに該当するため）：

1. purelymail.com でアカウント作成（Simple pricing $10/年を推奨）。
2. Purelymail管理画面で `mizudenki-kyukyu.jp` をドメインとして追加。
3. 以下の値をダッシュボード表示のまま控えて共有：
   - `purelymail_ownership_proof` の値（TXTレコード用）
   - DKIM用CNAMEレコード3件（`purelymail1〜3._domainkey` とそれぞれの向き先）

これらの値が揃い次第、フェーズ2（XServer DNSレコード変更）に進む。

## フェーズ2〜7

未着手。フェーズ1で値を受け取り次第、このファイルに追記しながら進める。
