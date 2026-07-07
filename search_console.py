import json
import re
from google.oauth2 import service_account
from googleapiclient.discovery import build

def get_search_console_service(service_account_json_val):
    """
    サービスアカウントJSON（辞書、JSON文字列、またはファイルパス）から認証情報を作成し、Search Consoleサービスオブジェクトを返します。
    戻り値: (service, error_message)
    """
    if not service_account_json_val:
        return None, "サービスアカウントのJSONキーが空です。"
    try:
        import copy
        # 辞書オブジェクト（またはdictのように振る舞うAttrDictなど）の場合
        if isinstance(service_account_json_val, dict) or (not isinstance(service_account_json_val, str) and hasattr(service_account_json_val, "get")):
            # 元のオブジェクトを壊さないよう辞書としてディープコピー
            info = dict(copy.deepcopy(service_account_json_val))
            if "private_key" in info and isinstance(info["private_key"], str):
                info["private_key"] = info["private_key"].replace("\\n", "\n")
            credentials = service_account.Credentials.from_service_account_info(info)
        # JSON文字列の場合
        elif isinstance(service_account_json_val, str) and service_account_json_val.strip().startswith("{"):
            info = json.loads(service_account_json_val)
            if "private_key" in info and isinstance(info["private_key"], str):
                info["private_key"] = info["private_key"].replace("\\n", "\n")
            credentials = service_account.Credentials.from_service_account_info(info)
        # ファイルパスの場合
        else:
            credentials = service_account.Credentials.from_service_account_file(str(service_account_json_val))
            
        scoped_credentials = credentials.with_scopes(['https://www.googleapis.com/auth/webmasters.readonly'])
        service = build('webmasters', 'v3', credentials=scoped_credentials)
        return service, None
    except Exception as e:
        err_msg = str(e)
        print(f"❌ Search Console 認証情報作成中にエラーが発生しました: {err_msg}")
        return None, err_msg

def fetch_performance_data(service, property_url: str, days: int = 30) -> list:
    """
    Search Consoleから過去N日間のページごとのパフォーマンスデータ（URL、クエリ、表示回数、クリック数、順位）を取得します。
    """
    if not service or not property_url:
        return []
        
    from datetime import datetime, timedelta
    # 直近3日はデータが確定していないことが多いため、3日前を終点とします
    end_date = datetime.now() - timedelta(days=3)
    start_date = end_date - timedelta(days=days)
    
    request = {
        'startDate': start_date.strftime('%Y-%m-%d'),
        'endDate': end_date.strftime('%Y-%m-%d'),
        'dimensions': ['page', 'query'],
        'rowLimit': 5000
    }
    
    try:
        response = service.searchanalytics().query(siteUrl=property_url, body=request).execute()
        rows = response.get('rows', [])
        data = []
        for row in rows:
            page = row.get('keys', [None, None])[0]
            query = row.get('keys', [None, None])[1]
            data.append({
                'url': page,
                'query': query,
                'clicks': row.get('clicks', 0),
                'impressions': row.get('impressions', 0),
                'ctr': row.get('ctr', 0.0),
                'position': row.get('position', 0.0)
            })
        return data
    except Exception as e:
        print(f"❌ Search Console データ取得中にエラーが発生しました: {e}")
        return []

def analyze_low_performing_pages(perf_data: list, min_impressions: int = 10) -> dict:
    """
    パフォーマンスデータを解析し、改善の余地が大きいページとそれに紐づく低パフォーマンスクエリを特定します。
    - 判定基準:
      - 掲載順位が 10位 〜 30位（リライトで1ページ目に入れる可能性が高い）
      - 表示回数（impressions）が一定以上ある（min_impressions）
    返り値: { url: { "queries": [query1, query2, ...], "avg_position": float, "impressions": int, "clicks": int } }
    """
    results = {}
    for item in perf_data:
        url = item['url']
        pos = item['position']
        imp = item['impressions']
        query = item['query']
        clicks = item['clicks']
        
        # 改善の余地がある順位範囲（10〜30位）かつ、表示回数が一定数以上
        if 10.0 <= pos <= 30.0 and imp >= min_impressions:
            if url not in results:
                results[url] = {
                    "queries": [],
                    "impressions": 0,
                    "clicks": 0,
                    "positions": []
                }
            # クエリを除外（URLとクエリが全く同じものは除外）
            if query and query != "":
                results[url]["queries"].append(query)
            results[url]["impressions"] += imp
            results[url]["clicks"] += clicks
            results[url]["positions"].append(pos)
            
    # 平均順位を計算し、表示回数順にソートしやすいように整形
    for url, info in list(results.items()):
        if not info["positions"]:
            del results[url]
            continue
        info["avg_position"] = round(sum(info["positions"]) / len(info["positions"]), 1)
        # 重複クエリを削除し、インプレッション順にソートするためにクエリリストを整理
        info["queries"] = list(set(info["queries"]))[:5]
        del info["positions"]
        
    # インプレッションが多い順に並び替える
    sorted_results = dict(sorted(results.items(), key=lambda x: x[1]['impressions'], reverse=True))
    return sorted_results

def extract_wp_post_id_from_url(url: str) -> int:
    """
    URLからWordPressの投稿IDを推測または抽出します。
    例：
      https://miyakojima-rentacar.net/article/archives/123 -> 123
      https://miyakojima-rentacar.net/article/?p=123 -> 123
    """
    if not url:
        return None
        
    # パターン1: ?p=123
    p_match = re.search(r'\?p=(\d+)', url)
    if p_match:
        return int(p_match.group(1))
        
    # パターン2: /archives/123
    archives_match = re.search(r'/archives/(\d+)', url)
    if archives_match:
        return int(archives_match.group(1))
        
    return None
