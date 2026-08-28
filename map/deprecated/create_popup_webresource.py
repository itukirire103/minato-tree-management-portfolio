"""
create_popup_webresource.py
------------------------------
(仮称)樹木管理システム ポートフォリオ用
MSAL認証の中継用ページ(popup.html)を、Dataverseの「Webリソース」として
Web API経由で作成・公開するスクリプト。
PCFのControlManifestでの<html>宣言がうまく機能しなかったため、
独立したWebリソースとして直接作成する。

事前準備:
    同じフォルダに dataverse_common.py と popup.html が必要
    (popup.htmlが見つからない場合は TreeMapControl\\popup.html も探す)。

実行方法:
    py create_popup_webresource.py
"""

import base64
import os
import sys
import requests
from dataverse_common import connect, create_record

HERE = os.path.dirname(os.path.abspath(__file__))


def find_popup_html():
    candidates = [
        os.path.join(HERE, "popup.html"),
        os.path.join(HERE, "TreeMapControl", "popup.html"),
    ]
    for path in candidates:
        if os.path.exists(path):
            return path
    raise FileNotFoundError(
        f"popup.html が見つかりません。以下のいずれかに配置してください: {candidates}"
    )


def main():
    popup_path = find_popup_html()
    print(f"popup.html を読み込みます: {popup_path}")
    with open(popup_path, "r", encoding="utf-8") as f:
        html_content = f.read()

    base, headers, prefix = connect()

    name = f"{prefix}_popup.html"
    encoded = base64.b64encode(html_content.encode("utf-8")).decode("ascii")

    # 既に同名のWebリソースが存在するか確認(冪等性)
    check_url = f"{base}/webresourceset?$filter=name eq '{name}'&$select=webresourceid"
    resp = requests.get(check_url, headers=headers)
    resp.raise_for_status()
    existing = resp.json().get("value", [])

    if existing:
        record_id = existing[0]["webresourceid"]
        print(f"Webリソース『{name}』は既に存在します。内容を更新します。")
        update_url = f"{base}/webresourceset({record_id})"
        resp = requests.patch(update_url, headers=headers, json={"content": encoded})
        if resp.status_code not in (200, 204):
            raise RuntimeError(f"更新に失敗しました: {resp.status_code} {resp.text}")
    else:
        data = {
            "name": name,
            "displayname": "認証中継ページ(MSAL popup)",
            "webresourcetype": 1,  # 1 = HTML
            "content": encoded,
        }
        record_id = create_record(base, headers, "webresourceset", data)
        print(f"Webリソース『{name}』を作成しました(id={record_id})。")

    # 公開(公開しないとURLが有効にならない)
    publish_body = {
        "ParameterXml": (
            f"<importexportxml><webresources>"
            f"<webresource>{record_id}</webresource>"
            f"</webresources></importexportxml>"
        )
    }
    resp = requests.post(f"{base}/PublishXml", headers=headers, json=publish_body)
    if resp.status_code not in (200, 204):
        raise RuntimeError(f"公開に失敗しました: {resp.status_code} {resp.text}")
    print("公開しました。")

    print(f"\n想定されるURL(環境のURLに続けて):")
    print(f"  /webresources/{name}")
    print("\nこの値を、Azure ADアプリ登録のリダイレクトURIと")
    print("TreeMap.tsx の REDIRECT_URI 定数に設定してください。")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # noqa: BLE001
        print(f"\nエラーが発生しました: {exc}", file=sys.stderr)
        sys.exit(1)
