"""
verify_security_roles.py
---------------------------
(仮称)樹木管理システム ポートフォリオ用 セキュリティロール検証ハーネス

create_security_roles.py が定義している「どのロールに何の権限をどの深さで
付与するはずだったか(MATRIX)」を期待値として、実際にDataverseに設定されている
ロールの権限と突き合わせて差分レポートを表示する。

実行方法:
    py verify_security_roles.py

前提:
    create_security_roles.py を先に実行し、ロールが作成済みであること。
"""

import sys
import requests
from dataverse_common import connect
from create_security_roles import (
    ENTITIES,
    ROLES,
    MATRIX,
    DEPTH_MAP,
    CRUD_TO_TYPE,
    get_entity_privileges,
)

DEPTH_INT_TO_LABEL = {0: "Basic", 1: "Local", 2: "Deep", 3: "Global"}


def get_role_id(base, headers, name):
    url = f"{base}/roles?$select=roleid&$filter=name eq '{name}'"
    resp = requests.get(url, headers=headers)
    resp.raise_for_status()
    value = resp.json()["value"]
    return value[0]["roleid"] if value else None


def get_role_privileges(base, headers, role_id):
    """ロールに実際に付与されている(PrivilegeId, Depthラベル)の集合を返す。"""
    url = f"{base}/RetrieveRolePrivilegesRole(RoleId={role_id})"
    resp = requests.get(url, headers=headers)
    if resp.status_code != 200:
        print(f"  [警告] ロールの権限取得に失敗しました: {resp.status_code} {resp.text}")
        return set()
    data = resp.json()
    items = data.get("RolePrivileges", data.get("value", []))
    result = set()
    for item in items:
        pid = item.get("PrivilegeId") or item.get("privilegeid")
        depth_raw = item.get("Depth")
        if depth_raw is None:
            depth_raw = item.get("depth")
        if isinstance(depth_raw, int):
            depth_label = DEPTH_INT_TO_LABEL.get(depth_raw, str(depth_raw))
        else:
            depth_label = str(depth_raw)
        if pid:
            result.add((pid.lower(), depth_label))
    return result


def expected_for_role(role_name, privileges_by_entity):
    """このロールが持つべき(PrivilegeId, Depthラベル, 説明)のリストを返す。"""
    expected = []
    for entity_suffix, role_map in MATRIX.items():
        crud, scope = role_map.get(role_name, ("", "なし"))
        if not crud or scope == "なし":
            continue
        depth = DEPTH_MAP[scope]
        entity_privs = privileges_by_entity[entity_suffix]

        types_needed = [CRUD_TO_TYPE[letter] for letter in crud]
        if "C" in crud or "U" in crud:
            types_needed += ["Append", "AppendTo"]

        for ptype in types_needed:
            if ptype in entity_privs:
                desc = f"{entity_suffix}.{ptype}({depth})"
                expected.append((entity_privs[ptype].lower(), depth, desc))
    return expected


def main():
    base, headers, prefix = connect()

    print("\n----- 各テーブルの権限IDを再取得します -----")
    privileges_by_entity = {}
    for suffix in ENTITIES:
        logical_name = f"{prefix}_{suffix}"
        privileges_by_entity[suffix] = get_entity_privileges(base, headers, logical_name)

    print("\n" + "=" * 60)
    print("セキュリティロール検証結果")
    print("=" * 60)

    total_roles = 0
    ok_roles = 0
    total_privs = 0
    ok_privs = 0

    for role_name in ROLES:
        if role_name == "システム管理者":
            print(f"\n■ {role_name} : 組み込みロールのため検証をスキップします(常にフルアクセス)。")
            continue

        total_roles += 1
        print(f"\n■ {role_name} を検証します...")
        role_id = get_role_id(base, headers, role_name)
        if not role_id:
            print(f"  → ロールが見つかりません。create_security_roles.pyを実行しましたか？")
            continue

        actual = get_role_privileges(base, headers, role_id)
        expected = expected_for_role(role_name, privileges_by_entity)

        missing = []
        for pid, depth, desc in expected:
            total_privs += 1
            if (pid, depth) in actual:
                ok_privs += 1
            else:
                missing.append(desc)

        exp_total = len(expected)
        exp_ok = exp_total - len(missing)
        status = "OK" if not missing else "差分あり"
        print(f"  結果: {status}  ({exp_ok}/{exp_total} 件一致)")
        if missing:
            print(f"  不足している権限: {', '.join(missing)}")
        else:
            ok_roles += 1

    print("\n" + "=" * 60)
    print(f"総合結果: ロール {ok_roles}/{total_roles} 件OK, 権限 {ok_privs}/{total_privs} 件OK")
    print("=" * 60)

    if ok_roles == total_roles and ok_privs == total_privs:
        print("\nすべてのロールが設計通りに設定されています。")
    else:
        print("\n一部に差分があります。上記の『不足している権限』を確認してください。")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # noqa: BLE001
        print(f"\nエラーが発生しました: {exc}", file=sys.stderr)
        sys.exit(1)
