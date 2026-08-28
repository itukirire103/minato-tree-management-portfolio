"""
seed_tree_data.py
--------------------
(仮称)樹木管理システム ポートフォリオ用
樹木マスタに実データ相当のサンプルを一括投入するスクリプト。

港区が公開したサンプルデータ(仕様書別紙1-2)の樹種・路線番号の命名規則
(芝05、芝06...)・座標範囲(港区芝周辺、北緯35.66台、東経139.75台)を参考に、
統計的に自然な分布(健全度はA:B1:B2:C=概ね50:30:15:5等)で合成データを生成する。

事前準備:
    同じフォルダに dataverse_common.py が必要。

実行方法:
    py seed_tree_data.py
"""

import random
import sys
import datetime

from dataverse_common import connect, get_entity_set_name, create_record

TREE_COUNT = 300

# 港区の公開サンプル(街路樹診断結果一覧)に実在した樹種+都内街路樹で一般的な樹種
SPECIES = [
    ("ホルトノキ", "常緑"), ("クスノキ", "常緑"), ("シイノキ", "常緑"),
    ("ケヤキ", "落葉"), ("イチョウ", "落葉"), ("ソメイヨシノ", "落葉"),
    ("ハナミズキ", "落葉"), ("トウカエデ", "落葉"), ("プラタナス", "落葉"),
    ("ヤマボウシ", "落葉"), ("モミジバフウ", "落葉"), ("ユリノキ", "落葉"),
]

# 別紙1-2の実データに登場した路線番号(芝05〜芝07等)の命名規則を踏襲
ROUTE_PREFIX = "芝"
ROUTE_NUMBERS = [f"{i:02d}" for i in range(1, 24)]  # 芝01〜芝23

# 港区芝周辺のおおよその座標範囲(別紙1-2の実データを参考)
BASE_LAT = 35.660
BASE_LNG = 139.748

HEALTH_WEIGHTS = [("A", 50), ("B1", 30), ("B2", 15), ("C", 5)]
STATUS_WEIGHTS = [("現存", 90), ("伐採済", 5), ("植替え済", 5)]
SIZE_WEIGHTS = [("高木", 75), ("中木", 20), ("低木", 5)]


def weighted_choice(pairs):
    items, weights = zip(*pairs)
    return random.choices(items, weights=weights, k=1)[0]


def random_date(start_year=1995, end_year=2018):
    start = datetime.date(start_year, 1, 1)
    end = datetime.date(end_year, 12, 31)
    delta_days = (end - start).days
    d = start + datetime.timedelta(days=random.randint(0, delta_days))
    return d.isoformat()


