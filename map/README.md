# 樹木マップ(Azure Maps PCFコントロール)

> 樹木の位置情報をAzure Maps上にピン表示する、PowerApps Component Framework(PCF)カスタムコントロール

[`../backend/`](../backend/README.md) で構築したDataverseの「樹木マスタ」テーブル(緯度・経度・健全度)をデータセットとして受け取り、地図上に健全度別の色分けピンとして表示する。港区仕様書の機能要件「地図」区分(全10項目)に対応する部分。

## 技術スタック

- PowerApps Component Framework(PCF) / `control-type="virtual"`(React制御)
- TypeScript, React 16
- azure-maps-control(Azure Maps Web SDK)
- Dataverse 環境変数(Azure Mapsサブスクリプションキーの安全な受け渡し)

## アーキテクチャ: 認証方式

Azure Mapsの認証は、Dataverseの「環境変数」にサブスクリプションキーを保存し、PCFが`context.webAPI`(Dataverseに元々サインイン済みの状態)経由で取得する方式を採用している。追加のブラウザ認証は一切発生しない。

当初はEntra ID(AAD)のポップアップ認証を試みたが、Power AppsのPCFが動くiframeの入れ子構造に起因する`timed_out`エラーが解消できず断念した。その経緯・当時のコードは [`deprecated/`](deprecated/README.md) に記録している。

## ハーネス設計

### 構築
- `create_env_variable.py` — Azure Mapsサブスクリプションキーを、Dataverseの環境変数として安全に登録する
- `TreeMapControl/` — PCF本体。`npm run build` → `pac pcf push --publisher-prefix new` でデプロイ

### 検証・診断
バックエンド側(`verify_schema.py`等)と同じ「自己申告した期待値と実環境を突合する」パターンに加え、今回の障害切り分けの過程で以下の読み取り専用診断スクリプトを追加した。

- `verify_pcf_control.py` — `pcf_manifest.json`(自己申告)を元に、`customcontrols`への登録有無を検証
- `diagnose_map_binding.py` — コントロールが実際にビュー(savedquery)・フォーム(systemform)にバインドされているかをDataverse Web APIから直接確認
- `dump_view_layout.py` — 対象ビューの`layoutxml`を生で出力し、コントロール設定の詳細を確認
- `check_env_var_value.py` — 環境変数に保存された値を、Azure Maps REST APIに対して直接テストして有効性を検証
- `check_view_fetchxml.py` — 対象ビューの`fetchxml`(絞り込み条件)と、Dataverse上の実データを直接確認

### ビルドツールの既知の不具合への対処
PCFの標準ビルドツール(`pcf-scripts`)は`node_modules`配下のファイルまで無条件にBabelでトランスパイルしてしまい、`azure-maps-control`のような既製バンドルのWeb Worker内コードを壊すことがある(`_toArray is not defined`等のランタイムエラー)。`npm install`のたびに`node_modules`内の`pcf-scripts`を自動パッチする`fix-pcf-webpack.js`を`postinstall`フックとして整備し、再現性を担保している。

## 不具合修正の記録

開発中に発生し、実際に原因を特定・修正した不具合。

1. **`feature-usage`宣言の値が無効** — `WebAPI.retrieveMultipleRecords`ではなく`WebAPI`が正しい値だった。ビルドは通るがランタイムで`context.webAPI`呼び出しが失敗する不具合
2. **対象ビューが既定ビューでなかった** — コントロール自体は正しく設定されていたが、ビュー切り替えが必要なことに気づいていなかった
3. **`pcf-scripts`によるnode_modulesの誤トランスパイル** — 上記「ビルドツールの既知の不具合」を参照。地図タイルが白いまま表示されない原因だった
4. **初回コールド起動時のインスタンス作り直しによる再描画取りこぼし** — データセットのロードと連動してコントロールのインスタンス自体が複数回(観測上2〜3回)作り直され、そのたびに非同期のキー取得→`notifyOutputChanged()`のやり直しが発生。`setTimeout`での遅延では作り直しの頻度に負けて解消しきれなかった。最終的に、取得したキーをインスタンスフィールドではなく**モジュールスコープ**にキャッシュする方式に変更し、2回目以降のインスタンスは`updateView()`の初回呼び出しで同期的にキャッシュ済みの値を使えるようにして、競合そのものを起きなくして解消
5. **ドラッグ操作が地図全体のパン操作と競合する** — ポイントのドラッグを実装した際、`mousedown`時点で地図のパン操作(`dragPanInteraction`)を無効化していたが、地図側のパン処理と競合し、ポイントではなく地図全体が動いてしまっていた。ポイントに**マウスが乗った時点(`mouseenter`)**で先にパン操作を無効化しておく方式に変更して解消
6. **一部の樹木しか地図に表示されない** — `paging.setPageSize(500)`を`init()`で設定していたが、初回の読み込みはその設定が反映される前にプラットフォーム既定の(より小さい)ページサイズで走ってしまい、300件中の一部しか地図に表示されていなかった。「最新の情報に更新」を手動で押すと全件表示されることから、ページングの取りこぼしと推測し、ビューの`fetchxml`とDataverse上の実データを直接確認して絞り込み条件の問題ではないことを切り分けた上で特定。`hasNextPage`が立っている間`loadNextPage()`を呼び続けて全件読み込む実装に変更して解消

いずれも「デプロイは成功するが動かない」系の不具合で、Dataverse Web APIへの直接クエリ・Azure Maps REST APIへの直接テスト・ブラウザコンソールログの精読を組み合わせて原因を切り分けた。

## セットアップ手順

1. `npm install`(初回のみ。`postinstall`で`pcf-scripts`への既知不具合パッチが自動適用される)
2. `create_env_variable.py`でAzure Mapsサブスクリプションキーを環境変数として登録
3. `cd TreeMapControl && npm run build`
4. `pac pcf push --publisher-prefix new`でデプロイ
5. Power Apps側で対象ビュー(「樹木マップ」)にこのコントロールが設定されていることを確認

## 実装状況

機能要件「地図」区分(10項目)のうち、以下を実装・動作確認済み。

- ポイント表示・健全度による色分け(#26)
- ポイントクリックでの樹木情報画面への遷移(#28)
- 空き地クリックでの新規登録(#29)
- ドラッグによる位置修正・緯度経度の再取得(#30, #31)
- 新設/撤去に応じた地図表示変更(#32、既存の再描画の仕組みで対応)

「管理者アカウント」という要件は、特定のロール名にハードコードせず、`context.utils.hasEntityPrivilege()`でDataverseの実際の更新/作成権限を判定する設計にしている。ロール構成が変わってもコード変更が不要。

詳細な項目別の状況は [`../backend/機能要件_アーキテクチャ選定マッピング_v2.xlsx`](../backend/機能要件_アーキテクチャ選定マッピング_v2.xlsx) の「実装状況」列を参照。

---

本プロジェクトは東京都港区が公表した公募資料を参考にした個人の学習・ポートフォリオ目的の制作物であり、港区への正式な提案書・提出物ではありません。
