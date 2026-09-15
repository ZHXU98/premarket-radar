#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fetch_news_cn.py — 国内重要新闻采集（盘前雷达 · 数据层）

数据源：同花顺「盘中推送」接口
  https://news.10jqka.com.cn/tapp/news/push/stock/?page=N
  返回 JSON：data.list[]，每条含：
    title   标题
    digest  摘要
    url     链接
    ctime   发布时间（Unix 时间戳，秒）
    import  重要性（"0"=普通，"3"=重要；>0 即保留）
    tag     标签（如 "港股,A股"）

采集策略：
  1. 从 page=1 向后翻页（接口按时间倒序，最新在前）。
  2. 只保留 import > 0 的「重要」新闻（0 为噪音，剔除）。
  3. 停止条件（先到先停，谁先满足就停）：
       - 已凑够 target 条（默认 20）；或
       - 已翻到 window_hours 时间窗之前（默认 8 小时）。
     夜盘多为海外消息、国内消息少，故窗口取 8 小时足够。
  4. 按 id 去重，按 (重要性降序, 时间降序) 排序后返回。

设计原则：
  1. 纯标准库（urllib），零第三方依赖，无 key 开箱即用。
  2. 只取「标题 + 摘要 + 链接 + 时间 + 重要性」，不转载全文。
  3. 所有时间统一按北京时间（+8）格式化。

用法：
  python3 fetch_news_cn.py                  # 打印 JSON 到 stdout
  python3 fetch_news_cn.py --pretty         # 美化打印
  python3 fetch_news_cn.py --window 8       # 时间窗（小时，默认 8）
  python3 fetch_news_cn.py --target 20      # 凑够多少条即停（默认 20）
  python3 fetch_news_cn.py --limit 20       # 卡片展示上限（默认 20）
"""

import json
import sys
import time
import urllib.request
import urllib.parse
from datetime import datetime, timedelta, timezone

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120 Safari/537.36")
TIMEOUT = 15
TZ = timezone(timedelta(hours=8))

BASE = "https://news.10jqka.com.cn/tapp/news/push/stock/"
SOURCE_NAME = "同花顺"


def _get_json(page, retries=2):
    """拉取指定页 JSON，失败返回 None。"""
    url = BASE + "?" + urllib.parse.urlencode({"page": str(page)})
    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(
                url, headers={"User-Agent": UA, "Referer": "https://news.10jqka.com.cn/"}
            )
            with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
                return json.loads(resp.read().decode("utf-8", "ignore"))
        except Exception:
            if attempt < retries:
                time.sleep(0.3 * (attempt + 1))
    return None


def _fmt_time(ts):
    """Unix 时间戳 -> 'MM-DD HH:MM'（北京时间）。"""
    try:
        return datetime.fromtimestamp(int(ts), TZ).strftime("%m-%d %H:%M")
    except (TypeError, ValueError, OSError):
        return ""


def collect(window_hours=8, target=20, max_pages=40, display_limit=20):
    """采集同花顺重要新闻。

    停止条件（先到先停）：已凑够 target 条，或已翻到 window_hours 之前。

    返回 dict：
      ts           采集时间
      source       数据源头说明
      window_hours 时间窗
      target       目标条数
      total        命中（import>0 且落在窗内）总数
      items        已排序、截断到 display_limit 的新闻列表
    """
    cutoff = time.time() - window_hours * 3600
    seen = set()
    collected = []
    reached_window_edge = False

    for page in range(1, max_pages + 1):
        data = _get_json(page)
        if not data:
            break
        lst = (data.get("data") or {}).get("list") or []
        if not lst:
            break

        for it in lst:
            ctime = int(it.get("ctime") or 0)
            if ctime <= 0:
                continue
            # 接口按时间倒序：一旦越过时间窗，后续只会更旧 -> 停止
            if ctime < cutoff:
                reached_window_edge = True
                break
            imp = int(it.get("import") or 0)
            if imp <= 0:
                continue
            nid = it.get("id") or it.get("seq")
            if nid in seen:
                continue
            seen.add(nid)
            collected.append({
                "id": nid,
                "title": (it.get("title") or "").strip(),
                "digest": (it.get("digest") or "").strip(),
                "url": it.get("url") or "",
                "time": _fmt_time(ctime),
                "ts": ctime,
                "importance": imp,
                "tag": (it.get("tag") or "").strip(),
                "source": SOURCE_NAME,
            })

        # 先到先停：翻到时间窗边界，或已凑够 target 条
        if reached_window_edge or len(collected) >= target:
            break
        # 礼貌节流
        time.sleep(0.12)

    # 排序：重要性降序 -> 时间降序
    collected.sort(key=lambda x: (-x["importance"], -x["ts"]))
    items = collected[:display_limit]

    return {
        "ts": time.strftime("%Y-%m-%d %H:%M:%S"),
        "source": f"{SOURCE_NAME} 盘中推送接口 (free, no key)",
        "window_hours": window_hours,
        "target": target,
        "total": len(collected),
        "display_limit": display_limit,
        "items": items,
    }


def main():
    args = sys.argv[1:]
    pretty = "--pretty" in args
    window = 8
    target = 20
    limit = 20
    if "--window" in args:
        window = int(args[args.index("--window") + 1])
    if "--target" in args:
        target = int(args[args.index("--target") + 1])
    if "--limit" in args:
        limit = int(args[args.index("--limit") + 1])

    out = collect(window_hours=window, target=target, display_limit=limit)
    if pretty:
        print(json.dumps(out, ensure_ascii=False, indent=2))
    else:
        print(json.dumps(out, ensure_ascii=False))


if __name__ == "__main__":
    main()
