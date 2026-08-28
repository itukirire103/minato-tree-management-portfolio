"""
create_security_roles.py
---------------------------
(仮称)樹木管理システム ポートフォリオ用
Dataverse Web API を使って6区分アカウントのセキュリティロールを自動作成するスクリプト。

設計根拠: Dataverseデータモデル設計書.xlsx シート3「セキュリティロール」

やっていること:
    1. 対象7テーブルそれぞれについて、Create/Read/Write/Delete/Append/AppendTo の
       権限ID(Privilege)をDataverseから検索して控える。
    2. 6つのカスタムロールを作成する(既存ならスキップ)。
    3. 設計書の権限マトリクスに従い、各ロールに各テーブルの権限を付与する。

注意:
    セキュリティロールの権限IDの命名規則は、テーブル作成に比べて確認が難しい領域です。
    想定通りの名前で見つからない権限があった場合は、そのテーブルで実際に見つかった
    権限名の一覧を表示するので、それを見て一緒に調整します。

実行方法:
    py create_security_roles.py
"""

import sys
import requests
from dataverse_common import connect

# 対象7テーブル(スキーマ接尾辞)
ENTITIES = ["tree", "diagnosis", "inspection", "workhistory", "replant", "complaint", "vendor"]

ROLES = ["システム管理者", "各所管理者", "区一般職員", "街路樹管理委託事業者", "協定管理者", "その他(閲覧専用)"]

# entity -> role -> (CRUD文字列, スコープ) 。スコープ: 組織/BU/自分/なし
# 出典: Dataverseデータモデル設計書.xlsx シート3
MATRIX = {
    "tree": {
        "システム管理者": ("CRUD", "組織"),
        "各所管理者": ("CRU", "組織"),
        "区一般職員": ("CRU", "組織"),
        "街路樹管理委託事業者": ("RU", "BU"),
        "協定管理者": ("R", "BU"),
        "その他(閲覧専用)": ("R", "組織"),
    },
    "diagnosis": {
        "システム管理者": ("CRUD", "組織"),
        "各所管理者": ("CRU", "組織"),
        "区一般職員": ("R", "組織"),
        "街路樹管理委託事業者": ("R", "BU"),
        "協定管理者": ("R", "BU"),
        "その他(閲覧専用)": ("R", "組織"),
    },
    "inspection": {
        "システム管理者": ("CRUD", "組織"),
        "各所管理者": ("CRU", "組織"),
        "区一般職員": ("CRU", "組織"),
        "街路樹管理委託事業者": ("CRU", "BU"),
        "協定管理者": ("CR", "BU"),
        "その他(閲覧専用)": ("R", "組織"),
    },
    "workhistory": {
        "システム管理者": ("CRUD", "組織"),
        "各所管理者": ("CRU", "組織"),
        "区一般職員": ("CRU", "組織"),
        "街路樹管理委託事業者": ("CRU", "BU"),
        "協定管理者": ("R", "BU"),
        "その他(閲覧専用)": ("R", "組織"),
    },
    "replant": {
        "システム管理者": ("CRUD", "組織"),
        "各所管理者": ("CRU", "組織"),
        "区一般職員": ("CRU", "組織"),
        "街路樹管理委託事業者": ("R", "BU"),
        "協定管理者": ("R", "BU"),
        "その他(閲覧専用)": ("R", "組織"),
    },
    "complaint": {
        "システム管理者": ("CRUD", "組織"),
        "各所管理者": ("CRU", "組織"),
        "区一般職員": ("CRU", "組織"),
        "街路樹管理委託事業者": ("R", "BU"),
        "協定管理者": ("R", "BU"),
        "その他(閲覧専用)": ("", "なし"),
    },
    "vendor": {
        "システム管理者": ("CRUD", "組織"),
        "各所管理者": ("CRU", "組織"),
        "区一般職員": ("R", "組織"),
        "街路樹管理委託事業者": ("R", "自分"),
        "協定管理者": ("R", "自分"),
        "その他(閲覧専用)": ("", "なし"),
    },
}

DEPTH_MAP = {"組織": "Global", "BU": "Local", "自分": "Basic"}
CRUD_TO_TYPE = {"C": "Create", "R": "Read", "U": "Write", "D": "Delete"}


def get_root_business_unit(base, headers):
    url = f"{base}/businessunits?$select=businessunitid,name&$filter=_parentbusinessunitid_value eq null"
    resp = requests.get(url, headers=headers)
    resp.raise_for_status()
    value = resp.json()["value"]
    if not value:
        raise RuntimeError("ルートビジネスユニットが見つかりませんでした。")
    return value[0]["businessunitid"]


