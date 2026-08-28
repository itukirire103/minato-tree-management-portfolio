"""
check_view_fetchxml.py
-------------------------
「樹木マップ」ビューのfetchxml(絞り込み条件)を確認する追加診断スクリプト。
新規作成したレコードが地図に反映されない原因を切り分けるために作成した。

実行方法:
    py check_view_fetchxml.py <env_url>
"""
import sys
import requests
from dataverse_common import get_access_token, get_default_prefix, get_entity_set_name

API_VERSION = "v9.2"
DEFAULT_ENV_URL = "https://orgfeb03658.crm7.dynamics.com"


def main():
    env_url = (sys.argv[1] if len(sys.argv) > 1 else DEFAULT_ENV_URL).rstrip("/")
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
        f"&$select=name,fetchxml,savedqueryid"
    )
    resp = requests.get(url, headers=headers)
    resp.raise_for_status()
    views = resp.json().get("value", [])

    for v in views:
        if v["name"] == "樹木マップ":
            print(f"ビュー: {v['name']}")
            print(f"savedqueryid: {v['savedqueryid']}")
            print("\n--- fetchxml ---\n")
            print(v.get("fetchxml"))
            break
    else:
        print("『樹木マップ』ビューが見つかりませんでした。")

    print("\n" + "=" * 60)
    print(f"直近作成された{logical_name}レコードを新しい順に5件表示")
    print("=" * 60)
    entity_set_name = get_entity_set_name(base, headers, logical_name)
    rec_url = (
        f"{base}/{entity_set_name}"
        f"?$select={prefix}_treenumber,{prefix}_status,{prefix}_latitude,{prefix}_longitude,createdon,statecode"
        f"&$orderby=createdon desc&$top=5"
    )
    resp2 = requests.get(rec_url, headers=headers)
    resp2.raise_for_status()
    for rec in resp2.json().get("value", []):
        print(rec)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # noqa: BLE001
        print(f"\nエラーが発生しました: {exc}", file=sys.stderr)
        sys.exit(1)
