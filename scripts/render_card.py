#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
render_card.py — 盘前雷达卡片渲染（输出层）

读模板 + score_and_report 的报告，替换占位符，生成当天「盘前雷达」卡片 HTML。
只做「填值 + 替换占位符」，版式在 templates/card.html 里。

用法：
  python3 render_card.py                  # 生成到 output/card_YYYYMMDD.html
  python3 render_card.py /path/out.html   # 指定输出路径
"""

import json
import os
import re
import sys

import score_and_report

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATE = os.path.join(SCRIPT_DIR, "templates", "card.html")
DEFAULT_OUT = os.path.join(SCRIPT_DIR, "..", "output")


def render_groups(groups):
    """生成数据分组 HTML。"""
    parts = []
    for g in groups:
        parts.append(f'<div class="sec-title">{g["title"]}</div>')
        parts.append('<div class="grid">')
        for r in g["rows"]:
            parts.append(
                '<div class="m">'
                f'<div class="m-name">{r["name"]}</div>'
                f'<div class="m-val {r["cls"]}">{r["value"]}'
                f'<span class="m-delta">{r["delta"]}</span></div>'
                f'<div class="m-sub">{r["sub"]}</div>'
                '</div>'
            )
        parts.append('</div>')
    return "\n".join(parts)


def render_news(news):
    """生成新闻列表 HTML。"""
    items = []
    for n in news:
        title = n.get("title", "")
        if not title:
            continue
        tag = n.get("tag") or ""
        t = n.get("time", "")
        url = n.get("url", "")
        tag_html = f'<span class="n-tag">{tag}</span>' if tag else ""
        time_html = f'<span class="n-time">{t}</span>' if t else ""
        title_html = (f'<a class="n-title" href="{url}" target="_blank" '
                     f'rel="noopener">{title}</a>') if url else \
                    f'<span class="n-title">{title}</span>'
        items.append(
            f'<div class="n">{tag_html}{time_html}{title_html}</div>'
        )
    if not items:
        return '<div class="n-empty">时间窗内暂无 import&gt;0 的重要新闻</div>'
    return "\n".join(items)


def render(report):
    """读模板 + 填值，返回最终 HTML。"""
    with open(TEMPLATE, encoding="utf-8") as f:
        html = f.read()

    mapping = {
        "{{date}}": report["date"],
        "{{weekday}}": report["weekday"],
        "{{ts}}": report["ts"],
        "{{groups}}": render_groups(report["groups"]),
        "{{news}}": render_news(report["news"]),
        "{{news_total}}": str(len(report.get("news") or [])),
        "{{news_window}}": str(report.get("news_meta", {}).get("window_hours", 8)),
        "{{news_source}}": report.get("news_meta", {}).get("source", ""),
    }
    for k, v in mapping.items():
        html = html.replace(k, v)
    return html


def main():
    out_path = sys.argv[1] if len(sys.argv) > 1 else None
    report = score_and_report.collect()
    html = render(report)

    if out_path is None:
        date = report["date"].replace("-", "")
        os.makedirs(DEFAULT_OUT, exist_ok=True)
        out_path = os.path.join(DEFAULT_OUT, f"card_{date}.html")
    out_path = os.path.abspath(out_path)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)

    leftover = re.findall(r"\{\{[^}]+\}\}", html)
    print(f"已生成卡片: {out_path}")
    print(f"日期: {report['date']} {report['weekday']}")
    print(f"指标分组: {len(report['groups'])} 组 | 重要新闻: {report['news_meta']['total']} 条")
    if leftover:
        print(f"[警告] 残留未替换占位符 {len(leftover)} 个: {leftover[:5]}")
    else:
        print("[OK] 全部占位符已替换，无残留")


if __name__ == "__main__":
    main()
