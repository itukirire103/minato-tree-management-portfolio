"""
create_workhistory_table.py
------------------------------
(仮称)樹木管理システム ポートフォリオ用
Dataverse Web API を使って「作業履歴」テーブルを自動作成するスクリプト。
樹木マスタ・委託業者マスタの2つへのルックアップを持つ。

事前準備:
    同じフォルダに dataverse_common.py が必要。
    樹木マスタ(new_tree)・委託業者マスタ(new_vendor)が先に作成済みであること。

実行方法:
    py create_workhistory_table.py
"""

import sys
import requests
from dataverse_common import (
    connect,
    label,
    entity_exists,
    add_date,
    add_choice,
    add_string,
    add_lookup,
    save_manifest_entry,
)


def create_workhistory_entity(base: str, headers: dict, prefix: str) -> str:
    logical_name = f"{prefix}_workhistory"
    if entity_exists(base, headers, logical_name):
        print("作業履歴は既に存在します。作成をスキップします。")
        return logical_name

    body = {
        "@odata.type": "Microsoft.Dynamics.CRM.EntityMetadata",
        "SchemaName": f"{prefix}_WorkHistory",
        "DisplayName": label("作業履歴"),
        "DisplayCollectionName": label("作業履歴"),
        "Description": label("(仮称)樹木管理システム ポートフォリオ 作業履歴テーブル"),
        "OwnershipType": "UserOwned",
        "IsActivity": False,
        "HasNotes": True,  # 作業前後の写真はノートで添付
        "HasActivities": False,
        "Attributes": [
            {
                "@odata.type": "Microsoft.Dynamics.CRM.StringAttributeMetadata",
                "SchemaName": f"{prefix}_WorkNumber",
                "DisplayName": label("作業記録番号"),
                "RequiredLevel": {"Value": "None"},
                "MaxLength": 100,
                "FormatName": {"Value": "Text"},
                "IsPrimaryName": True,
                "AutoNumberFormat": "WORK-{SEQNUM:5}",
            }
        ],
    }
    resp = requests.post(f"{base}/EntityDefinitions", headers=headers, json=body)
    if resp.status_code not in (200, 201, 204):
        raise RuntimeError(f"テーブル作成に失敗しました: {resp.status_code} {resp.text}")
    print("作業履歴テーブルを作成しました。")
    return logical_name


def build(base, headers, prefix):
    logical_name = create_workhistory_entity(base, headers, prefix)

    add_choice(
        base, headers, logical_name, prefix, "WorkType", "作業種別",
        ["剪定", "伐採", "伐根", "支柱設置撤去", "施肥", "土壌改良", "その他"],
    )
    add_date(base, headers, logical_name, prefix, "WorkDate", "作業日")
    add_choice(base, headers, logical_name, prefix, "PerformerType", "実施者区分", ["区", "委託業者"])
    add_string(base, headers, logical_name, prefix, "WorkNotes", "作業内容メモ", max_len=2000, memo=True)

    # 樹木マスタへのルックアップ(1本の樹木に複数の作業履歴が紐づく)
    add_lookup(
        base, headers,
        referencing_entity=logical_name,
        referenced_entity=f"{prefix}_tree",
        referenced_attribute=f"{prefix}_treeid",
        prefix=prefix,
        field_name="TreeId",
        disp="樹木ID",
        relationship_name=f"{prefix}_tree_workhistory",
    )

    # 委託業者マスタへのルックアップ(実施事業者)
    add_lookup(
        base, headers,
        referencing_entity=logical_name,
        referenced_entity=f"{prefix}_vendor",
        referenced_attribute=f"{prefix}_vendorid",
        prefix=prefix,
        field_name="VendorId",
        disp="実施事業者",
        relationship_name=f"{prefix}_vendor_workhistory",
    )

    save_manifest_entry("workhistory", "作業履歴", [
        {"suffix": "WorkNumber", "display": "作業記録番号"},
        {"suffix": "WorkType", "display": "作業種別"},
        {"suffix": "WorkDate", "display": "作業日"},
        {"suffix": "PerformerType", "display": "実施者区分"},
        {"suffix": "WorkNotes", "display": "作業内容メモ"},
        {"suffix": "TreeId", "display": "樹木ID"},
        {"suffix": "VendorId", "display": "実施事業者"},
    ])

    print("\n完了しました。Power AppsのUIで『作業履歴』テーブルを開いて列を確認してください。")


def main():
    base, headers, prefix = connect()
    build(base, headers, prefix)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # noqa: BLE001
        print(f"\nエラーが発生しました: {exc}", file=sys.stderr)
        sys.exit(1)
