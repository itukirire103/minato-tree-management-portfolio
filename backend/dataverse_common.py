"""
dataverse_common.py
--------------------
(仮称)樹木管理システム ポートフォリオ用
複数のテーブル作成スクリプトから共通で使うヘルパー関数群。

このファイル単体では何もしない。各テーブル作成スクリプト(create_xxx_table.py)から
import して使う。
"""

import json
import os
import time
import requests
import msal

PUBLIC_CLIENT_ID = "51f81489-12ee-4a9e-aaae-a2591f45987d"
AUTHORITY = "https://login.microsoftonline.com/organizations"
API_VERSION = "v9.2"

# 検証ハーネス(verify_schema.py)が参照する「実際に作成したはずの列」の台帳ファイル。
# 各テーブル作成スクリプトが実行完了時にここへ自己申告する。
MANIFEST_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "schema_manifest.json")


def load_manifest() -> dict:
    if not os.path.exists(MANIFEST_FILE):
        return {}
    with open(MANIFEST_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_manifest_entry(entity_suffix: str, entity_display: str, columns: list):
    """
    entity_suffix: プレフィックスを除いたテーブルの論理名(例: "tree")
    entity_display: テーブルの表示名(例: "樹木マスタ")
    columns: [{"suffix": "RouteNumber", "display": "路線番号"}, ...] のリスト
             ("suffix"はadd_string等に渡したnameパラメータと同じ値にすること)
    """
    manifest = load_manifest()
    manifest[entity_suffix] = {"display": entity_display, "columns": columns}
    with open(MANIFEST_FILE, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    print(f"\nマニフェストに『{entity_display}』の情報を記録しました({MANIFEST_FILE})。")


def get_access_token(env_url: str) -> str:
    app = msal.PublicClientApplication(PUBLIC_CLIENT_ID, authority=AUTHORITY)
    scopes = [f"{env_url}/.default"]
    flow = app.initiate_device_flow(scopes=scopes)
    if "user_code" not in flow:
        raise RuntimeError(f"デバイスコードフローの開始に失敗しました: {flow}")
    print(flow["message"])
    result = app.acquire_token_by_device_flow(flow)
    if "access_token" not in result:
        raise RuntimeError(f"認証に失敗しました: {result.get('error_description')}")
    return result["access_token"]


def get_default_prefix(base: str, headers: dict) -> str:
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


def connect():
    """環境URLの入力を受け付け、サインインして (base, headers, prefix) を返す。"""
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
    return base, headers, prefix


def label(text: str) -> dict:
    return {
        "@odata.type": "Microsoft.Dynamics.CRM.Label",
        "LocalizedLabels": [
            {
                "@odata.type": "Microsoft.Dynamics.CRM.LocalizedLabel",
                "Label": text,
                "LanguageCode": 1041,
            }
        ],
    }


def entity_exists(base: str, headers: dict, logical_name: str) -> bool:
    url = f"{base}/EntityDefinitions(LogicalName='{logical_name}')"
    resp = requests.get(url, headers=headers)
    return resp.status_code == 200


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


def add_file(base, headers, logical_name, prefix, name, disp, max_size_kb=10240):
    body = {
        "@odata.type": "Microsoft.Dynamics.CRM.FileAttributeMetadata",
        "SchemaName": f"{prefix}_{name}",
        "DisplayName": label(disp),
        "MaxSizeInKB": max_size_kb,
    }
    _post_attribute(base, headers, logical_name, body, disp)


def add_lookup(base, headers, referencing_entity, referenced_entity, referenced_attribute,
               prefix, field_name, disp, relationship_name):
    """referencing_entity(子) から referenced_entity(親) へのN:1ルックアップを作成する。"""
    check_url = f"{base}/RelationshipDefinitions(SchemaName='{relationship_name}')"
    if requests.get(check_url, headers=headers).status_code == 200:
        print(f"関係『{relationship_name}』は既に存在します。スキップします。")
        return
    body = {
        "@odata.type": "Microsoft.Dynamics.CRM.OneToManyRelationshipMetadata",
        "SchemaName": relationship_name,
        "ReferencedEntity": referenced_entity,
        "ReferencingEntity": referencing_entity,
        "ReferencedAttribute": referenced_attribute,
        "Lookup": {
            "@odata.type": "Microsoft.Dynamics.CRM.LookupAttributeMetadata",
            "SchemaName": f"{prefix}_{field_name}",
            "DisplayName": label(disp),
        },
    }
    resp = requests.post(f"{base}/RelationshipDefinitions", headers=headers, json=body)
    if resp.status_code not in (200, 201, 204):
        print(f"関係『{disp}』の作成に失敗しました: {resp.status_code} {resp.text}")
    else:
        print(f"ルックアップ『{disp}』を作成しました。")


# =========================================================
# ここから：実データ(レコード)のCRUD用ヘルパー
# テーブル/列のメタデータ操作(上記)とは別の領域。
# =========================================================

_entity_set_name_cache = {}


def get_entity_set_name(base, headers, logical_name):
    """テーブルの論理名(例: new_tree)から、レコード操作に使うコレクション名(例: new_trees)を取得する。"""
    if logical_name in _entity_set_name_cache:
        return _entity_set_name_cache[logical_name]
    url = f"{base}/EntityDefinitions(LogicalName='{logical_name}')?$select=EntitySetName"
    resp = requests.get(url, headers=headers)
    resp.raise_for_status()
    name = resp.json()["EntitySetName"]
    _entity_set_name_cache[logical_name] = name
    return name


def create_record(base, headers, entity_set_name, data):
    """1件のレコードを作成し、作成されたレコードのGUIDを返す。"""
    url = f"{base}/{entity_set_name}"
    resp = requests.post(url, headers=headers, json=data)
    if resp.status_code not in (200, 201, 204):
        raise RuntimeError(f"レコード作成に失敗しました: {resp.status_code} {resp.text}")
    entity_id_header = resp.headers.get("OData-EntityId", "")
    record_id = entity_id_header.split("(")[-1].rstrip(")")
    return record_id


def lookup_bind(entity_set_name, record_id):
    """ルックアップ列に設定する '@odata.bind' の値を組み立てる。"""
    return f"/{entity_set_name}({record_id})"