def generate_trees(count):
    trees = []
    # 路線ごとに連続した樹木番号・近接した座標を割り振り、実データの雰囲気に寄せる
    per_route = max(1, count // len(ROUTE_NUMBERS))
    tree_index = 0
    for route_no in ROUTE_NUMBERS:
        route_lat = BASE_LAT + random.uniform(-0.01, 0.01)
        route_lng = BASE_LNG + random.uniform(-0.01, 0.01)
        n_this_route = per_route + (1 if random.random() < 0.3 else 0)
        for i in range(1, n_this_route + 1):
            if tree_index >= count:
                break
            species, leaf_type = random.choice(SPECIES)
            height = round(random.uniform(3.0, 15.0), 1)
            girth = round(random.uniform(20, 95))
            spread = round(random.uniform(1.5, 7.0), 1)
            lat = round(route_lat + i * 0.00015 + random.uniform(-0.00005, 0.00005), 6)
            lng = round(route_lng + i * 0.00015 + random.uniform(-0.00005, 0.00005), 6)

            trees.append({
                "route_number": f"{ROUTE_PREFIX}{route_no}",
                "tree_number": f"{ROUTE_PREFIX}{route_no}-{i:03d}",
                "address": f"港区芝{random.randint(1, 5)}丁目",
                "species": species,
                "leaf_type": leaf_type,
                "height": height,
                "girth": girth,
                "spread": spread,
                "size_class": weighted_choice(SIZE_WEIGHTS),
                "health": weighted_choice(HEALTH_WEIGHTS),
                "status": weighted_choice(STATUS_WEIGHTS),
                "planted_date": random_date(),
                "has_stake": random.random() < 0.3,
                "has_tag": random.random() < 0.5,
                "lat": lat,
                "lng": lng,
            })
            tree_index += 1
        if tree_index >= count:
            break
    return trees[:count]


def choice_value_map(base, headers, logical_name, column_suffix, prefix):
    """選択肢(Picklist)列のラベル→内部値(Value)対応表を取得する。"""
    import requests
    attr_logical = f"{prefix}_{column_suffix}".lower()
    url = (
        f"{base}/EntityDefinitions(LogicalName='{logical_name}')"
        f"/Attributes(LogicalName='{attr_logical}')/Microsoft.Dynamics.CRM.PicklistAttributeMetadata"
        f"?$select=LogicalName&$expand=OptionSet"
    )
    resp = requests.get(url, headers=headers)
    resp.raise_for_status()
    options = resp.json()["OptionSet"]["Options"]
    mapping = {}
    for opt in options:
        jp_label = opt["Label"]["LocalizedLabels"][0]["Label"]
        mapping[jp_label] = opt["Value"]
    return mapping


def main():
    base, headers, prefix = connect()
    logical_name = f"{prefix}_tree"
    entity_set = get_entity_set_name(base, headers, logical_name)

    print("選択肢列(常緑落葉区分/樹木区分/現在の健全度/ステータス)の内部値を取得します...")
    leaf_map = choice_value_map(base, headers, logical_name, "LeafType", prefix)
    size_map = choice_value_map(base, headers, logical_name, "SizeClass", prefix)
    health_map = choice_value_map(base, headers, logical_name, "HealthStatus", prefix)
    status_map = choice_value_map(base, headers, logical_name, "Status", prefix)

    print(f"\n{TREE_COUNT}件のサンプル樹木データを生成します...")
    trees = generate_trees(TREE_COUNT)

    confirm = input(
        f"{len(trees)}件のレコードを樹木マスタに新規作成します。"
        f"(このスクリプトは重複防止機能を持たないため、複数回実行すると重複します) "
        f"続行しますか？ (y/n): "
    )
    if confirm.strip().lower() != "y":
        print("中止しました。")
        return

    created = 0
    for t in trees:
        data = {
            f"{prefix}_treenumber": t["tree_number"],
            f"{prefix}_routenumber": t["route_number"],
            f"{prefix}_address": t["address"],
            f"{prefix}_species": t["species"],
            f"{prefix}_treeheight": t["height"],
            f"{prefix}_trunkgirth": t["girth"],
            f"{prefix}_crownspread": t["spread"],
            f"{prefix}_leaftype": leaf_map[t["leaf_type"]],
            f"{prefix}_sizeclass": size_map[t["size_class"]],
            f"{prefix}_healthstatus": health_map[t["health"]],
            f"{prefix}_status": status_map[t["status"]],
            f"{prefix}_planteddate": t["planted_date"],
            f"{prefix}_hasstake": t["has_stake"],
            f"{prefix}_hastag": t["has_tag"],
            f"{prefix}_latitude": t["lat"],
            f"{prefix}_longitude": t["lng"],
        }
        try:
            create_record(base, headers, entity_set, data)
            created += 1
            if created % 25 == 0:
                print(f"  {created}/{len(trees)} 件作成しました...")
        except Exception as exc:  # noqa: BLE001
            print(f"  [警告] {t['tree_number']} の作成に失敗しました: {exc}")

    print(f"\n完了しました。{created}/{len(trees)} 件のレコードを作成しました。")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # noqa: BLE001
        print(f"\nエラーが発生しました: {exc}", file=sys.stderr)
        sys.exit(1)
