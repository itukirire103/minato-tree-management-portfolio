"""
create_inspection_table.py
----------------------------
(仮称)樹木管理システム ポートフォリオ用
Dataverse Web API を使って「点検記録」テーブルを自動作成するスクリプト。

事前準備:
    同じフォルダに dataverse_common.py が必要。

実行方法:
    py create_inspection_table.py
"""

import sys
import requests
from dataverse_common import (
    connect,
    label,
    entity_exists,
    add_string,
    add_date,
    add_boolean,
    add_choice,
    add_lookup,
    save_manifest_entry,
)


def create_inspection_entity(base: str, headers: dict, prefix: str) -> str:
    logical_name = f"{prefix}_inspection"
    if entity_exists(base, headers, logical_name):
        print("点検記録は既に存在します。作成をスキップします。")
        return logical_name

    body = {
        "@odata.type": "Microsoft.Dynamics.CRM.EntityMetadata",
        "SchemaName": f"{prefix}_Inspection",
        "DisplayName": label("点検記録"),
        "DisplayCollectionName": label("点検記録"),
        "Description": label("(仮称)樹木管理システム ポートフォリオ 点検記録テーブル"),
        "OwnershipType": "UserOwned",
        "IsActivity": False,
        "HasNotes": True,  # 点検写真(番号プレート/全景/樹冠部/主要部/根元部)はノートで添付
        "HasActivities": False,
        "Attributes": [
            {
                "@odata.type": "Microsoft.Dynamics.CRM.StringAttributeMetadata",
                "SchemaName": f"{prefix}_InspectionNumber",
                "DisplayName": label("点検記録番号"),
                "RequiredLevel": {"Value": "None"},
                "MaxLength": 100,
                "FormatName": {"Value": "Text"},
                "IsPrimaryName": True,
                "AutoNumberFormat": "INSP-{SEQNUM:5}",
            }
        ],
    }
    resp = requests.post(f"{base}/EntityDefinitions", headers=headers, json=body)
    if resp.status_code not in (200, 201, 204):
        raise RuntimeError(f"テーブル作成に失敗しました: {resp.status_code} {resp.text}")
    print("点検記録テーブルを作成しました。")
    return logical_name


def main():
    base, headers, prefix = connect()
    logical_name = create_inspection_entity(base, headers, prefix)

    add_date(base, headers, logical_name, prefix, "InspectionDate", "点検日")
    add_string(base, headers, logical_name, prefix, "Inspector", "点検者", max_len=100)

    # 維持管理上の問題(樹木点検表①)
    add_boolean(base, headers, logical_name, prefix, "OverRoadLimit", "建築限界越え_車道側")
    add_boolean(base, headers, logical_name, prefix, "OverSidewalkLimit", "建築限界越え_歩道側")
    add_boolean(base, headers, logical_name, prefix, "ConflictWithFacility", "道路施設との競合")
    add_boolean(base, headers, logical_name, prefix, "StakeNeedsFix", "支柱直し撤去")
    add_boolean(base, headers, logical_name, prefix, "BigBranchDamage", "太枝枯れ折れ")
    add_boolean(base, headers, logical_name, prefix, "RootLiftPavementCrack", "根上がり舗装クラック")

    # 活力点検(樹木点検表②)
    add_boolean(base, headers, logical_name, prefix, "LeafAbnormal", "葉の状態異常")
    add_boolean(base, headers, logical_name, prefix, "TipDieback", "先端枝の枯れ")
    add_boolean(base, headers, logical_name, prefix, "SevereDecline", "枯死著しい衰弱")

    # 樹木の異常(樹木点検表③)
    add_boolean(base, headers, logical_name, prefix, "Mushroom", "キノコの有無")
    add_boolean(base, headers, logical_name, prefix, "BarkDecay", "樹皮枯死欠損腐朽")
    add_boolean(base, headers, logical_name, prefix, "PestDamage", "病虫害")
    add_boolean(base, headers, logical_name, prefix, "Swaying", "揺れ")
    add_boolean(base, headers, logical_name, prefix, "UnnaturalLean", "不自然な傾斜")

    add_choice(
        base, headers, logical_name, prefix, "InspectionResult", "点検結果",
        ["概ね良好", "維持管理処置必要", "外観診断必要"],
    )
    add_string(base, headers, logical_name, prefix, "OtherNotes", "その他特記事項", max_len=2000, memo=True)

    # 樹木マスタへのルックアップ(1本の樹木に複数回の点検記録が紐づく)
    add_lookup(
        base, headers,
        referencing_entity=logical_name,
        referenced_entity=f"{prefix}_tree",
        referenced_attribute=f"{prefix}_treeid",
        prefix=prefix,
        field_name="TreeId",
        disp="樹木ID",
        relationship_name=f"{prefix}_tree_inspection",
    )

    save_manifest_entry("inspection", "点検記録", [
        {"suffix": "InspectionNumber", "display": "点検記録番号"},
        {"suffix": "InspectionDate", "display": "点検日"},
        {"suffix": "Inspector", "display": "点検者"},
        {"suffix": "OverRoadLimit", "display": "建築限界越え_車道側"},
        {"suffix": "OverSidewalkLimit", "display": "建築限界越え_歩道側"},
        {"suffix": "ConflictWithFacility", "display": "道路施設との競合"},
        {"suffix": "StakeNeedsFix", "display": "支柱直し撤去"},
        {"suffix": "BigBranchDamage", "display": "太枝枯れ折れ"},
        {"suffix": "RootLiftPavementCrack", "display": "根上がり舗装クラック"},
        {"suffix": "LeafAbnormal", "display": "葉の状態異常"},
        {"suffix": "TipDieback", "display": "先端枝の枯れ"},
        {"suffix": "SevereDecline", "display": "枯死著しい衰弱"},
        {"suffix": "Mushroom", "display": "キノコの有無"},
        {"suffix": "BarkDecay", "display": "樹皮枯死欠損腐朽"},
        {"suffix": "PestDamage", "display": "病虫害"},
        {"suffix": "Swaying", "display": "揺れ"},
        {"suffix": "UnnaturalLean", "display": "不自然な傾斜"},
        {"suffix": "InspectionResult", "display": "点検結果"},
        {"suffix": "OtherNotes", "display": "その他特記事項"},
        {"suffix": "TreeId", "display": "樹木ID"},
    ])

    print("\n完了しました。Power AppsのUIで『点検記録』テーブルを開いて列を確認してください。")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # noqa: BLE001
        print(f"\nエラーが発生しました: {exc}", file=sys.stderr)
        sys.exit(1)
