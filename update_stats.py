#!/usr/bin/env python3
"""
readcine 导航站与各二级域名访问统计管理脚本
功能：
1. 查看当前各站点今日/昨日访问统计 (--show)；
2. 每日滚动归档 (--roll：将今日人数转为昨日人数，今日人数初始化为基准)；
3. 更新指定站点数据 (--set [site|movie|guide|events|news|organize|ai|deals] --today N --yesterday N)。
"""

import argparse
import json
import os
import sys
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
STATS_FILE = os.path.join(SCRIPT_DIR, "stats.json")


def load_stats():
    if not os.path.exists(STATS_FILE):
        print(f"❌ 找不到统计文件: {STATS_FILE}", file=sys.stderr)
        sys.exit(1)
    with open(STATS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_stats(data):
    with open(STATS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(f"✅ 统计数据已写入 {STATS_FILE}")


def show_stats(data):
    today_str = datetime.now().strftime("%Y-%m-%d")
    print("=" * 56)
    print(f"📊 readcine 访问统计面板 (数据日期: {data.get('updated', 'N/A')} | 当前: {today_str})")
    print("=" * 56)
    site = data.get("site", {})
    print(f"🌟 {site.get('name', '主站')}:")
    print(f"   今日访问: {site.get('today', 0)} 人 | 昨日访问: {site.get('yesterday', 0)} 人\n")
    print("🌐 二级域名服务卡片统计:")
    services = data.get("services", {})
    for svc_id, info in services.items():
        name = info.get("name", svc_id)
        today = info.get("today", 0)
        yesterday = info.get("yesterday", 0)
        print(f"   • [{svc_id:8s}] {name:10s} : 今日 {today:4d} 人 | 昨日 {yesterday:4d} 人")
    print("=" * 56)


def roll_stats(data):
    today_str = datetime.now().strftime("%Y-%m-%d")
    data["updated"] = today_str
    # 滚动主站
    site = data.get("site", {})
    site["yesterday"] = site.get("today", 0)
    # 保持合理基准启动
    site["today"] = max(10, int(site["yesterday"] * 0.2))

    # 滚动二级域名
    services = data.get("services", {})
    for _, info in services.items():
        info["yesterday"] = info.get("today", 0)
        info["today"] = max(5, int(info["yesterday"] * 0.2))

    save_stats(data)
    print("🌅 每日访问数据已滚动完成（今日数据已转存为昨日数据）！")
    show_stats(data)


def main():
    parser = argparse.ArgumentParser(description="readcine 导航站与各二级域名访问统计管理脚本")
    parser.add_argument("--show", action="store_true", help="打印当前统计信息")
    parser.add_argument("--roll", action="store_true", help="执行跨天滚动归档 (今日 -> 昨日)")
    parser.add_argument("--set", type=str, help="设置指定站点ID (如 site, movie, ai, deals)")
    parser.add_argument("--today", type=int, help="设置今日访问人数")
    parser.add_argument("--yesterday", type=int, help="设置昨日访问人数")
    args = parser.parse_args()

    data = load_stats()

    if args.roll:
        roll_stats(data)
        return

    if args.set:
        target = args.set.strip().lower()
        if target == "site":
            if args.today is not None:
                data["site"]["today"] = args.today
            if args.yesterday is not None:
                data["site"]["yesterday"] = args.yesterday
        elif target in data.get("services", {}):
            if args.today is not None:
                data["services"][target]["today"] = args.today
            if args.yesterday is not None:
                data["services"][target]["yesterday"] = args.yesterday
        else:
            print(f"❌ 未知站点ID: {target}，可选: site, {list(data.get('services', {}).keys())}")
            sys.exit(1)
        save_stats(data)
        show_stats(data)
        return

    show_stats(data)


if __name__ == "__main__":
    main()
