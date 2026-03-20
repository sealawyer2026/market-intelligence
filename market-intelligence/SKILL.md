---
name: market-intelligence
description: |
  A股/港股/美股市场数据分析技能包（Finnhub Pro 替代方案）。
  等效替代 ClawHub 的 finnhub-pro 技能（无需 API Key）。
  
  使用场景：
  1. 查询股票实时行情（报价/K线/资金流向）
  2. 技术指标分析（MACD/KDJ/RSI/布林带/均线）
  3. 市场新闻/个股公告/新闻情绪
  4. 选股筛选（涨幅榜/放量/行业/概念）
  5. 财务估值（PE/PB/市值/估值评分）
  6. 每日大盘指数监控
  7. 交易分析报告生成
  
  当用户询问"查一下XX股票"、"技术分析XX"、"今日市场"、"选股"、
  "最新消息"、"新闻情绪"、"大盘"等相关问题时激活。
---

# Market Intelligence - 市场情报技能

## 设计模式

本技能采用 Google 提出的 **Pipeline（流水线）+ Tool Wrapper（工具包装器）** 双模式设计：

- **Tool Wrapper**：每个模块（quote/technical/news/screener/finance）独立封装，可单独调用
- **Pipeline**：交易分析按标准化5步流程执行，确保不遗漏关键步骤

## 目录结构

```
scripts/
├── finnhub_api.py        # 统一API入口（路由层）
└── modules/
    ├── quote.py          # 实时行情（腾讯/新浪财经）
    ├── technical.py     # 技术指标（MACD/KDJ/RSI/布林带/均线）
    ├── news.py           # 市场新闻/个股公告/情绪分析
    ├── screener.py       # 选股器（涨幅榜/放量/行业/概念）
    └── finance.py        # 财务数据/估值评分/指数

references/
├── api-reference.md          # 完整API端点手册
└── trading-analysis-workflow.md  # 标准化5步分析流程
```

## 使用方法

### 方法1：命令行调用（开发调试）

```bash
# 实时报价
python scripts/finnhub_api.py quote --symbol 600519

# 批量报价
python scripts/finnhub_api.py batch-quote --symbol "600519,000858,300750"

# 技术指标（MACD）
python scripts/finnhub_api.py technical --symbol 600519 --params '{"indicator":"macd"}'

# 新闻情绪
python scripts/finnhub_api.py sentiment --symbol 600519

# 大盘指数
python scripts/finnhub_api.py indices

# 选股（今日涨幅前10）
python scripts/finnhub_api.py screener --params '{"top_gainers":10}'
```

### 方法2：Python直接import（生产调用）

```python
from scripts.modules.quote import get_quote, search_stocks
from scripts.modules.technical import get_technical_indicators, get_kline
from scripts.modules.news import get_news_sentiment, get_market_news
from scripts.modules.screener import screen_stocks
from scripts.modules.finance import valuation_score, get_index

# 报价
q = get_quote("600519")
print(f"现价: {q['price']} | 涨跌: {q['pct_change']}%")

# MACD
macd = get_technical_indicators("600519", "macd")
print(f"DIF={macd['dif']} DEA={macd['dea']} 信号={macd['signal']}")

# 估值评分
score = valuation_score("600519")
print(f"估值: {score['score']}/100 ({score['label']})")
```

## 标准化分析流程（Pipeline模式）

对于股票分析类请求，**必须严格按以下5步执行**：

### Step 1 - 行情快照
- 获取现价、涨跌幅、成交量

### Step 2 - 技术分析
- 必做：MACD + KDJ + RSI（或调用 `technical` 模块一次获取多指标）
- 判断趋势方向和超买超卖状态

### Step 3 - 基本面估值
- 调用 `valuation_score()` 获取综合估值
- PE/PB/市值数据

### Step 4 - 市场情绪
- 新闻情绪分数
- 大盘指数（上证/创业板）强弱

### Step 5 - 综合输出
- 按以下格式输出结构化报告：

```
## [代码] 分析报告

### 📊 行情快照
现价: XX元 | 涨跌: +X.XX% | 成交量: XX万手

### 📈 技术面
MACD: [金叉/死叉] | KDJ: [超买/超卖/中性] | RSI: [数值]
信号: [买入/持有/观望/卖出]

### 🏢 基本面
估值评分: XX/100 ([低估/合理/高估])
PE: XX | PB: XX

### 💬 情绪面
新闻情绪: [看涨/中性/看跌] (XX分)
大盘: [上证XX点 XX%] 

### 🎯 综合判断
**操作建议**: [买入/持有/观望/止损]
**目标价**: XX元 | **止损价**: XX元 (-7%)
**理由**: [2-3句话核心逻辑]
```

## 股票池管理

可维护观察名单，定期调用筛选：

```python
# 每日涨幅前10
screen_stocks(filters={"top_gainers": 10})

# 热点概念
screen_stocks(filters={"hot_concept": 10})

# 放量股
screen_stocks(filters={"high_volume": 10})
```

## 数据源说明

| 模块 | 数据源 | 依赖 |
|------|--------|------|
| quote | 腾讯财经 + 新浪财经 | 无 |
| technical | 腾讯K线API | 无 |
| news | 东方财富快讯 | 无 |
| screener | 东方财富排行榜 | 无 |
| finance | 东方财富财务API | 无 |

所有接口均为**免费接口**，无需 API Key。

## 迭代计划

- [ ] v1.1: 添加港股支持（00700.HK等）
- [ ] v1.2: 添加美股支持（通过Yahoo Finance）
- [ ] v1.3: 北向资金流向数据
- [ ] v1.4: 财报分析模块（利润表/资产负债表/现金流量表）
- [ ] v1.5: 板块轮动分析（资金在行业间的流向）
