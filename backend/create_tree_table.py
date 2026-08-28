"""
create_tree_table.py
---------------------
(仮称)樹木管理システム ポートフォリオ用
Dataverse Web API を直接呼び出して「樹木マスタ」テーブルと列を自動作成するスクリプト。

事前準備:
    pip install msal requests

実行方法:
    python create_tree_table.py
    → 実行すると「https://microsoft.com/devicelogin で XXXXXXX を入力してください」
      という案内が出るので、ブラウザで自分のPower Platformアカウントでログインする。
    → 環境のURL(例: https://orgXXXXXXXX.crm7.dynamics.com)を聞かれるので入力する。
      Power Platform管理センター(admin.powerplatform.microsoft.com)の
      環境詳細ページで「環境のURL」として確認できる。

このスクリプトは何度実行しても安全(冪等)になるよう、
「すでに存在する場合はスキップして次に進む」処理を入れている。
"""

import sys
import time
import requests
import msal

from dataverse_common import save_manifest_entry

# Azure CLI/PowerShell系サンプルで広く使われている公開クライアントID。
# 個別のアプリ登録なしにデバイスコードフローで対話ログインするために使用する。
PUBLIC_CLIENT_ID = "51f81489-12ee-4a9e-aaae-a2591f45987d"
AUTHORITY = "https://login.microsoftonline.com/organizations"
API_VERSION = "v9.2"


def get_access_token(env_url: str) -> str:
    """デバイスコードフローでサインインし、Dataverse用アクセストークンを取得する。"""
    app = msal.PublicClientApplication(PUBLIC_CLIENT_ID, authority=AUTHORITY)
    scopes = [f"{env_url}/.default"]
    flow = app.initiate_device_flow(scopes=scopes)
    if "user_code" not in flow:
        raise RuntimeError(f"デバイスコードフローの開始に失敗しました: {flow}")
    print(flow["message"])  # ブラウザでの操作案内を表示
    result = app.acquire_token_by_device_flow(flow)
    if "access_token" not in result:
        raise RuntimeError(f"認証に失敗しました: {result.get('error_description')}")
    return result["access_token"]


def get_default_prefix(base: str, headers: dict) -> str:
    """既定ソリューションの発行元(publisher)から customizationprefix を取得する。"""
    url = (
        f"{base}/solutions?$filter=uniquename eq 'Default'"
        f"&$expand=publisherid($select=customizationprefix)"
    )
    resp = requests.get(url, headers=headers)
    resp.raise_for_status()
    value = resp.json()["value"]
    if not value:
        raise RuntimeError("既定の発行元(publisher)が見つかりませんでした。")
    return value[0]["publisherid"]["customizationprefix"]


def label(text: str) -> dict:
    return {
        "@odata.type": "Microsoft.Dynamics.CRM.Label",
        "LocalizedLabels": [
            {
                "@odata.type": "Microsoft.Dynamics.CRM.LocalizedLabel",
                "Label": text,
                "LanguageCode": 1041,  # 日本語
            }
        ],
    }


def entity_exists(base: str, headers: dict, logical_name: str) -> bool:
    url = f"{base}/EntityDefinitions(LogicalName='{logical_name}')"
    resp = requests.get(url, headers=headers)
    return resp.status_code == 200


def create_tree_entity(base: str, headers: dict, prefix: str) -> str:
    """樹木マスタ本体(主要な名前列=樹木番号)を作成する。"""
    logical_name = f"{prefix}_tree"
    if entity_exists(base, headers, logical_name):
        print("樹木マスタは既に存在します。作成をスキップします。")
        return logical_name

    body = {
        "@odata.type": "Microsoft.Dynamics.CRM.EntityMetadata",
        "SchemaName": f"{prefix}_Tree",
        "DisplayName": label("樹木マスタ"),
        "DisplayCollectionName": label("樹木マスタ"),
        "Description": label("(仮称)樹木管理システム ポートフォリオ 樹木マスタテーブル"),
        "OwnershipType": "UserOwned",
        "IsActivity": False,
        "HasNotes": True,
        "HasActivities": False,
        "Attributes": [
            {
                "@odata.type": "Microsoft.Dynamics.CRM.StringAttributeMetadata",
                "SchemaName": f"{prefix}_TreeNumber",
                "DisplayName": label("樹木番号"),
                "RequiredLevel": {"Value": "ApplicationRequired"},
                "MaxLength": 100,
                "FormatName": {"Value": "Text"},
                "IsPrimaryName": True,
            }
        ],
    }
    resp = requests.post(f"{base}/EntityDefinitions", headers=headers, json=body)
    if resp.status_code not in (200, 201, 204):
        raise RuntimeError(f"テーブル作成に失敗しました: {resp.status_code} {resp.text}")
    print("樹木マスタテーブルを作成しました。")
    time.sleep(3)  # メタデータ反映待ち
    return logical_name


