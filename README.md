# (仮称)樹木管理システム 構築プロジェクト

> 東京都港区の公募型プロポーザル仕様書をベースにした、個人ポートフォリオ用リポジトリ

本プロジェクトは、東京都港区が公表した「(仮称)樹木管理システム構築業務委託」の公募資料を教材として、Power Platform(Dataverse)によるフルスクラッチ相当の業務システムを個人で設計・構築したものです。実際の港区案件への提出物ではなく、公開情報を参考にした学習・ポートフォリオ目的の制作物です。

## 構成

このリポジトリは2つのパートで構成されています。

| ディレクトリ | 内容 | 技術スタック |
|---|---|---|
| [`backend/`](backend/README.md) | Dataverseのテーブル・セキュリティロールを Web API + Python でコード化(Infrastructure as Code) | Python, Dataverse Web API, Power Automate |
| [`map/`](map/README.md) | 樹木の位置をAzure Mapsで表示するPCF(PowerApps Component Framework)カスタムコントロール | TypeScript, React, azure-maps-control, PCF |

詳細なデータモデル・セキュリティロール設計・要件定義プロセス・実装進捗は [`backend/README.md`](backend/README.md) を、地図コントロールの実装・不具合修正の記録は [`map/README.md`](map/README.md) を参照してください。

## セットアップ

各ディレクトリのREADMEを参照してください。`map/` は初回のみ `npm install` が必要です(`postinstall` フックで PCF ビルドツールへの既知の不具合パッチが自動適用されます)。

---

本プロジェクトは東京都港区が公表した公募資料を参考にした個人の学習・ポートフォリオ目的の制作物であり、港区への正式な提案書・提出物ではありません。
