"""
diagnose_map_binding.py
------------------------
(仮称)樹木管理システム ポートフォリオ用
TreeMapControlが実際に「樹木マップ」ビュー/フォームにバインドされているかを診断する。

verify_pcf_control.py は customcontrols への「登録」までしか確認できないため、
「登録はされているが、どの画面のどこにも使われていない」というケースを
切り分けるために作成した、読み取り専用の追加診断スクリプト。

事前準備:
    同じフォルダに dataverse_common.py が必要。

実行方法:
    py diagnose_map_binding.py <env_url>
    (env_url省略時は aad_setup_result.json 由来の既定値を使用)
"""

import sys
import requests
from dataverse_common import get_access_token, get_default_prefix

API_VERSION = "v9.2"
DEFAULT_ENV_URL = "https://orgfeb03658.crm7.dynamics.com"


def main():
    env_url = (sys.argv[1] if len(sys.argv) > 1 else DEFAULT_ENV_URL).rstrip("/")
    print(f"対象環境: {env_url}\n")
    print("ブラウザでのサインインが必要です。以下の案内に従ってください。\n")
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
    print(f"発行元プレフィックス: {prefix} / 対象テーブル論理名: {logical_name}\n")

    print("=" * 60)
    print("1. customcontrols への登録確認")
    print("=" * 60)
    url = f"{base}/customcontrols?$filter=contains(name,'TreeMapControl')&$select=name,customcontrolid"
    resp = requests.get(url, headers=headers)
    resp.raise_for_status()
    controls = resp.json().get("value", [])
    if controls:
        for c in controls:
            print(f"  登録あり: {c['name']} ({c['customcontrolid']})")
    else:
        print("  [!] customcontrolsに見つかりません。pac pcf push からやり直しが必要です。")
        return

    print("\n" + "=" * 60)
    print(f"2. {logical_name} のフォーム(systemform)を確認")
    print("=" * 60)
    url = f"{base}/systemforms?$filter=objecttypecode eq '{logical_name}'&$select=name,type,formxml"
    resp = requests.get(url, headers=headers)
    resp.raise_for_status()
    forms = resp.json().get("value", [])
    found_in_form = False
    for f in forms:
        formxml = f.get("formxml") or ""
        hit = "treemapcontrol" in formxml.lower()
        marker = " [発見]" if hit else ""
        print(f"  フォーム『{f['name']}』(type={f.get('type')}){marker}")
        if hit:
            found_in_form = True
    if not forms:
        print("  フォームが見つかりませんでした。")

    print("\n" + "=" * 60)
    print(f"3. {logical_name} のビュー(savedquery)を確認")
    print("=" * 60)
    url = f"{base}/savedqueries?$filter=returnedtypecode eq '{logical_name}'&$select=name,layoutxml"
    resp = requests.get(url, headers=headers)
    resp.raise_for_status()
    views = resp.json().get("value", [])
    found_in_view = False
    for v in views:
        layoutxml = v.get("layoutxml") or ""
        hit = "treemapcontrol" in layoutxml.lower()
        marker = " [発見]" if hit else ""
        print(f"  ビュー『{v['name']}』{marker}")
        if hit:
            found_in_view = True
    if not views:
        print("  ビューが見つかりませんでした。")

    print("\n" + "=" * 60)
    print("4. customcontroldefaultconfig(既定グリッドコントロール設定)を確認")
    print("=" * 60)
    try:
        url = f"{base}/customcontroldefaultconfigs?$select=customcontrolid,configxml,objecttypecode"
        resp = requests.get(url, headers=headers)
        if resp.status_code == 200:
            configs = resp.json().get("value", [])
            hit_configs = [c for c in configs if logical_name in (c.get("objecttypecode") or "")]
            if hit_configs:
                for c in hit_configs:
                    print(f"  発見: objecttypecode={c.get('objecttypecode')}")
            else:
                print(f"  {logical_name} 向けの既定グリッドコントロール設定は見つかりませんでした。")
        else:
            print(f"  [情報] この環境では確認できませんでした(status={resp.status_code})。")
    except Exception as exc:  # noqa: BLE001
        print(f"  [情報] 確認できませんでした: {exc}")

    print("\n" + "=" * 60)
    print("診断結果まとめ")
    print("=" * 60)
    if not found_in_form and not found_in_view:
        print("→ TreeMapControlはDataverseに登録済みだが、フォーム・ビューのどちらにもバインドされていません。")
        print("  Power Appsで対象のビュー(またはフォーム上のサブグリッド)を開き、")
        print("  『コントロールの追加』からTreeMapPCF.TreeMapControlを選択し、")
        print("  Webクライアント向けに設定した上で『すべてのカスタマイズを公開』が必要です。")
    else:
        print("→ バインドを確認できました。updateView()が呼ばれない別の原因(公開漏れ/キャッシュ等)を調査する必要があります。")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # noqa: BLE001
        print(f"\nエラーが発生しました: {exc}", file=sys.stderr)
        sys.exit(1)