def add_string(base, headers, logical_name, prefix, name, disp, max_len=200, memo=False):
    otype = "MemoAttributeMetadata" if memo else "StringAttributeMetadata"
    body = {
        "@odata.type": f"Microsoft.Dynamics.CRM.{otype}",
        "SchemaName": f"{prefix}_{name}",
        "DisplayName": label(disp),
        "MaxLength": max_len,
    }
    if not memo:
        body["FormatName"] = {"Value": "Text"}
    _post_attribute(base, headers, logical_name, body, disp)


def add_decimal(base, headers, logical_name, prefix, name, disp, precision=2):
    body = {
        "@odata.type": "Microsoft.Dynamics.CRM.DecimalAttributeMetadata",
        "SchemaName": f"{prefix}_{name}",
        "DisplayName": label(disp),
        "MinValue": -100000,
        "MaxValue": 100000,
        "Precision": precision,
    }
    _post_attribute(base, headers, logical_name, body, disp)


def add_date(base, headers, logical_name, prefix, name, disp):
    body = {
        "@odata.type": "Microsoft.Dynamics.CRM.DateTimeAttributeMetadata",
        "SchemaName": f"{prefix}_{name}",
        "DisplayName": label(disp),
        "Format": "DateOnly",
    }
    _post_attribute(base, headers, logical_name, body, disp)


def add_boolean(base, headers, logical_name, prefix, name, disp, true_label="あり", false_label="なし"):
    body = {
        "@odata.type": "Microsoft.Dynamics.CRM.BooleanAttributeMetadata",
        "SchemaName": f"{prefix}_{name}",
        "DisplayName": label(disp),
        "OptionSet": {
            "@odata.type": "Microsoft.Dynamics.CRM.BooleanOptionSetMetadata",
            "TrueOption": {"Value": 1, "Label": label(true_label)},
            "FalseOption": {"Value": 0, "Label": label(false_label)},
        },
    }
    _post_attribute(base, headers, logical_name, body, disp)


def add_choice(base, headers, logical_name, prefix, name, disp, options):
    body = {
        "@odata.type": "Microsoft.Dynamics.CRM.PicklistAttributeMetadata",
        "SchemaName": f"{prefix}_{name}",
        "DisplayName": label(disp),
        "OptionSet": {
            "@odata.type": "Microsoft.Dynamics.CRM.OptionSetMetadata",
            "IsGlobal": False,
            "OptionSetType": "Picklist",
            "Options": [
                {"Value": 100000 + i, "Label": label(opt)} for i, opt in enumerate(options)
            ],
        },
    }
    _post_attribute(base, headers, logical_name, body, disp)


def _post_attribute(base, headers, logical_name, body, disp):
    schema = body["SchemaName"]
    check_url = (
        f"{base}/EntityDefinitions(LogicalName='{logical_name}')"
        f"/Attributes(LogicalName='{schema.lower()}')"
    )
    if requests.get(check_url, headers=headers).status_code == 200:
        print(f"列『{disp}』は既に存在します。スキップします。")
        return
    url = f"{base}/EntityDefinitions(LogicalName='{logical_name}')/Attributes"
    resp = requests.post(url, headers=headers, json=body)
    if resp.status_code not in (200, 201, 204):
        print(f"列『{disp}』の作成に失敗しました: {resp.status_code} {resp.text}")
    else:
        print(f"列『{disp}』を作成しました。")
    time.sleep(1)


def add_self_lookup(base, headers, logical_name, prefix):
    """植替え前樹木IDの自己参照ルックアップ(1:N関係)を作成する。"""
    schema_name = f"{prefix}_tree_replantfrom_tree"
    check_url = f"{base}/RelationshipDefinitions(SchemaName='{schema_name}')"
    if requests.get(check_url, headers=headers).status_code == 200:
        print("植替え前樹木IDの関係は既に存在します。スキップします。")
        return
    body = {
        "@odata.type": "Microsoft.Dynamics.CRM.OneToManyRelationshipMetadata",
        "SchemaName": schema_name,
        "ReferencedEntity": logical_name,
        "ReferencingEntity": logical_name,
        "ReferencedAttribute": f"{prefix}_treeid",
        "Lookup": {
            "@odata.type": "Microsoft.Dynamics.CRM.LookupAttributeMetadata",
            "SchemaName": f"{prefix}_ReplantFromTreeId",
            "DisplayName": label("植替え前樹木ID"),
        },
    }
    url = f"{base}/RelationshipDefinitions"
    resp = requests.post(url, headers=headers, json=body)
    if resp.status_code not in (200, 201, 204):
        print(f"自己参照ルックアップの作成に失敗しました: {resp.status_code} {resp.text}")
    else:
        print("植替え前樹木IDの自己参照ルックアップを作成しました。")


