#!/usr/bin/env python3
"""
从 Cloudflare Web Analytics (RUM) 获取 100% 真实的独立访客数 (Visits / UV)
并同步更新 stats.json。

使用说明：
  python3 sync_cf_stats.py
  python3 sync_cf_stats.py --dry-run
"""

import os
import sys
import json
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
STATS_FILE = os.path.join(SCRIPT_DIR, "stats.json")
TOKEN_FILE = os.path.join(SCRIPT_DIR, "cf_token.txt")

# Cloudflare 配置
CF_ACCOUNT_TAG = os.getenv("CF_ACCOUNT_TAG", "0381e8ee971cfcbfb2a3102730d8d4c0")
CF_SITE_TAG = os.getenv("CF_SITE_TAG", "676bf273aad84e87b7292da0b707976a")


def get_cf_token():
    token = os.getenv("CF_ANALYTICS_TOKEN", "").strip()
    if token:
        return token
    if os.path.exists(TOKEN_FILE):
        try:
            with open(TOKEN_FILE, "r", encoding="utf-8") as f:
                return f.read().strip()
        except Exception:
            pass
    server_token_file = "/etc/cloudflare/analytics.token"
    if os.path.exists(server_token_file):
        try:
            with open(server_token_file, "r", encoding="utf-8") as f:
                return f.read().strip()
        except Exception:
            pass
    return None


# 域名与 stats.json key 映射
HOST_MAP = {
    "readcine.com": "site",
    "go.readcine.com": "site",
    "movie.readcine.com": "movie",
    "guide.readcine.com": "guide",
    "events.readcine.com": "events",
    "news.readcine.com": "news",
    "organize.readcine.com": "organize",
    "ai.readcine.com": "ai",
    "deals.readcine.com": "deals",
}


def query_cf_analytics(token):
    now = datetime.now(timezone.utc)
    start_time = (now - timedelta(days=3)).strftime("%Y-%m-%dT00:00:00Z")

    query = """
    query GetSiteAnalytics($accountTag: String!, $siteTag: String!, $startTime: String!) {
      viewer {
        accounts(filter: {accountTag: $accountTag}) {
          rumPageloadEventsAdaptiveGroups(
            filter: {siteTag: $siteTag, datetime_geq: $startTime}
            limit: 200
            orderBy: [date_DESC]
          ) {
            dimensions {
              date
              requestHost
            }
            count
            sum {
              visits
            }
          }
        }
      }
    }
    """

    req_data = json.dumps({
        "query": query,
        "variables": {
            "accountTag": CF_ACCOUNT_TAG,
            "siteTag": CF_SITE_TAG,
            "startTime": start_time
        }
    }).encode("utf-8")

    req = urllib.request.Request(
        "https://api.cloudflare.com/client/v4/graphql",
        data=req_data,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
    )

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if data.get("errors"):
                print(f"❌ GraphQL Errors: {data['errors']}", file=sys.stderr)
                return None
            return data["data"]["viewer"]["accounts"][0]["rumPageloadEventsAdaptiveGroups"]
    except Exception as e:
        print(f"❌ 请求 Cloudflare 失败: {e}", file=sys.stderr)
        return None


def sync():
    dry_run = "--dry-run" in sys.argv
    token = get_cf_token()
    if not token:
        print("❌ 未找到 Cloudflare API Token。请设置 CF_ANALYTICS_TOKEN 环境变量或在同目录下创建 cf_token.txt 文件。", file=sys.stderr)
        sys.exit(1)

    records = query_cf_analytics(token)
    if records is None:
        sys.exit(1)

    bj_tz = timezone(timedelta(hours=8))
    now_bj = datetime.now(bj_tz)
    today_str = now_bj.strftime("%Y-%m-%d")
    yesterday_str = (now_bj - timedelta(days=1)).strftime("%Y-%m-%d")

    daily_stats = {}
    for r in records:
        date = r["dimensions"]["date"]
        host = r["dimensions"]["requestHost"]
        visits = r["sum"]["visits"]

        if date not in daily_stats:
            daily_stats[date] = {}

        key = HOST_MAP.get(host, host)
        daily_stats[date][key] = daily_stats[date].get(key, 0) + visits

    print(f"📡 Cloudflare 数据已拉取:")
    for d, s in sorted(daily_stats.items(), reverse=True):
        print(f"   [{d}]: {s}")

    if not os.path.exists(STATS_FILE):
        print(f"❌ 找不到 stats.json: {STATS_FILE}", file=sys.stderr)
        sys.exit(1)

    with open(STATS_FILE, "r", encoding="utf-8") as f:
        stats = json.load(f)

    stats["updated"] = today_str

    today_site = daily_stats.get(today_str, {}).get("site", 0)
    yesterday_site = daily_stats.get(yesterday_str, {}).get("site", 0)
    stats["site"]["today"] = today_site
    stats["site"]["yesterday"] = yesterday_site

    for svc_key, svc_info in stats.get("services", {}).items():
        svc_today = daily_stats.get(today_str, {}).get(svc_key, 0)
        svc_yesterday = daily_stats.get(yesterday_str, {}).get(svc_key, 0)
        svc_info["today"] = svc_today
        svc_info["yesterday"] = svc_yesterday

    print(f"\n📊 汇总后的真实访问人数 (UV):")
    print(f"   主站 ({stats['site']['name']}): 今日 {stats['site']['today']} 人 | 昨日 {stats['site']['yesterday']} 人")
    for k, v in stats["services"].items():
        print(f"   • {v['name']} ({k}): 今日 {v['today']} 人 | 昨日 {v['yesterday']} 人")

    if dry_run:
        print("\n🔍 --dry-run 模式，未修改文件。")
        return

    with open(STATS_FILE, "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(f"\n✅ stats.json 已更新为 Cloudflare 真实访问数据！")


if __name__ == "__main__":
    sync()
