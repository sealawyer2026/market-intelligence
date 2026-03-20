---
name: market-intelligence
description: |
  A股/港股/美股市场数据分析技能包 v1.2（Finnhub Pro 替代方案）。
  等效替代 ClawHub 的 finnhub-pro 技能（无需 API Key）。

  使用场景：
  1. 查询股票实时行情（A股/港股/美股，自动识别市场）
  2. 技术指标分析（MACD/KDJ/RSI/布林带/均线，支持三市场）
  3. 市场新闻/个股公告/新闻情绪
  4. 选股筛选（涨幅榜/放量/行业/概念）
  5. 财务估值（PE/PB/市值/估值评分）
  6. 每日大盘指数监控（上证/深证/创业板/科创50/沪深300）
  7. 交易分析报告生成

  当用户询问"查一下XX股票"、"技术分析XX"、"今日市场"、"选股"、
  "港股行情"、"美股报价"、"最新消息"、"新闻情绪"、"大盘"等
  相关问题时激活。
---

# Market Intelligence v1.2 - 市场情报技能

## 设计模式

本技能采用 Google 提出的 **Pipeline（流水线）+ Tool Wrapper（工具包装器）** 双模式设计。

## 目录结构

```
scripts/
├── finnhub_api.py        # 统一API入口（路由层）
└── modules/
    ├── quote.py          # 实时行情（A/H/美股，腾讯+Yahoo Finance）
    ├── technical.py     # 技术指标（三市场K线+MACD/KDJ/RSI/布林带）
    ├── news.py           # 市场新闻/个股公告/情绪分析
    ├── screener.py       # 选股器（涨幅榜/放量/行业/概念）
    └── finance.py        # 财务数据/估值评分/指数

references/
├── api-reference.md          # 完整API端点手册
└── trading-analysis-workflow.md  # 标准化5步分析流程
```

## 市场自动识别

`symbol` 参数**自动识别**市场，无需手动标注：

| 示例 | 市场 | 自动识别依据 |
|------|------|-------------|
| `600519` | A股-沪 | 6位数字，6开头 |
| `000858` | A股-深 | 6位数字，0/3开头 |
| `00700` | 港股 | 5位数字，腾讯代码 |
| `AAPL` | 美股 | 全大写字母 |
| `hk.00700` | 港股 | 显式标注 |
| `TSLA.US` | 美股 | 显式标注 |

## 使用方法

### 方法1：命令行调用

```bash
# A股报价
python scripts/finnhub_api.py quote --symbol 600519

# 港股报价（腾讯代码，自动识别）
python scripts/finnhub_api.py quote --symbol 00700

# 美股报价（Yahoo Finance）
python scripts/finnhub_api.py quote --symbol AAPL

# 批量报价（混合市场）
python scripts/finnhub_api.py batch-quote --symbol "600519,00700,AAPL"

# 全量技术指标（A/H/美股通用）
python scripts/finnhub_api.py technical --symbol AAPL --params '{"indicator":"all"}'

# 三市场状态
python scripts/finnhub_api.py market-status

# 跨市场搜索
python scripts/finnhub_api.py search --symbol "腾讯"
```

### 方法2：Python直接import

```python
from scripts.modules.quote import get_quote, search_stocks, detect_market
from scripts.modules.technical import get_technical_indicators, get_kline
from scripts.modules.news import get_news_sentiment, get_market_news
from scripts.modules.screener import screen_stocks
from scripts.modules.finance import valuation_score, get_index

# 自动识别市场
q = get_quote("00700")   # 港股腾讯
q = get_quote("AAPL")    # 美股苹果
q = get_quote("600519")  # A股茅台

# 全量指标（1次调用获取MACD+KDJ+RSI+布林带+均线）
indicators = get_technical_indicators("AAPL", "all")
print(indicators["macd"])   # MACD
print(indicators["kdj"])    # KDJ
print(indicators["rsi"])    # RSI
print(indicators["boll"])   # 布林带
print(indicators["ma"])     # 均线排列
```

## 标准化分析流程（Pipeline模式）

对于股票分析类请求，**必须严格按以下5步执行**：

### Step 1 - 行情快照
- 自动识别市场获取现价、涨跌幅、成交量

### Step 2 - 技术分析
- 必做：`indicator="all"` 一次获取 MACD + KDJ + RSI + 布林带 + 均线
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
## [代码] 分析报告 ([市场])

### 📊 行情快照
现价: XX元 | 涨跌: +X.XX% | 成交量: XX万手

### 📈 技术面
MACD: [金叉/死叉] | KDJ: [超买/超卖/中性] | RSI: [数值]
均线: [多头/空头排列]
信号: [买入/持有/观望/卖出]

### 🏢 基本面
估值评分: XX/100 ([低估/合理/高估])
PE: XX | PB: XX

### 💬 情绪面
新闻情绪: [看涨/中性/看跌] (XX分)

### 🎯 综合判断
**操作建议**: [买入/持有/观望/止损]
**目标价**: XX元 | **止损价**: XX元 (-7%)
**理由**: [2-3句话核心逻辑]
```

## 数据源说明

| 市场 | 行情 | K线 | 数据源 |
|------|------|-----|--------|
| A股 | 腾讯+新浪 | 腾讯 | 免费，无Key |
| 港股 | 腾讯 | 腾讯 | 免费，无Key |
| 美股 | Yahoo Finance | Yahoo Finance | 免费，无Key |

## 版本历史

| 版本 | 日期 | 更新内容 |
|------|------|---------|
| **v1.0** | 2026-03-20 | 首发：A股13个API端点 |
| **v1.2** | 2026-03-20 | 新增港股/美股支持；MACD+KDJ+RSI一键获取 |

## 迭代计划

- [x] v1.0: A股13个API端点
- [x] v1.2: 港股+美股支持
- [ ] v1.3: 北向资金流向数据
- [ ] v1.4: 财报分析模块（利润表/资产负债表/现金流量表）
- [ ] v1.5: 板块轮动分析（资金在行业间的流向）
