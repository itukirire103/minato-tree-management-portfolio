# (仮称)樹木管理システム 構築プロジェクト

> 東京都港区の公募型プロポーザル仕様書をベースにした、個人ポートフォリオ用リポジトリ

本プロジェクトは、東京都港区が公表した「(仮称)樹木管理システム構築業務委託」の公募資料を教材として、Power Platform(Dataverse)によるフルスクラッチ相当の業務システムを個人で設計・構築したものです。実際の港区案件への提出物ではなく、公開情報を参考にした学習・ポートフォリオ目的の制作物です。

## 構成

このリポジトリは2つのパートで構成されています。

| ディレクトリ | 内容 | 技術スタック |
|---|---|---|
| [`backend/`](backend/README.md) | Dataverseのテーブル・セキュリティロールを Web API + Python でコード化(Infrastructure as Code) | Python, Dataverse Web API, Power Automate |
| `map/` | 樹木の位置をAzure Mapsで表示するPCF(PowerApps Component Framework)カスタムコントロール | TypeScript, React, azure-maps-control, PCF |

詳細なデータモデル・セキュリティロール設計・要件定義プロセス・実装進捗は [`backend/README.md`](backend/README.md) を参照してください。

`map/` は現時点では専用READMEを未整備です(TreeMapControlの実装、Azure Maps連携、PCFビルドツールの既知の不具合(node_modules誤トランスパイル)への対処である `fix-pcf-webpack.js` などが含まれます)。

## セットアップ

各ディレクトリのREADME・スクリプト内コメントを参照してください。`map/` は初回のみ `npm install` が必要です(`postinstall` フックで PCF ビルドツールへの既知の不具合パッチが自動適用されます)。

---

本プロジェクトは東京都港区が公表した公募資料を参考にした個人の学習・ポートフォリオ目的の制作物であり、港区への正式な提案書・提出物ではありません。
