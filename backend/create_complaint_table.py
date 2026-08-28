"""
create_complaint_table.py
----------------------------
(仮称)樹木管理システム ポートフォリオ用
Dataverse Web API を使って「苦情・陳情記録」テーブルを自動作成するスクリプト。
設計書(Dataverseデータモデル設計書.xlsx)の8テーブル中、最後のテーブル。

事前準備:
    同じフォルダに dataverse_common.py が必要。
    樹木マスタ(new_tree)が先に作成済みであること
    (このテーブルの樹木IDは特定の樹木に紐づかない陳情もあるため任意項目とする)。

実行方法:
    py create_complaint_table.py
"""

import sys
import requests
from dataverse_common import (
    connect,
    label,
    entity_exists,
    add_date,
    add_string,
    add_choice,
    add_lookup,
    save_manifest_entry,
)


def create_complaint_entity(base: str, headers: dict, prefix: str) -> str:
    logical_name = f"{prefix}_complaint"
    if entity_exists(base, headers, logical_name):
        print("苦情・陳情記録は既に存在します。作成をスキップします。")
        return logical_name

    body = {
        "@odata.type": "Microsoft.Dynamics.CRM.EntityMetadata",
        "SchemaName": f"{prefix}_Complaint",
        "DisplayName": label("苦情・陳情記録"),
        "DisplayCollectionName": label("苦情・陳情記録"),
        "Description": label("(仮称)樹木管理システム ポートフォリオ 苦情・陳情記録テーブル"),
        "OwnershipType": "UserOwned",
        "IsActivity": False,
        "HasNotes": True,
        "HasActivities": False,
        "Attributes": [
            {
                "@odata.type": "Microsoft.Dynamics.CRM.StringAttributeMetadata",
                "SchemaName": f"{prefix}_ComplaintNumber",
                "DisplayName": label("苦情記録番号"),
                "RequiredLevel": {"Value": "None"},
                "MaxLength": 100,
                "FormatName": {"Value": "Text"},
                "IsPrimaryName": True,
                "AutoNumberFormat": "CMPL-{SEQNUM:5}",
            }
        ],
    }
    resp = requests.post(f"{base}/EntityDefinitions", headers=headers, json=body)
    if resp.status_code not in (200, 201, 204):
        raise RuntimeError(f"テーブル作成に失敗しました: {resp.status_code} {resp.text}")
    print("苦情・陳情記録テーブルを作成しました。")
    return logical_name


def build(base, headers, prefix):
    logical_name = create_complaint_entity(base, headers, prefix)

    add_string(base, headers, logical_name, prefix, "RouteNumber", "路線番号", max_len=50)
    add_date(base, headers, logical_name, prefix, "RequestDate", "依頼日")
    add_string(base, headers, logical_name, prefix, "RequestContent", "依頼内容", max_len=2000, memo=True)
    add_date(base, headers, logical_name, prefix, "ResponseDate", "対応日")
    add_string(base, headers, logical_name, prefix, "ResponseRecord", "対応記録", max_len=2000, memo=True)
    add_choice(
        base, headers, logical_name, prefix, "Status", "ステータス",
        ["未対応", "対応中", "対応済"],
    )

    # 樹木マスタへの任意のルックアップ(特定樹木に紐づかない陳情もあるため必須にしない)
    add_lookup(
        base, headers,
        referencing_entity=logical_name,
        referenced_entity=f"{prefix}_tree",
        referenced_attribute=f"{prefix}_treeid",
        prefix=prefix,
        field_name="TreeId",
        disp="樹木ID",
        relationship_name=f"{prefix}_tree_complaint",
    )

    save_manifest_entry("complaint", "苦情・陳情記録", [
        {"suffix": "ComplaintNumber", "display": "苦情記録番号"},
        {"suffix": "RouteNumber", "display": "路線番号"},
        {"suffix": "RequestDate", "display": "依頼日"},
        {"suffix": "RequestContent", "display": "依頼内容"},
        {"suffix": "ResponseDate", "display": "対応日"},
        {"suffix": "ResponseRecord", "display": "対応記録"},
        {"suffix": "Status", "display": "ステータス"},
        {"suffix": "TreeId", "display": "樹木ID"},
    ])

    print("\n完了しました。Power AppsのUIで『苦情・陳情記録』テーブルを開いて列を確認してください。")
    print("これで設計書の8テーブル中、7テーブル(樹木マスタ〜苦情・陳情記録)が完成しました。")


def main():
    base, headers, prefix = connect()
    build(base, headers, prefix)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # noqa: BLE001
        print(f"\nエラーが発生しました: {exc}", file=sys.stderr)
        sys.exit(1)
