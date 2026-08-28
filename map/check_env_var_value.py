"""
check_env_var_value.py
------------------------
(仮称)樹木管理システム ポートフォリオ用
Dataverse環境変数『new_AzureMapsSubscriptionKey』の実際の値(マスク済み)と、
それが実際にAzure Maps APIで有効かどうかを検証する追加診断スクリプト。

実行方法:
    py check_env_var_value.py <env_url> [実際の正しいキー(比較用、省略可)]
"""

import sys
import requests
from dataverse_common import get_access_token, get_default_prefix

API_VERSION = "v9.2"
DEFAULT_ENV_URL = "https://orgfeb03658.crm7.dynamics.com"


def main():
    env_url = (sys.argv[1] if len(sys.argv) > 1 else DEFAULT_ENV_URL).rstrip("/")
    compare_key = sys.argv[2] if len(sys.argv) > 2 else None

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
    schema_name = f"{prefix}_AzureMapsSubscriptionKey"

    query = (
        f"{base}/environmentvariablevalues"
        f"?$select=value&$expand=EnvironmentVariableDefinitionId($select=schemaname)"
    )
    resp = requests.get(query, headers=headers)
    resp.raise_for_status()
    all_values = resp.json().get("value", [])

    match = None
    for v in all_values:
        defn = v.get("EnvironmentVariableDefinitionId") or {}
        if defn.get("schemaname") == schema_name:
            match = v
            break

    print("=" * 60)
    print(f"環境変数定義スキーマ名: {schema_name}")
    print("=" * 60)

    if not match:
        print("[!] 値(environmentvariablevalue)レコードが存在しません。")
        print("    → create_env_variable.py が未実行、または値未設定です。")
        return

    stored_value = match.get("value") or ""
    length = len(stored_value)
    masked = (stored_value[:5] + "..." ) if length >= 5 else "(短すぎる/空)"
    print(f"保存されている値の長さ: {length} 文字")
    print(f"先頭5文字: {masked}")

    if compare_key:
        if stored_value == compare_key:
            print("→ 実際の有効なキーと完全一致しました。")
        else:
            print("→ [不一致] 実際の有効なキーとは異なります。値が古い/誤っている可能性が高いです。")

    print("\n" + "=" * 60)
    print("Azure Maps APIに対して、保存されている値を直接テスト")
    print("=" * 60)
    if not stored_value.strip():
        print("値が空のため、テストをスキップします。")
        return

    test_url = (
        "https://atlas.microsoft.com/map/tile"
        f"?api-version=2.0&tilesetId=microsoft.base.road&zoom=1&x=0&y=0"
        f"&subscription-key={stored_value.strip()}"
    )
    test_resp = requests.get(test_url)
    print(f"HTTPステータス: {test_resp.status_code}")
    if test_resp.status_code == 200:
        print("→ 保存されている値は有効です。")
    else:
        print("→ 保存されている値は無効です。実際のキーで再登録が必要です。")
        print(f"   レスポンス本文(先頭200文字): {test_resp.text[:200]}")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # noqa: BLE001
        print(f"\nエラーが発生しました: {exc}", file=sys.stderr)
        sys.exit(1)
