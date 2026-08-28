"""
create_env_variable.py
-------------------------
(仮称)樹木管理システム ポートフォリオ用
Azure Mapsのサブスクリプションキーを、Dataverseの「環境変数」として
安全に登録するスクリプト。

Entra ID認証(MSALのポップアップ)は、PCFが動くiframeの入れ子構造に起因する
timed_outエラーが解消できなかったため断念し、こちらのシンプルな方式に切り替えた。

環境変数を使う利点:
    - Azure MapsのキーがPCFのソースコードに一切書かれない
      (GitHub公開時にキーが漏れる心配がない)
    - キーを変更(ローテーション)してもコードの再デプロイが不要
    - PCFはDataverseに元々サインイン済みの状態(context.webAPI)から
      環境変数の値を取得するだけなので、追加のブラウザ認証が発生しない

事前準備:
    同じフォルダに dataverse_common.py が必要。

実行方法:
    py create_env_variable.py
    (実行するとAzure Mapsキーの入力を求められます。画面には表示されません)
"""

import getpass
import sys
import requests
from dataverse_common import connect, create_record, get_entity_set_name

ENV_VAR_SCHEMA_NAME = "AzureMapsSubscriptionKey"
ENV_VAR_DISPLAY_NAME = "Azure Maps サブスクリプションキー"


def find_definition(base, headers, prefix, schema_name, def_entity_set):
    full_name = f"{prefix}_{schema_name}"
    url = (
        f"{base}/{def_entity_set}"
        f"?$filter=schemaname eq '{full_name}'"
        f"&$select=environmentvariabledefinitionid,schemaname"
    )
    resp = requests.get(url, headers=headers)
    resp.raise_for_status()
    value = resp.json().get("value", [])
    return value[0] if value else None


def main():
    base, headers, prefix = connect()

    def_entity_set = get_entity_set_name(base, headers, "environmentvariabledefinition")
    val_entity_set = get_entity_set_name(base, headers, "environmentvariablevalue")

    secret_value = getpass.getpass("Azure Mapsのサブスクリプションキーを入力してください(画面には表示されません): ")
    if not secret_value.strip():
        print("キーが入力されませんでした。中止します。")
        sys.exit(1)

    existing = find_definition(base, headers, prefix, ENV_VAR_SCHEMA_NAME, def_entity_set)

    if existing:
        def_id = existing["environmentvariabledefinitionid"]
        print("環境変数の定義は既に存在します。値のみ更新します。")
    else:
        def_data = {
            "schemaname": f"{prefix}_{ENV_VAR_SCHEMA_NAME}",
            "displayname": ENV_VAR_DISPLAY_NAME,
            "type": 100000000,  # 100000000 = 文字列
        }
        def_id = create_record(base, headers, def_entity_set, def_data)
        print(f"環境変数の定義『{ENV_VAR_DISPLAY_NAME}』を作成しました。")

    # 値(environmentvariablevalue)を確認・作成/更新
    val_url = (
        f"{base}/{val_entity_set}"
        f"?$filter=_environmentvariabledefinitionid_value eq {def_id}"
        f"&$select=environmentvariablevalueid"
    )
    resp = requests.get(val_url, headers=headers)
    resp.raise_for_status()
    existing_values = resp.json().get("value", [])

    if existing_values:
        value_id = existing_values[0]["environmentvariablevalueid"]
        update_url = f"{base}/{val_entity_set}({value_id})"
        resp = requests.patch(update_url, headers=headers, json={"value": secret_value})
        if resp.status_code not in (200, 204):
            raise RuntimeError(f"値の更新に失敗しました: {resp.status_code} {resp.text}")
        print("環境変数の値を更新しました。")
    else:
        value_data = {
            "value": secret_value,
            "EnvironmentVariableDefinitionId@odata.bind": f"/{def_entity_set}({def_id})",
        }
        create_record(base, headers, val_entity_set, value_data)
        print("環境変数の値を新規作成しました。")

    print(f"\n完了しました。スキーマ名: {prefix}_{ENV_VAR_SCHEMA_NAME}")
    print("この値はPCFからDataverse Web API経由(context.webAPI)で取得します。")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # noqa: BLE001
        print(f"\nエラーが発生しました: {exc}", file=sys.stderr)
        sys.exit(1)
