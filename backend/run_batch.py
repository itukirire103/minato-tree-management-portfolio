"""
run_batch.py
-------------
(仮称)樹木管理システム ポートフォリオ用 バッチ実行スクリプト

毎回サインインし直す手間を減らすため、1回のサインインで
「テーブル作成 → 検証」までまとめて実行する。

実行方法:
    py run_batch.py

このファイルを直接編集して、実行したい create_xxx_table.py の
build(...) 呼び出しを増減させる(下のRUN_STEPSを編集する)。
"""

import sys
from dataverse_common import connect
from verify_schema import verify

# 実行したいテーブル作成処理をここに追加していく。
# 新しいテーブルスクリプトを作ったら、ここに1行 import と1行 呼び出しを足すだけでよい。
import create_vendor_table
import create_workhistory_table
import create_replant_table
import create_complaint_table


RUN_STEPS = [
    ("委託業者・協定管理者マスタ", create_vendor_table.build),
    ("作業履歴", create_workhistory_table.build),
    ("植替え履歴", create_replant_table.build),
    ("苦情・陳情記録", create_complaint_table.build),
]


def main():
    base, headers, prefix = connect()

    for name, build_func in RUN_STEPS:
        print(f"\n----- {name} を処理します -----")
        try:
            build_func(base, headers, prefix)
        except Exception as exc:  # noqa: BLE001
            print(f"『{name}』の処理中にエラーが発生しました: {exc}", file=sys.stderr)
            print("このステップはスキップして、次に進みます。\n")
            continue

    print("\n----- すべてのテーブル作成処理が終わったので検証します -----\n")
    verify(base, headers, prefix)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # noqa: BLE001
        print(f"\nエラーが発生しました: {exc}", file=sys.stderr)
        sys.exit(1)
