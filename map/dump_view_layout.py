"""
dump_view_layout.py
---------------------
(仮称)樹木管理システム ポートフォリオ用
「樹木マップ」ビューのlayoutxml(生データ)と公開状態を確認する追加診断スクリプト。
diagnose_map_binding.py で「バインドあり」までは分かったが、設定内容が正しいか、
公開済みかまでは分からなかったための深掘り用。

実行方法:
    py dump_view_layout.py <env_url>
"""

import sys
import requests
from dataverse_common import get_access_token, get_default_prefix

API_VERSION = "v9.2"
DEFAULT_ENV_URL = "https://orgfeb03658.crm7.dynamics.com"


def main():
    env_url = (sys.argv[1] if len(sys.argv) > 1 else DEFAULT_ENV_URL).rstrip("/")
    print(f"対象環境: {env_url}\n")
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
    logical_name = f"{prefix}_tree"

    url = (
        f"{base}/savedqueries?$filter=returnedtypecode eq '{logical_name}'"
        f"&$select=name,layoutxml,statecode,querytype,isdefault,savedqueryid"
    )
    resp = requests.get(url, headers=headers)
    resp.raise_for_status()
    views = resp.json().get("value", [])

    target = None
    for v in views:
        if "treemapcontrol" in (v.get("layoutxml") or "").lower():
            target = v
            break

    if not target:
        print("対象ビューが見つかりませんでした。")
        return

    print("=" * 60)
    print(f"ビュー名: {target['name']}")
    print(f"savedqueryid: {target['savedqueryid']}")
    print(f"querytype: {target.get('querytype')}")
    print(f"statecode: {target.get('statecode')} (0=有効, 1=無効)")
    print(f"isdefault: {target.get('isdefault')}")
    print("=" * 60)
    print("\n--- layoutxml 全文 ---\n")
    print(target.get("layoutxml"))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # noqa: BLE001
        print(f"\nエラーが発生しました: {exc}", file=sys.stderr)
        sys.exit(1)
