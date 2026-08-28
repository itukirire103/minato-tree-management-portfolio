"""
verify_aad_setup.py
----------------------
(仮称)樹木管理システム ポートフォリオ用
setup_azure_maps_aad.ps1 が作成したはずの
「Azure ADアプリ登録」「RBACロール割り当て」を、Microsoft Graph API /
Azure Resource Manager API 経由で検証するスクリプト。

事前準備:
    同じフォルダに setup_azure_maps_aad.ps1 の実行結果(aad_setup_result.json)が必要。
    pip install msal requests

実行方法:
    py verify_aad_setup.py
"""

import json
import os
import sys
import requests
import msal

PUBLIC_CLIENT_ID = "51f81489-12ee-4a9e-aaae-a2591f45987d"  # dataverse_common.pyと同じ公開クライアントID
HERE = os.path.dirname(os.path.abspath(__file__))
RESULT_FILE = os.path.join(HERE, "aad_setup_result.json")


def load_setup_result():
    if not os.path.exists(RESULT_FILE):
        print(f"{RESULT_FILE} が見つかりません。先に setup_azure_maps_aad.ps1 を実行してください。")
        sys.exit(1)
    with open(RESULT_FILE, "r", encoding="utf-8-sig") as f:
        return json.load(f)


def get_token(tenant_id, scope):
    app = msal.PublicClientApplication(
        PUBLIC_CLIENT_ID,
        authority=f"https://login.microsoftonline.com/{tenant_id}",
    )
    flow = app.initiate_device_flow(scopes=[scope])
    if "user_code" not in flow:
        raise RuntimeError(f"デバイスコードフローの開始に失敗しました: {flow}")
    print(flow["message"])
    result = app.acquire_token_by_device_flow(flow)
    if "access_token" not in result:
        raise RuntimeError(f"認証に失敗しました: {result.get('error_description')}")
    return result["access_token"]


def verify_app_registration(graph_token, app_object_id, expected_redirect_uri):
    url = f"https://graph.microsoft.com/v1.0/applications/{app_object_id}"
    resp = requests.get(url, headers={"Authorization": f"Bearer {graph_token}"})
    if resp.status_code != 200:
        print(f"[NG] アプリ登録が見つかりません: {resp.status_code} {resp.text}")
        return False
    data = resp.json()
    print(f"[OK] アプリ登録が見つかりました: {data.get('displayName')}")

    spa_uris = data.get("spa", {}).get("redirectUris", [])
    if expected_redirect_uri in spa_uris:
        print(f"[OK] リダイレクトURIが正しく設定されています: {expected_redirect_uri}")
        return True
    else:
        print(f"[NG] リダイレクトURIが見つかりません。")
        print(f"     期待値: {expected_redirect_uri}")
        print(f"     実際の設定: {spa_uris}")
        return False


def verify_role_assignment(arm_token, sp_object_id, maps_account_id):
    # Azure Mapsアカウントスコープでのロール割り当て一覧を取得
    url = (
        f"https://management.azure.com{maps_account_id}"
        f"/providers/Microsoft.Authorization/roleAssignments"
        f"?api-version=2022-04-01&$filter=principalId eq '{sp_object_id}'"
    )
    resp = requests.get(url, headers={"Authorization": f"Bearer {arm_token}"})
    if resp.status_code != 200:
        print(f"[NG] ロール割り当ての取得に失敗しました: {resp.status_code} {resp.text}")
        return False

    assignments = resp.json().get("value", [])
    if not assignments:
        print("[NG] このサービスプリンシパルへのロール割り当てが見つかりません。")
        return False

    print(f"[OK] ロール割り当てが {len(assignments)} 件見つかりました。")
    for a in assignments:
        role_id = a.get("properties", {}).get("roleDefinitionId", "")
        print(f"     roleDefinitionId: {role_id}")
    print("     ※『Azure Maps Data Reader』かどうかは、上記IDが一致するか目視確認してください。")
    return True


def main():
    setup = load_setup_result()
    tenant_id = setup["tenantId"]

    print("\n----- Microsoft Graphでアプリ登録を検証します -----")
    graph_token = get_token(tenant_id, "https://graph.microsoft.com/.default")
    app_ok = verify_app_registration(graph_token, setup["appObjectId"], setup["redirectUri"])

    print("\n----- Azure Resource Managerでロール割り当てを検証します -----")
    arm_token = get_token(tenant_id, "https://management.azure.com/.default")
    role_ok = verify_role_assignment(arm_token, setup["spObjectId"], setup["mapsAccountId"])

    print("\n" + "=" * 60)
    if app_ok and role_ok:
        print("すべて設計通りに設定されています。")
    else:
        print("一部に差分があります。上記の[NG]箇所を確認してください。")
    print("=" * 60)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # noqa: BLE001
        print(f"\nエラーが発生しました: {exc}", file=sys.stderr)
        sys.exit(1)