def get_entity_privileges(base, headers, logical_name):
    """指定テーブルに対応する権限(Create/Read/Write/Delete/Append/AppendTo)のIDを検索する。"""
    url = f"{base}/privileges?$select=privilegeid,name&$filter=contains(name,'{logical_name}')"
    resp = requests.get(url, headers=headers)
    resp.raise_for_status()
    found = resp.json()["value"]
    result = {}
    wanted = ["Create", "Read", "Write", "Delete", "Append", "AppendTo"]
    for ptype in wanted:
        expected = f"prv{ptype}{logical_name}".lower()
        for item in found:
            if item["name"].lower() == expected:
                result[ptype] = item["privilegeid"]
                break
    missing = [p for p in wanted if p not in result]
    if missing:
        print(f"  [警告] {logical_name}: 想定した名前で見つからなかった権限 = {missing}")
        print(f"         実際に見つかった権限名一覧: {[i['name'] for i in found]}")
    return result


def get_or_create_role(base, headers, name, root_bu_id):
    url = f"{base}/roles?$select=roleid&$filter=name eq '{name}'"
    resp = requests.get(url, headers=headers)
    resp.raise_for_status()
    value = resp.json()["value"]
    if value:
        print(f"ロール『{name}』は既に存在します。")
        return value[0]["roleid"]

    body = {
        "name": name,
        "businessunitid@odata.bind": f"/businessunits({root_bu_id})",
    }
    resp = requests.post(f"{base}/roles", headers=headers, json=body)
    if resp.status_code not in (200, 201, 204):
        raise RuntimeError(f"ロール『{name}』の作成に失敗しました: {resp.status_code} {resp.text}")
    role_id = resp.headers.get("OData-EntityId", "").split("(")[-1].rstrip(")")
    print(f"ロール『{name}』を作成しました。")
    return role_id


def assign_privileges(base, headers, role_id, role_name, privileges_by_entity):
    """1ロール分の権限をまとめて付与する。"""
    payload_privileges = []
    for entity_suffix, crud_scope in MATRIX.items():
        crud, scope = crud_scope.get(role_name, ("", "なし"))
        if not crud or scope == "なし":
            continue
        depth = DEPTH_MAP[scope]
        entity_privs = privileges_by_entity[entity_suffix]

        # CRUDで指定された権限
        for letter in crud:
            ptype = CRUD_TO_TYPE[letter]
            if ptype in entity_privs:
                payload_privileges.append({"PrivilegeId": entity_privs[ptype], "Depth": depth})

        # 作成/更新権限があるなら、ルックアップ設定に必要なAppend/AppendToも付与する
        if ("C" in crud or "U" in crud):
            for ptype in ("Append", "AppendTo"):
                if ptype in entity_privs:
                    payload_privileges.append({"PrivilegeId": entity_privs[ptype], "Depth": depth})

    if not payload_privileges:
        print(f"  ロール『{role_name}』には付与する権限がありません。スキップします。")
        return

    url = f"{base}/roles({role_id})/Microsoft.Dynamics.CRM.AddPrivilegesRole"
    resp = requests.post(url, headers=headers, json={"Privileges": payload_privileges})
    if resp.status_code not in (200, 201, 204):
        print(f"  ロール『{role_name}』への権限付与に失敗しました: {resp.status_code} {resp.text}")
    else:
        print(f"  ロール『{role_name}』に権限を{len(payload_privileges)}件付与しました。")


def main():
    base, headers, prefix = connect()

    print("\n----- 各テーブルの権限IDを検索します -----")
    privileges_by_entity = {}
    for suffix in ENTITIES:
        logical_name = f"{prefix}_{suffix}"
        privileges_by_entity[suffix] = get_entity_privileges(base, headers, logical_name)

    root_bu_id = get_root_business_unit(base, headers)

    print("\n----- ロールを作成し、権限を付与します -----")
    for role_name in ROLES:
        role_id = get_or_create_role(base, headers, role_name, root_bu_id)
        assign_privileges(base, headers, role_id, role_name, privileges_by_entity)

    print("\n完了しました。Power Apps画面(Settings > ユーザーとアクセス許可 > セキュリティロール)で確認してください。")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # noqa: BLE001
        print(f"\nエラーが発生しました: {exc}", file=sys.stderr)
        sys.exit(1)
