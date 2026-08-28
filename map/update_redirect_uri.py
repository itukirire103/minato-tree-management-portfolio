"""
update_redirect_uri.py
-------------------------
(仮称)樹木管理システム ポートフォリオ用
setup_azure_maps_aad.ps1 で作成したAzure ADアプリ登録(TreeMapPCF)の
SPAリダイレクトURIを、実際に作成したWebリソースのパスに合わせて更新する。

事前準備:
    同じフォルダに aad_setup_result.json が必要(setup_azure_maps_aad.ps1の実行結果)。
    pip install msal requests

実行方法:
    py update_redirect_uri.py
"""

import json
import os
import sys
import requests
import msal

PUBLIC_CLIENT_ID = "51f81489-12ee-4a9e-aaae-a2591f45987d"
HERE = os.path.dirname(os.path.abspath(__file__))
RESULT_FILE = os.path.join(HERE, "aad_setup_result.json")

NEW_REDIRECT_PATH = "/webresources/new_popup.html"


def load_setup_result():
    with open(RESULT_FILE, "r", encoding="utf-8-sig") as f:
        return json.load(f)


def get_graph_token(tenant_id):
    app = msal.PublicClientApplication(
        PUBLIC_CLIENT_ID,
        authority=f"https://login.microsoftonline.com/{tenant_id}",
    )
    flow = app.initiate_device_flow(scopes=["https://graph.microsoft.com/.default"])
    if "user_code" not in flow:
        raise RuntimeError(f"デバイスコードフローの開始に失敗しました: {flow}")
    print(flow["message"])
    result = app.acquire_token_by_device_flow(flow)
    if "access_token" not in result:
        raise RuntimeError(f"認証に失敗しました: {result.get('error_description')}")
    return result["access_token"]


def main():
    setup = load_setup_result()
    tenant_id = setup["tenantId"]
    app_object_id = setup["appObjectId"]
    env_url = setup["redirectUri"].split("/webresources/")[0]  # 元のURLからオリジン部分だけ取り出す
    new_redirect_uri = env_url + NEW_REDIRECT_PATH

    print(f"新しいリダイレクトURI: {new_redirect_uri}")

    token = get_graph_token(tenant_id)
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    url = f"https://graph.microsoft.com/v1.0/applications/{app_object_id}"
    body = {"spa": {"redirectUris": [new_redirect_uri]}}
    resp = requests.patch(url, headers=headers, json=body)

    if resp.status_code not in (200, 204):
        raise RuntimeError(f"更新に失敗しました: {resp.status_code} {resp.text}")

    print("リダイレクトURIを更新しました。")

    # aad_setup_result.jsonも更新しておく(以後の参照用)
    setup["redirectUri"] = new_redirect_uri
    with open(RESULT_FILE, "w", encoding="utf-8") as f:
        json.dump(setup, f, ensure_ascii=False, indent=2)
    print(f"{RESULT_FILE} も更新しました。")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # noqa: BLE001
        print(f"\nエラーが発生しました: {exc}", file=sys.stderr)
        sys.exit(1)
