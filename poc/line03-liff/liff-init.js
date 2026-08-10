/**
 * LINE-03: LIFF + Bubble PoC — LIFF初期化スクリプト
 *
 * 目的：BubbleのRun Javascript要素（Toolboxプラグイン等）に貼り付け、
 *       LIFFを初期化してLINE User Id / 表示名を取得し、
 *       Bubble側のコールバック関数（bubble_fn_*）へ値を渡す。
 *
 * 前提：
 *   - このページを開く前に、LINE Developers ConsoleのLIFFアプリ設定で
 *     エンドポイントURLがこのBubbleページのURLに設定されていること。
 *   - ページ内でLIFF SDK（https://static.line-scdn.net/liff/edge/2/sdk.js）が
 *     事前に読み込まれていること（Bubbleの「Page HTML header」等で読み込む想定）。
 *
 * 使い方：
 *   Bubble側のワークフローで、以下のコールバックを定義しておく（Toolbox準拠）。
 *   - bubble_fn_userid(userId: string)
 *   - bubble_fn_displayname(displayName: string)
 *   - bubble_fn_error(message: string)  // 任意。異常系(TC-06)の可視化用
 *
 * 参照：docs/poc/LINE-03-liff-bubble-poc.md
 */
(function () {
  var LIFF_ID = "2011043480-hLNRE7GE";

  function log() {
    var args = Array.prototype.slice.call(arguments);
    args.unshift("[line03-liff]");
    console.log.apply(console, args);
  }

  function reportError(stage, error) {
    var message = stage + ": " + (error && error.message ? error.message : String(error));
    console.error("[line03-liff]", message);
    if (typeof bubble_fn_error === "function") {
      bubble_fn_error(message);
    }
  }

  if (typeof liff === "undefined") {
    reportError(
      "sdk-load",
      new Error("LIFF SDKが読み込まれていません。Bubbleのページ設定でsdk.jsの読み込みを確認してください。")
    );
    return;
  }

  liff
    .init({ liffId: LIFF_ID })
    .then(function () {
      log("liff.init OK");

      // TC-06: 未ログイン等の異常系確認
      // 通常、LINEアプリ内(LIFFブラウザ)で開けば自動的にログイン済みになる。
      // 外部ブラウザから直接開いた場合など、未ログインならログイン画面へ誘導する。
      if (!liff.isLoggedIn()) {
        log("not logged in -> liff.login()");
        liff.login();
        return null; // login()はリダイレクトを伴うため、以降の処理はここで終了
      }

      return liff.getProfile();
    })
    .then(function (profile) {
      if (!profile) {
        // liff.login() によるリダイレクト待ちのケース
        return;
      }

      // LINE User IDや表示名は個人識別情報のためログへ出力しない。
      log("profile acquired");

      if (typeof bubble_fn_userid === "function") {
        bubble_fn_userid(profile.userId);
      } else {
        reportError("callback", new Error("bubble_fn_userid が定義されていません"));
      }

      if (typeof bubble_fn_displayname === "function") {
        bubble_fn_displayname(profile.displayName);
      } else {
        reportError("callback", new Error("bubble_fn_displayname が定義されていません"));
      }
    })
    .catch(function (error) {
      reportError("liff.init/getProfile", error);
    });

  // --- P1 (TC-08, 任意・並行調査): openid scope + getIDToken() ---------------
  // LINE-03の完了条件には含めない。scopeに openid を追加した場合のみ有効化して試す。
  // 本実装(LINE-05以降)でのID token検証方式は、本実装時にLINE公式ドキュメントを
  // 確認のうえ別途確定するため、ここでは調査目的の参考実装にとどめる。
  //
  // liff.init({ liffId: LIFF_ID }).then(function () {
  //   var idToken = liff.getIDToken();
  //   // IDトークンは秘密情報のためログへ出力しない。
  //   if (typeof bubble_fn_setIdToken === "function") {
  //     bubble_fn_setIdToken(idToken);
  //   }
  // });
})();
