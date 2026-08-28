"""
create_vendor_table.py
------------------------
(仮称)樹木管理システム ポートフォリオ用
Dataverse Web API を使って「委託業者・協定管理者マスタ」テーブルを自動作成するスクリプト。

事前準備:
    同じフォルダに dataverse_common.py が必要。

実行方法:
    py create_vendor_table.py
"""

import sys
import requests
from dataverse_common import (
    connect,
    label,
    entity_exists,
    add_string,
    add_choice,
    save_manifest_entry,
)


def create_vendor_entity(base: str, headers: dict, prefix: str) -> str:
    logical_name = f"{prefix}_vendor"
    if entity_exists(base, headers, logical_name):
        print("委託業者・協定管理者マスタは既に存在します。作成をスキップします。")
        return logical_name

    body = {
        "@odata.type": "Microsoft.Dynamics.CRM.EntityMetadata",
        "SchemaName": f"{prefix}_Vendor",
        "DisplayName": label("委託業者・協定管理者マスタ"),
        "DisplayCollectionName": label("委託業者・協定管理者マスタ"),
        "Description": label("(仮称)樹木管理システム ポートフォリオ 委託業者・協定管理者マスタテーブル"),
        "OwnershipType": "UserOwned",
        "IsActivity": False,
        "HasNotes": True,
        "HasActivities": False,
        "Attributes": [
            {
                "@odata.type": "Microsoft.Dynamics.CRM.StringAttributeMetadata",
                "SchemaName": f"{prefix}_VendorName",
                "DisplayName": label("事業者名"),
                "RequiredLevel": {"Value": "ApplicationRequired"},
                "MaxLength": 200,
                "FormatName": {"Value": "Text"},
                "IsPrimaryName": True,
            }
        ],
    }
    resp = requests.post(f"{base}/EntityDefinitions", headers=headers, json=body)
    if resp.status_code not in (200, 201, 204):
        raise RuntimeError(f"テーブル作成に失敗しました: {resp.status_code} {resp.text}")
    print("委託業者・協定管理者マスタテーブルを作成しました。")
    return logical_name


def build(base, headers, prefix):
    logical_name = create_vendor_entity(base, headers, prefix)

    add_choice(
        base, headers, logical_name, prefix, "VendorType", "区分",
        ["街路樹管理委託事業者", "協定管理者", "その他"],
    )
    add_string(base, headers, logical_name, prefix, "AreaInCharge", "担当路線・エリア", max_len=2000, memo=True)
    add_string(base, headers, logical_name, prefix, "ContactInfo", "連絡先", max_len=200)

    save_manifest_entry("vendor", "委託業者・協定管理者マスタ", [
        {"suffix": "VendorName", "display": "事業者名"},
        {"suffix": "VendorType", "display": "区分"},
        {"suffix": "AreaInCharge", "display": "担当路線・エリア"},
        {"suffix": "ContactInfo", "display": "連絡先"},
    ])

    print("\n完了しました。Power AppsのUIで『委託業者・協定管理者マスタ』テーブルを開いて列を確認してください。")


def main():
    base, headers, prefix = connect()
    build(base, headers, prefix)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # noqa: BLE001
        print(f"\nエラーが発生しました: {exc}", file=sys.stderr)
        sys.exit(1)
