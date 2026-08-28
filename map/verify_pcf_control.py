"""
verify_pcf_control.py
------------------------
(仮称)樹木管理システム ポートフォリオ用
pcf_manifest.json に記録されたPCFコンポーネントが、実際にDataverse環境の
customcontrols(カスタムコントロール定義)として登録されているかを検証する。

これまでの verify_schema.py / verify_security_roles.py と同じパターン:
「作る側が自己申告したもの」を期待値として、実環境と突合する。

事前準備:
    同じフォルダに dataverse_common.py と pcf_manifest.json が必要。

実行方法:
    py verify_pcf_control.py
"""

import json
import os
import sys
import requests
from dataverse_common import connect

HERE = os.path.dirname(os.path.abspath(__file__))
MANIFEST_FILE = os.path.join(HERE, "pcf_manifest.json")


def load_pcf_manifest():
    if not os.path.exists(MANIFEST_FILE):
        print(f"{MANIFEST_FILE} が見つかりません。")
        sys.exit(1)
    with open(MANIFEST_FILE, "r", encoding="utf-8-sig") as f:
        return json.load(f)


def check_control(base, headers, control_name):
    # まず完全一致で確認
    url = f"{base}/customcontrols?$filter=name eq '{control_name}'&$select=name,customcontrolid"
    resp = requests.get(url, headers=headers)
    if resp.status_code != 200:
        print(f"  [警告] 照会に失敗しました: {resp.status_code} {resp.text}")
        return False
    value = resp.json().get("value", [])
    if value:
        return True

    # 完全一致で見つからない場合、部分一致で実際の登録名を調べる(デバッグ用)
    short_name = control_name.split(".")[-1]  # 例: "TreeMapControl"
    url2 = f"{base}/customcontrols?$filter=contains(name,'{short_name}')&$select=name,customcontrolid"
    resp2 = requests.get(url2, headers=headers)
    if resp2.status_code == 200:
        candidates = resp2.json().get("value", [])
        if candidates:
            print(f"  [情報] 完全一致は見つかりませんでしたが、類似する登録名が見つかりました:")
            for c in candidates:
                print(f"         実際の登録名: 「{c['name']}」")
        else:
            print(f"  [情報] 『{short_name}』を含む登録名も見つかりませんでした。")
    return False


def main():
    manifest = load_pcf_manifest()
    base, headers, prefix = connect()

    print("=" * 60)
    print("PCFコンポーネント検証結果")
    print("=" * 60)

    ok_count = 0
    for control_name, info in manifest.items():
        found = check_control(base, headers, control_name)
        status = "OK" if found else "見つかりません"
        print(f"\n■ {info['display']}({control_name}) : {status}")
        if found:
            ok_count += 1
            print(f"  データセット: {info['dataset']}")
            print(f"  必須列: {', '.join(info['bound_columns'])}")
        else:
            print("  → pac pcf push が正常に完了しているか確認してください。")

    print("\n" + "=" * 60)
    print(f"総合結果: {ok_count}/{len(manifest)} 件OK")
    print("=" * 60)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # noqa: BLE001
        print(f"\nエラーが発生しました: {exc}", file=sys.stderr)
        sys.exit(1)
