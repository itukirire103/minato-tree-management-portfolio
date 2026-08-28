"""
create_replant_table.py
--------------------------
(仮称)樹木管理システム ポートフォリオ用
Dataverse Web API を使って「植替え履歴」テーブルを自動作成するスクリプト。
樹木マスタへ「旧樹木」「新樹木」の2本のルックアップを持つ点がポイント
(同じ参照先テーブルに対して、意味の異なる2つの関係を作る)。

事前準備:
    同じフォルダに dataverse_common.py が必要。
    樹木マスタ(new_tree)が先に作成済みであること。

実行方法:
    py create_replant_table.py
"""

import sys
import requests
from dataverse_common import (
    connect,
    label,
    entity_exists,
    add_date,
    add_string,
    add_lookup,
    save_manifest_entry,
)


def create_replant_entity(base: str, headers: dict, prefix: str) -> str:
    logical_name = f"{prefix}_replant"
    if entity_exists(base, headers, logical_name):
        print("植替え履歴は既に存在します。作成をスキップします。")
        return logical_name

    body = {
        "@odata.type": "Microsoft.Dynamics.CRM.EntityMetadata",
        "SchemaName": f"{prefix}_Replant",
        "DisplayName": label("植替え履歴"),
        "DisplayCollectionName": label("植替え履歴"),
        "Description": label("(仮称)樹木管理システム ポートフォリオ 植替え履歴テーブル"),
        "OwnershipType": "UserOwned",
        "IsActivity": False,
        "HasNotes": True,
        "HasActivities": False,
        "Attributes": [
            {
                "@odata.type": "Microsoft.Dynamics.CRM.StringAttributeMetadata",
                "SchemaName": f"{prefix}_ReplantNumber",
                "DisplayName": label("植替え記録番号"),
                "RequiredLevel": {"Value": "None"},
                "MaxLength": 100,
                "FormatName": {"Value": "Text"},
                "IsPrimaryName": True,
                "AutoNumberFormat": "REPL-{SEQNUM:5}",
            }
        ],
    }
    resp = requests.post(f"{base}/EntityDefinitions", headers=headers, json=body)
    if resp.status_code not in (200, 201, 204):
        raise RuntimeError(f"テーブル作成に失敗しました: {resp.status_code} {resp.text}")
    print("植替え履歴テーブルを作成しました。")
    return logical_name


def build(base, headers, prefix):
    logical_name = create_replant_entity(base, headers, prefix)

    add_date(base, headers, logical_name, prefix, "ReplantDate", "植替え日")
    add_string(base, headers, logical_name, prefix, "Background", "経緯・備考", max_len=2000, memo=True)

    # 旧樹木への参照
    add_lookup(
        base, headers,
        referencing_entity=logical_name,
        referenced_entity=f"{prefix}_tree",
        referenced_attribute=f"{prefix}_treeid",
        prefix=prefix,
        field_name="OldTreeId",
        disp="旧樹木ID",
        relationship_name=f"{prefix}_tree_replant_old",
    )

    # 新樹木への参照(同じ樹木マスタに対する、意味の異なる2本目のルックアップ)
    add_lookup(
        base, headers,
        referencing_entity=logical_name,
        referenced_entity=f"{prefix}_tree",
        referenced_attribute=f"{prefix}_treeid",
        prefix=prefix,
        field_name="NewTreeId",
        disp="新樹木ID",
        relationship_name=f"{prefix}_tree_replant_new",
    )

    save_manifest_entry("replant", "植替え履歴", [
        {"suffix": "ReplantNumber", "display": "植替え記録番号"},
        {"suffix": "ReplantDate", "display": "植替え日"},
        {"suffix": "Background", "display": "経緯・備考"},
        {"suffix": "OldTreeId", "display": "旧樹木ID"},
        {"suffix": "NewTreeId", "display": "新樹木ID"},
    ])

    print("\n完了しました。Power AppsのUIで『植替え履歴』テーブルを開いて列を確認してください。")


def main():
    base, headers, prefix = connect()
    build(base, headers, prefix)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # noqa: BLE001
        print(f"\nエラーが発生しました: {exc}", file=sys.stderr)
        sys.exit(1)
