"""
run_load_test.py
-------------------
(仮称)樹木管理システム ポートフォリオ用
非機能要件#8(最大10名程度が同時アクセスしても支障なく利用)・
#21(検索スピードや画面展開が遅延しない構成)に対応するための簡易負荷テスト。

専用ツール(JMeter等)の代わりに、Python標準のconcurrent.futuresで
疑似的な同時アクセスを再現し、Dataverse Web APIへの応答時間を計測する。

実行方法:
    py run_load_test.py <env_url> [同時実行数(既定10)] [ワーカーあたりリクエスト数(既定10)]
"""
import sys
import time
import statistics
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
from dataverse_common import get_access_token, get_default_prefix, get_entity_set_name

API_VERSION = "v9.2"
DEFAULT_ENV_URL = "https://orgfeb03658.crm7.dynamics.com"


def worker(base, headers, entity_set_name, worker_id, requests_per_worker):
    times = []
    for _ in range(requests_per_worker):
        url = f"{base}/{entity_set_name}?$top=50&$orderby=createdon desc"
        start = time.perf_counter()
        resp = requests.get(url, headers=headers)
        elapsed = time.perf_counter() - start
        resp.raise_for_status()
        times.append(elapsed)
    return worker_id, times


def main():
    env_url = (sys.argv[1] if len(sys.argv) > 1 else DEFAULT_ENV_URL).rstrip("/")
    concurrency = int(sys.argv[2]) if len(sys.argv) > 2 else 10
    requests_per_worker = int(sys.argv[3]) if len(sys.argv) > 3 else 10

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
    entity_set_name = get_entity_set_name(base, headers, f"{prefix}_tree")

    print(f"対象環境: {env_url}")
    print(f"同時実行数(疑似同時アクセスユーザー数): {concurrency}")
    print(f"ワーカーあたりリクエスト数: {requests_per_worker}")
    print(f"合計リクエスト数: {concurrency * requests_per_worker}\n")

    all_times = []
    overall_start = time.perf_counter()
    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = [
            executor.submit(worker, base, headers, entity_set_name, i, requests_per_worker)
            for i in range(concurrency)
        ]
        for future in as_completed(futures):
            worker_id, times = future.result()
            all_times.extend(times)
            print(f"  ワーカー{worker_id}: 完了 (平均 {statistics.mean(times) * 1000:.0f}ms)")

    overall_elapsed = time.perf_counter() - overall_start

    print("\n" + "=" * 60)
    print("結果サマリー")
    print("=" * 60)
    print(f"総リクエスト数: {len(all_times)}")
    print(f"全体所要時間: {overall_elapsed:.2f}秒")
    print(f"スループット: {len(all_times) / overall_elapsed:.1f} req/秒")
    print(f"平均応答時間: {statistics.mean(all_times) * 1000:.0f}ms")
    print(f"中央値: {statistics.median(all_times) * 1000:.0f}ms")
    print(f"最小/最大: {min(all_times) * 1000:.0f}ms / {max(all_times) * 1000:.0f}ms")
    sorted_times = sorted(all_times)
    p95_idx = min(int(len(sorted_times) * 0.95), len(sorted_times) - 1)
    print(f"95パーセンタイル: {sorted_times[p95_idx] * 1000:.0f}ms")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # noqa: BLE001
        print(f"\nエラーが発生しました: {exc}", file=sys.stderr)
        sys.exit(1)
