# 廃止したアプローチ: Entra ID(AAD)ポップアップ認証によるAzure Maps連携

## 何を試みたか

TreeMapControl(PCF)からAzure Mapsを呼び出す際、当初はAzure MapsのEntra ID(AAD)認証を使う方針だった。具体的には以下を構築した。

- `setup_azure_maps_aad.ps1` — Azure ADアプリ登録(SPA)、サービスプリンシパル作成、Azure Mapsアカウントへの「Azure Maps Data Reader」ロール割り当てを自動化
- `create_popup_webresource.py` / `TreeMapControl/popup.html` — MSALのポップアップ認証で使うリダイレクト先Webリソースの作成
- `update_redirect_uri.py` — アプリ登録のリダイレクトURIを環境のURLに合わせて更新
- `verify_aad_setup.py` — 上記一式が実際にAzure/Dataverse側に作成されているかの検証

## なぜ廃止したか

MSALのポップアップ認証(`loginPopup`)を、Power AppsのPCFが動くiframeの入れ子構造の中で呼び出すと、`timed_out`エラーが解消できなかった。Power Appsのモデル駆動アプリ自体が複数のiframeで構成されており、ポップアップからのリダイレクト完了をMSALが正しく検知できないことが原因と推測される。

複数の切り分け(リダイレクトURIの確認、popup.htmlの内容確認等)を行ったが解決に至らず、認証方式そのものを変更する判断をした。

## 何に切り替えたか

Dataverseの「環境変数」にAzure Mapsのサブスクリプションキーを保存し、PCFは`context.webAPI`(Dataverseに元々サインイン済みの状態)経由でその値を取得する方式に変更した(`create_env_variable.py` / `TreeMapControl/index.ts`の`fetchSubscriptionKey()`)。

この方式の利点:
- 追加のブラウザ認証・ポップアップが一切発生しない
- サブスクリプションキーがソースコードに書かれないため、GitHub公開時の漏洩リスクがない
- キーをローテーションしてもコードの再デプロイが不要

## このフォルダの位置づけ

ここにあるファイルは**現在使われていない**。`ControlManifest.Input.xml`からも`popup.html`のリソース参照と`login.microsoftonline.com`のドメイン許可は削除済み。動作しないアプローチの記録として、意思決定の過程を残すために保管している。
