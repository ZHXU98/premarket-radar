# 盘前雷达 · Premarket Radar

> A 股盘前「隔夜外盘 + 重要新闻」数据简报，30 秒看清隔夜发生了什么。**不预测，只呈现。**

<p align="center">
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue" alt="MIT License"></a>
  <a href="#特性"><img src="https://img.shields.io/badge/deps-zero%20dependency-success" alt="零第三方依赖"></a>
  <a href="#快速开始"><img src="https://img.shields.io/badge/key-none%20required-brightgreen" alt="无需 API Key"></a>
  <img src="https://img.shields.io/badge/python-3.8%2B-3776AB?logo=python&logoColor=white" alt="Python 3.8+">
</p>

一个纯 Python 标准库、**零第三方依赖、无 key 开箱即用**的盘前数据工具。采集隔夜外围行情与重要新闻，生成一张可分享的 HTML 数据卡。

> **开源免费**：MIT 协议，可自由使用、修改、商用。代码纯标准库、无 key、开箱即用，装上就能跑。

## 为什么做这个

提前预测涨跌没有意义。A 股开盘前真正需要的是**事实**：隔夜美股怎么走的、美元和人民币在什么位置、美债和油价怎么动、今早有哪些重要消息。盘前雷达把这些**如实采集、结构化呈现**，不做任何方向判断或风险打分——结论留给你自己下。

## 特性

- ✅ **零依赖**：纯标准库（urllib / json），`python3` 直接跑，无 `pip install`
- ✅ **无 key**：所有数据源免鉴权，开箱即用
- ✅ **不预测**：只呈现已发生的数据与新闻，无方向判断、无风险分级
- ✅ **隔夜外盘**：美股指（标普/道指/纳指/费半/中概金龙）、汇率、美债、商品
- ✅ **重要新闻**：同花顺重要新闻流（`import > 0`），凑够 20 条或回溯 8 小时
- ✅ **可分享数据卡**：HTML 卡片，指标网格 + 新闻列表

## 快速开始

```bash
cd scripts

# 一键：采集隔夜外盘 + 重要新闻 -> 结构化 JSON
python3 score_and_report.py --pretty

# 渲染 HTML 数据卡
python3 render_card.py
```

输出产物在 `output/` 目录：
- `card_YYYYMMDD.html` — 可分享数据卡

## 数据源

| 模块 | 内容 | 数据源 |
|---|---|---|
| 隔夜外盘行情 | 标普500、道琼斯、纳斯达克、费城半导体、中概金龙、恒生指数、恒生科技、离岸人民币、美元指数、美债 10Y、WTI 原油、纽约黄金、伦铜、A50 期货、VIX | 腾讯 / 新浪 / 东财（免费公开接口） |
| 重要新闻 | 同花顺重要新闻流，只保留 `import > 0` | 同花顺 |

### 卡片展示的 4 组 / 15 项

| 分组 | 指标 |
|---|---|
| 外围股指 | 标普500、道琼斯、纳斯达克、费城半导体、中概金龙、恒生指数 |
| 汇率 · 美债 | 离岸人民币、美元指数、美债 10Y |
| 大宗商品 | WTI 原油、纽约黄金、伦铜 |
| A股前瞻 | 富时中国 A50 期货、恒生科技指数、VIX 恐慌指数 |

## 新闻采集策略

来源：同花顺盘中推送接口（按时间倒序翻页）。

- **过滤**：只保留 `import > 0` 的「重要」新闻。
- **停止条件（先到先停）**：已凑够 **20 条**，或已翻到 **8 小时** 之前。
- **排序**：重要性降序 → 时间降序，展示前 20 条。

## 目录结构

```
premarket-radar/
├── SKILL.md                    # WorkBuddy / ClawHub skill 元数据
├── README.md
├── LICENSE
├── scripts/
│   ├── score_and_report.py     # 编排：汇总行情 + 新闻 -> 结构化报告
│   ├── fetch_market.py         # 隔夜外盘行情采集
│   ├── fetch_news_cn.py        # 同花顺重要新闻采集
│   ├── render_card.py          # 数据卡渲染
│   └── templates/card.html     # 数据卡模板
└── output/card_YYYYMMDD.html   # 生成产物
```

## 免责声明

本项目输出为公开市场数据与新闻的整理，仅供参考，**不构成投资建议**。市场有风险，投资需谨慎。

## License

[MIT](./LICENSE) © 2026 hectorlee
