"""
check_audit_settings.py
--------------------------
組織全体とtreeテーブルの監査(Audit)設定が有効になっているかを確認する
一時診断スクリプト。

実行方法:
    py check_audit_settings.py <env_url>
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
    prefix = get_default_prefix(base, headers)

    org_url = f"{base}/organizations?$select=isauditenabled,auditretentionperiodv2"
    resp = requests.get(org_url, headers=headers)
    resp.raise_for_status()
    org = resp.json()["value"][0]
    print(f"組織全体の監査(isauditenabled): {org.get('isauditenabled')}")
    print(f"監査ログ保持期間: {org.get('auditretentionperiodv2')}")

    logical_name = f"{prefix}_tree"
    ent_url = f"{base}/EntityDefinitions(LogicalName='{logical_name}')?$select=IsAuditEnabled"
    resp2 = requests.get(ent_url, headers=headers)
    resp2.raise_for_status()
    ent = resp2.json()
    print(f"\n{logical_name}テーブルの監査(IsAuditEnabled): {ent.get('IsAuditEnabled')}")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # noqa: BLE001
        print(f"\nエラーが発生しました: {exc}", file=sys.stderr)
        sys.exit(1)
