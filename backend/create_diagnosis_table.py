"""
create_diagnosis_table.py
--------------------------
(仮称)樹木管理システム ポートフォリオ用
Dataverse Web API を使って「樹木診断結果」テーブルを自動作成するスクリプト。

事前準備:
    同じフォルダに dataverse_common.py が必要(create_tree_table.py と同じ場所)。

実行方法:
    py create_diagnosis_table.py
"""

import sys
import requests
from dataverse_common import (
    connect,
    label,
    entity_exists,
    add_string,
    add_decimal,
    add_date,
    add_boolean,
    add_choice,
    add_file,
    add_lookup,
    save_manifest_entry,
)


def create_diagnosis_entity(base: str, headers: dict, prefix: str) -> str:
    logical_name = f"{prefix}_diagnosis"
    if entity_exists(base, headers, logical_name):
        print("樹木診断結果は既に存在します。作成をスキップします。")
        return logical_name

    body = {
        "@odata.type": "Microsoft.Dynamics.CRM.EntityMetadata",
        "SchemaName": f"{prefix}_Diagnosis",
        "DisplayName": label("樹木診断結果"),
        "DisplayCollectionName": label("樹木診断結果"),
        "Description": label("(仮称)樹木管理システム ポートフォリオ 樹木診断結果テーブル"),
        "OwnershipType": "UserOwned",
        "IsActivity": False,
        "HasNotes": True,  # 被害部写真など複数枚の添付はDataverse標準のノート機能で対応する
        "HasActivities": False,
        "Attributes": [
            {
                "@odata.type": "Microsoft.Dynamics.CRM.StringAttributeMetadata",
                "SchemaName": f"{prefix}_DiagnosisNumber",
                "DisplayName": label("診断記録番号"),
                "RequiredLevel": {"Value": "None"},
                "MaxLength": 100,
                "FormatName": {"Value": "Text"},
                "IsPrimaryName": True,
                # 自然キーがないため、自動採番(例: DIAG-00001)を主要な名前列にする
                "AutoNumberFormat": "DIAG-{SEQNUM:5}",
            }
        ],
    }
    resp = requests.post(f"{base}/EntityDefinitions", headers=headers, json=body)
    if resp.status_code not in (200, 201, 204):
        raise RuntimeError(f"テーブル作成に失敗しました: {resp.status_code} {resp.text}")
    print("樹木診断結果テーブルを作成しました。")
    return logical_name


def main():
    base, headers, prefix = connect()
    logical_name = create_diagnosis_entity(base, headers, prefix)

    add_date(base, headers, logical_name, prefix, "DiagnosisDate", "診断日")
    add_string(base, headers, logical_name, prefix, "Arborist", "樹木医名", max_len=100)

    add_choice(base, headers, logical_name, prefix, "Vigor", "樹勢(活力診断)", ["1", "2", "3", "4", "5"])
    add_choice(base, headers, logical_name, prefix, "Shape", "樹形(活力診断)", ["1", "2", "3", "4", "5"])

    add_string(base, headers, logical_name, prefix, "RootFindings", "根元_腐朽空洞等所見", max_len=2000, memo=True)
    add_string(base, headers, logical_name, prefix, "TrunkFindings", "幹_腐朽空洞等所見", max_len=2000, memo=True)
    add_string(base, headers, logical_name, prefix, "BranchFindings", "大枝_腐朽空洞等所見", max_len=2000, memo=True)

    add_choice(base, headers, logical_name, prefix, "VisualJudgement", "外観診断判定", ["A", "B1", "B2", "C"])
    add_choice(base, headers, logical_name, prefix, "OverallJudgement", "総合判定", ["A", "B1", "B2", "C"])
    add_string(base, headers, logical_name, prefix, "JudgementReason", "判定理由", max_len=2000, memo=True)

    add_choice(
        base, headers, logical_name, prefix, "NextDiagnosisTiming", "次回診断予定時期",
        ["1年後", "2年後", "3年後", "5年後"],
    )

    add_boolean(base, headers, logical_name, prefix, "NeedsDetailedDiagnosis", "精密診断要否")
    add_decimal(base, headers, logical_name, prefix, "DecayHollowRate", "精密診断_腐朽空洞率(%)", precision=1)

    add_file(base, headers, logical_name, prefix, "DiagnosisReportFile", "診断カルテ添付ファイル")

    # 樹木マスタへのルックアップ(1本の樹木に複数回の診断結果が紐づく)
    add_lookup(
        base, headers,
        referencing_entity=logical_name,
        referenced_entity=f"{prefix}_tree",
        referenced_attribute=f"{prefix}_treeid",
        prefix=prefix,
        field_name="TreeId",
        disp="樹木ID",
        relationship_name=f"{prefix}_tree_diagnosis",
    )

    save_manifest_entry("diagnosis", "樹木診断結果", [
        {"suffix": "DiagnosisNumber", "display": "診断記録番号"},
        {"suffix": "DiagnosisDate", "display": "診断日"},
        {"suffix": "Arborist", "display": "樹木医名"},
        {"suffix": "Vigor", "display": "樹勢(活力診断)"},
        {"suffix": "Shape", "display": "樹形(活力診断)"},
        {"suffix": "RootFindings", "display": "根元_腐朽空洞等所見"},
        {"suffix": "TrunkFindings", "display": "幹_腐朽空洞等所見"},
        {"suffix": "BranchFindings", "display": "大枝_腐朽空洞等所見"},
        {"suffix": "VisualJudgement", "display": "外観診断判定"},
        {"suffix": "OverallJudgement", "display": "総合判定"},
        {"suffix": "JudgementReason", "display": "判定理由"},
        {"suffix": "NextDiagnosisTiming", "display": "次回診断予定時期"},
        {"suffix": "NeedsDetailedDiagnosis", "display": "精密診断要否"},
        {"suffix": "DecayHollowRate", "display": "精密診断_腐朽空洞率(%)"},
        {"suffix": "DiagnosisReportFile", "display": "診断カルテ添付ファイル"},
        {"suffix": "TreeId", "display": "樹木ID"},
    ])

    print("\n完了しました。Power AppsのUIで『樹木診断結果』テーブルを開いて列を確認してください。")
    print("※被害部写真など複数枚の画像は、専用の列ではなく各レコードの「ノート(タイムライン)」")
    print("　から添付する運用にしています(HasNotes=Trueで有効化済み)。")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # noqa: BLE001
        print(f"\nエラーが発生しました: {exc}", file=sys.stderr)
        sys.exit(1)
