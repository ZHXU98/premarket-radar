#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
score_and_report.py — 盘前数据汇总（「盘前雷达」编排层）

汇总两个采集脚本的数据，生成「隔夜外盘 + 盘前数据 + 重要新闻」结构化报告。
本报告只做**数据采集与呈现**，不做任何涨跌预测、方向判断或风险打分——
用户明确认为提前预测无意义。

输入：
  fetch_market.collect()   外围行情（美股/汇率/美债/商品/A50）
  fetch_news_cn.collect()  同花顺重要新闻（import>0，≥12h 窗）

输出：
  {
    ts, date, weekday,
    groups: [ {title, rows:[{name,value,delta,cls,sub}]}, ... ],
    news:   [ {title, time, url, source, importance, tag}, ... ]
  }

配色（A股习惯）：涨 = 红(rk-up)，跌 = 绿(rk-dn)，平/缺 = 灰(rk-nt)。

用法：
  python3 score_and_report.py            # 打印报告 JSON
  python3 score_and_report.py --pretty   # 美化打印
"""

import json
import re
import sys
import time
from datetime import datetime, timedelta, timezone

import fetch_market
import fetch_news_cn

TZ = timezone(timedelta(hours=8))
WEEKDAY_MAP = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]

# 各行情项的展示精度（默认 2 位，A50/恒生科技等整数指数用 0）
PRECISION = {
    "hf_CHA50CFD": 0,
    "rt_hkHSTECH": 0,
    "hkHSI": 0,
    "fx_susdcnh": 4,
}

# 数据分组定义：(组标题, [(market_key, 是否美债收益率), ...])
GROUPS = [
    ("外围股指", [
        ("usINX", False), ("usDJI", False), ("usIXIC", False),
        ("gb_$sox", False), ("usHXC", False), ("hkHSI", False),
    ]),
    ("汇率 · 美债", [
        ("fx_susdcnh", False), ("DINIW", False), ("ust_yield", True),
    ]),
    ("大宗商品", [
        ("hf_CL", False), ("hf_GC", False), ("hf_HG", False),
    ]),
    ("A股前瞻", [
        ("hf_CHA50CFD", False), ("rt_hkHSTECH", False), ("hf_VX", False),
    ]),
]


def _norm_time(s):
    """把各源五花八门的时间串统一为 'MM-DD HH:MM'（有日期+时间时）或短形式。"""
    s = (s or "").strip()
    if not s:
        return ""
    m = re.search(r"(\d{4})[-/](\d{2})[-/](\d{2})[ T]+(\d{2}:\d{2})", s)
    if m:
        return f"{m.group(2)}-{m.group(3)} {m.group(4)}"
    m = re.search(r"(\d{4})[-/](\d{2})[-/](\d{2})", s)
    if m:
        return f"{m.group(2)}-{m.group(3)}"
    m = re.search(r"(\d{2}:\d{2})", s)
    if m:
        return m.group(1)
    return s


def _fmt_row(market, key, is_yield=False):
    """把一个行情项转成卡片行（name/value/delta/cls/sub）。"""
    if is_yield:
        uy = market.get("ust_yield") or {}
        price = uy.get("us10y")
        change = uy.get("change")
        name = "美债10Y"
        if price is None:
            return {"name": name, "value": "--", "delta": "", "cls": "rk-nt",
                    "sub": _norm_time(uy.get("date", ""))}
        cls = "rk-up" if (change or 0) > 0 else "rk-dn" if (change or 0) < 0 else "rk-nt"
        return {
            "name": name,
            "value": f"{price:.2f}%",
            "delta": f"{change:+.2f}" if change is not None else "",
            "cls": cls,
            "sub": _norm_time(uy.get("date", "")),
        }

    item = market.get(key) or {}
    name = item.get("name") or key
    price = item.get("price")
    pct = item.get("change_pct")
    if price is None:
        return {"name": name, "value": "--", "delta": "", "cls": "rk-nt",
                "sub": _norm_time(item.get("time", ""))}
    prec = PRECISION.get(key, 2)
    cls = "rk-up" if (pct or 0) > 0 else "rk-dn" if (pct or 0) < 0 else "rk-nt"
    return {
        "name": name,
        "value": f"{price:,.{prec}f}",
        "delta": f"{pct:+.2f}%" if pct is not None else "",
        "cls": cls,
        "sub": _norm_time(item.get("time", "")),
    }


def _build_groups(market):
    groups = []
    for title, keys in GROUPS:
        rows = []
        for key, is_yield in keys:
            rows.append(_fmt_row(market, key, is_yield))
        groups.append({"title": title, "rows": rows})
    return groups


def collect():
    """拉数据，返回完整报告 dict。"""
    market = fetch_market.collect()
    news_data = fetch_news_cn.collect()
    now = datetime.now(TZ)
    return {
        "ts": time.strftime("%Y-%m-%d %H:%M:%S"),
        "date": now.strftime("%Y-%m-%d"),
        "weekday": WEEKDAY_MAP[now.weekday()],
        "groups": _build_groups(market),
        "news": news_data.get("items") or [],
        "news_meta": {
            "source": news_data.get("source", ""),
            "window_hours": news_data.get("window_hours"),
            "total": news_data.get("total", 0),
        },
    }


def main():
    pretty = "--pretty" in sys.argv
    report = collect()
    if pretty:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