def main():
    env_url = input(
        "Dataverse環境のURLを入力してください "
        "(例: https://orgXXXXXXXX.crm7.dynamics.com): "
    ).strip().rstrip("/")

    print("\nブラウザでのサインインが必要です。以下の案内に従ってください。\n")
    token = get_access_token(env_url)

    base = f"{env_url}/api/data/{API_VERSION}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json; charset=utf-8",
        "OData-MaxVersion": "4.0",
        "OData-Version": "4.0",
        "Accept": "application/json",
    }

    prefix = get_default_prefix(base, headers)
    print(f"\n発行元(publisher)のプレフィックスは『{prefix}』です。\n")

    logical_name = create_tree_entity(base, headers, prefix)

    # 基本のテキスト・数値列
    add_string(base, headers, logical_name, prefix, "RouteNumber", "路線番号", max_len=50)
    add_string(base, headers, logical_name, prefix, "Address", "住居表示", max_len=200)
    add_decimal(base, headers, logical_name, prefix, "TreeHeight", "樹高(m)", precision=1)
    add_decimal(base, headers, logical_name, prefix, "TrunkGirth", "幹周(cm)", precision=0)
    add_decimal(base, headers, logical_name, prefix, "CrownSpread", "枝張(m)", precision=1)
    add_string(base, headers, logical_name, prefix, "Notes", "備考", max_len=2000, memo=True)
    add_string(base, headers, logical_name, prefix, "Species", "樹種", max_len=100)

    # 選択肢列
    add_choice(base, headers, logical_name, prefix, "LeafType", "常緑落葉区分", ["常緑", "落葉"])
    add_choice(base, headers, logical_name, prefix, "SizeClass", "樹木区分", ["高木", "中木", "低木"])
    add_choice(base, headers, logical_name, prefix, "HealthStatus", "現在の健全度", ["A", "B1", "B2", "C"])
    add_choice(base, headers, logical_name, prefix, "Status", "ステータス", ["現存", "伐採済", "植替え済"])

    # 日付・Yes/No列
    add_date(base, headers, logical_name, prefix, "PlantedDate", "植樹年月日")
    add_boolean(base, headers, logical_name, prefix, "HasStake", "支柱の有無")
    add_boolean(base, headers, logical_name, prefix, "HasTag", "管理札の有無")

    # 位置情報列
    add_decimal(base, headers, logical_name, prefix, "Latitude", "緯度", precision=6)
    add_decimal(base, headers, logical_name, prefix, "Longitude", "経度", precision=6)

    # 自己参照ルックアップ(最後)
    add_self_lookup(base, headers, logical_name, prefix)

    # 検証ハーネス用にマニフェストへ記録
    save_manifest_entry("tree", "樹木マスタ", [
        {"suffix": "TreeNumber", "display": "樹木番号"},
        {"suffix": "RouteNumber", "display": "路線番号"},
        {"suffix": "Address", "display": "住居表示"},
        {"suffix": "TreeHeight", "display": "樹高(m)"},
        {"suffix": "TrunkGirth", "display": "幹周(cm)"},
        {"suffix": "CrownSpread", "display": "枝張(m)"},
        {"suffix": "Notes", "display": "備考"},
        {"suffix": "Species", "display": "樹種"},
        {"suffix": "LeafType", "display": "常緑落葉区分"},
        {"suffix": "SizeClass", "display": "樹木区分"},
        {"suffix": "HealthStatus", "display": "現在の健全度"},
        {"suffix": "Status", "display": "ステータス"},
        {"suffix": "PlantedDate", "display": "植樹年月日"},
        {"suffix": "HasStake", "display": "支柱の有無"},
        {"suffix": "HasTag", "display": "管理札の有無"},
        {"suffix": "Latitude", "display": "緯度"},
        {"suffix": "Longitude", "display": "経度"},
        {"suffix": "ReplantFromTreeId", "display": "植替え前樹木ID"},
    ])

    print("\n完了しました。Power AppsのUIで『樹木マスタ』テーブルを開いて列を確認してください。")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # noqa: BLE001
        print(f"\nエラーが発生しました: {exc}", file=sys.stderr)
        sys.exit(1)
