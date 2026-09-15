---
name: 盘前雷达
slug: premarket-radar
version: 0.1.0
displayName: 盘前雷达
category: finance
platforms:
  - WorkBuddy
  - ClawHub
description: "A股盘前「隔夜外盘 + 重要新闻」数据简报，只做数据采集与呈现，不做任何涨跌预测或方向判断。采集隔夜美股指数(标普500/道琼斯/纳斯达克/费城半导体/中概金龙)、恒指与恒生科技、离岸人民币与美元指数、美债10Y、大宗商品(WTI原油/纽约黄金/伦铜)，以及A50期货、VIX；新闻来自同花顺重要新闻流(import>0)，凑够20条或回溯8小时。输出可分享的HTML数据卡。MIT开源、零第三方依赖、无key开箱即用。触发词：盘前雷达、盘前简报、隔夜外盘、盘前数据、外围行情、盘前新闻、今日盘前。"
agent_created: true
metadata:
  author: hectorlee
  license: MIT
  tags: premarket, overnight, market-data, news, A-share, finance, open-source, zero-dependency
  compatibility: workbuddy
---

# 盘前雷达（Premarket Radar）

A 股盘前的**隔夜外盘数据 + 重要新闻**简报。**只做数据采集与呈现，不做任何涨跌预测、方向判断或风险打分**——把隔夜发生了什么、盘前有哪些重要消息，如实摆出来。

## 核心定位

- **面向对象**：A 股投资者，盘前 30 秒看清"隔夜外围怎么走 + 有哪些重要新闻"。
- **输出性质**：**纯数据简报**，不含预测、不含方向结论、不含风险分级。
- **配色约定**：红 = 涨，绿 = 跌（A 股心智）。
- **数据真实**：所有指标来自脚本实时采集的公开接口，标注来源与时间。

## 红线

- **不预测**：只呈现已发生的数据与新闻，不做涨跌判断、不给方向概率、不做风险分级。
- **禁止编造数据**：所有指标必须来自脚本实时采集，标注来源与数值。
- **抓不到就留白**：某指标采集失败时显示 `--`，不用其他来源或估计值填充。
- **必须附免责声明**：每次输出末尾附：
  > 数据仅供研究参考，不构成任何投资建议。市场有风险，投资需谨慎。

## 快速开始

```bash
cd scripts

# 采集：隔夜外盘 + 重要新闻 -> 结构化 JSON（打印）
python3 score_and_report.py --pretty

# 渲染 HTML 数据卡（读报告 + templates/card.html）
python3 render_card.py
# -> output/card_YYYYMMDD.html
```

纯 Python 标准库（urllib / json），**零第三方依赖、无 key 开箱即用**。

## 数据源

| 模块 | 脚本 | 内容 | key |
|---|---|---|---|
| 隔夜外盘行情 | `fetch_market.py` | 美股指数（标普500/道琼斯/纳斯达克/费城半导体/中概金龙）、恒生指数/恒生科技、离岸人民币、美元指数、美债 10Y、WTI 原油、纽约黄金、伦铜、A50 期货、VIX（腾讯 / 新浪 / 东财，免费公开接口） | 否 |
| 重要新闻 | `fetch_news_cn.py` | 同花顺「盘中推送」接口，只保留 `import > 0` 的重要新闻 | 否 |

### 卡片展示的 4 组 / 15 项

| 分组 | 指标 |
|---|---|
| 外围股指 | 标普500、道琼斯、纳斯达克、费城半导体、中概金龙、恒生指数 |
| 汇率 · 美债 | 离岸人民币、美元指数、美债 10Y |
| 大宗商品 | WTI 原油、纽约黄金、伦铜 |
| A股前瞻 | 富时中国 A50 期货、恒生科技指数、VIX 恐慌指数 |

> 费城半导体（SOX）腾讯无对应代码，改用新浪 `gb_$sox`。

## 新闻采集策略

来源：同花顺 `https://news.10jqka.com.cn/tapp/news/push/stock/?page=N`（按时间倒序翻页）。

- **过滤**：只保留 `import > 0` 的「重要」新闻（`import == 0` 视为噪音，剔除）。
- **停止条件（先到先停）**：已凑够 **20 条**，或已翻到 **8 小时** 之前。
  - 夜盘以海外消息为主、国内发布较少，8 小时窗口已足够。
- **排序**：按 重要性降序 → 时间降序，卡片展示前 20 条。

## 输出产物

- `output/card_YYYYMMDD.html` — 可分享的数据卡（4 组指标网格 + 重要新闻列表）

## 目录结构

```
premarket-radar/
├── SKILL.md
├── README.md
├── LICENSE
├── scripts/
│   ├── score_and_report.py      # 编排：汇总行情 + 新闻 -> 结构化报告
│   ├── fetch_market.py          # 隔夜外盘行情采集
│   ├── fetch_news_cn.py         # 同花顺重要新闻采集
│   ├── render_card.py           # 数据卡渲染
│   └── templates/card.html      # 数据卡模板
└── output/card_YYYYMMDD.html    # 生成产物
```
