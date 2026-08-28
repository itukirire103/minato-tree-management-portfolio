"""
verify_schema.py
------------------
(仮称)樹木管理システム ポートフォリオ用 検証ハーネス

各 create_xxx_table.py が実行時に自己申告した schema_manifest.json をもとに、
実際のDataverse環境に「申告通りのテーブル・列が存在するか」を問い合わせて
差分レポートを表示する。

実行方法:
    py verify_schema.py

前提:
    - 同じフォルダに dataverse_common.py と schema_manifest.json が必要
    - schema_manifest.json は各 create_xxx_table.py を一度実行すると自動生成・更新される
"""

import sys
import requests
from dataverse_common import connect, load_manifest


def check_entity(base, headers, logical_name):
    url = f"{base}/EntityDefinitions(LogicalName='{logical_name}')"
    return requests.get(url, headers=headers).status_code == 200


def check_attribute(base, headers, logical_name, attr_logical_name):
    url = (
        f"{base}/EntityDefinitions(LogicalName='{logical_name}')"
        f"/Attributes(LogicalName='{attr_logical_name}')"
    )
    return requests.get(url, headers=headers).status_code == 200


def verify(base, headers, prefix):
    manifest = load_manifest()
    if not manifest:
        print("schema_manifest.json が見つからないか空です。")
        print("先に create_xxx_table.py を一度実行してマニフェストを作成してください。")
        return

    print("=" * 60)
    print("検証結果")
    print("=" * 60)

    total_tables = 0
    ok_tables = 0
    total_columns = 0
    ok_columns = 0

    for entity_suffix, info in manifest.items():
        total_tables += 1
        logical_name = f"{prefix}_{entity_suffix}"
        entity_display = info["display"]
        columns = info["columns"]

        entity_ok = check_entity(base, headers, logical_name)
        status = "OK" if entity_ok else "見つかりません"
        print(f"\n■ {entity_display}({logical_name}) : {status}")

        if not entity_ok:
            print("  → このテーブルはDataverse上に存在しません。create_xxx_table.pyを実行しましたか？")
            continue

        ok_tables += 1
        missing = []
        for col in columns:
            total_columns += 1
            attr_logical = f"{prefix}_{col['suffix']}".lower()
            if check_attribute(base, headers, logical_name, attr_logical):
                ok_columns += 1
            else:
                missing.append(col["display"])

        col_total = len(columns)
        col_ok = col_total - len(missing)
        print(f"  列: {col_ok}/{col_total} 件確認できました。")
        if missing:
            print(f"  不足している列: {', '.join(missing)}")

    print("\n" + "=" * 60)
    print(f"総合結果: テーブル {ok_tables}/{total_tables} 件OK, 列 {ok_columns}/{total_columns} 件OK")
    print("=" * 60)

    if ok_tables == total_tables and ok_columns == total_columns:
        print("\nすべて設計通りに作成されています。")
    else:
        print("\n一部に差分があります。上記の『不足している列』または『見つかりません』の箇所を確認してください。")


def main():
    base, headers, prefix = connect()
    verify(base, headers, prefix)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # noqa: BLE001
        print(f"\nエラーが発生しました: {exc}", file=sys.stderr)
        sys.exit(1)
