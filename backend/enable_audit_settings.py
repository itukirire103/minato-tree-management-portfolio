"""
enable_audit_settings.py
---------------------------
(仮称)樹木管理システム ポートフォリオ用
組織全体の監査(Audit)ログを有効化する。冪等(既に有効なら何もしない)。

非機能要件#32(アクセスログの保管・監視)に対応するための設定作業。

注意: テーブル単位の監査(IsAuditEnabled)はDataverse Web API(v9.2)経由での
更新が "Operation not supported on EntityMetadata" で失敗したため、
Power Appsの管理画面(該当テーブル > 設定 > 監査)から手動で有効化している。

実行方法:
    py enable_audit_settings.py <env_url>
"""
import sys
import requests
from dataverse_common import get_access_token, get_default_prefix

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
    get_default_prefix(base, headers)  # 接続確認を兼ねる

    # 組織全体の監査を有効化
    org_url = f"{base}/organizations?$select=organizationid,isauditenabled"
    resp = requests.get(org_url, headers=headers)
    resp.raise_for_status()
    org = resp.json()["value"][0]
    if org.get("isauditenabled"):
        print("組織全体の監査は既に有効です。スキップします。")
    else:
        org_id = org["organizationid"]
        patch_url = f"{base}/organizations({org_id})"
        resp = requests.patch(patch_url, headers=headers, json={"isauditenabled": True})
        if resp.status_code not in (200, 204):
            raise RuntimeError(f"組織監査の有効化に失敗しました: {resp.status_code} {resp.text}")
        print("組織全体の監査を有効化しました。")

    print(
        "\nテーブル単位の監査(樹木マスタ等)は、Power Appsの管理画面"
        "(該当テーブル > 設定 > 監査)から手動で有効化してください。"
    )


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # noqa: BLE001
        print(f"\nエラーが発生しました: {exc}", file=sys.stderr)
        sys.exit(1)
