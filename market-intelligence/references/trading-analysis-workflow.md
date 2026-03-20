# 交易分析工作流 (Pipeline Pattern)

## 标准化分析流程（5步）

每次分析股票，必须按顺序执行以下步骤，**不得跳过**。

### Step 1 — 行情快照 (Quote Snapshot)

```bash
python scripts/finnhub_api.py quote --symbol 600519
```

关注字段：
- `price` — 现价
- `pct_change` — 涨跌幅%
- `volume_hands` — 成交量（手）
- `bid1/ask1` — 买卖盘

### Step 2 — 技术面分析 (Technical Analysis)

```bash
# MACD + KDJ + RSI 组合
python scripts/finnhub_api.py technical --symbol 600519 --params '{"indicator":"macd"}'
python scripts/finnhub_api.py technical --symbol 600519 --params '{"indicator":"kdj"}'
python scripts/finnhub_api.py technical --symbol 600519 --params '{"indicator":"rsi"}'
python scripts/finnhub_api.py technical --symbol 600519 --params '{"indicator":"ma"}'
```

关注字段：
- MACD: `trend`(金叉/死叉), `signal`(买入/卖出)
- KDJ: `k/d/j`, `signal`(超买/超卖)
- RSI: `rsi`(>70超买/<30超卖)
- MA: `arrangement`(多头/空头排列)

### Step 3 — 基本面/估值 (Valuation)

```bash
python scripts/finnhub_api.py screener --symbol 600519
# 或直接调用
python -c "from scripts.modules.finance import valuation_score; import json; print(json.dumps(valuation_score('600519'), ensure_ascii=False))"
```

关注字段：
- `score` — 估值评分(0-100)
- `label` — 低估/合理/高估
- `pe_ttm`, `pb`

### Step 4 — 市场情绪/资金 (Sentiment)

```bash
python scripts/finnhub_api.py sentiment --symbol 600519
python scripts/finnhub_api.py indices  # 大盘指数
```

关注字段：
- `sentiment_score` — 情绪分(-1~1)
- `buzz` — 热度
- `positive/negative_signals` — 多空信号数

### Step 5 — 综合判断 (Synthesis)

综合以上数据，输出结构化判断：

```
## [股票代码] 分析报告

### 📊 行情快照
- 现价: XX元 | 涨跌: +X.XX% | 成交量: XX万手

### 📈 技术面
- MACD: [金叉/死叉] | KDJ: [状态] | RSI: [数值]
- 信号: [买入/持有/观望/卖出]

### 🏢 基本面
- 估值评分: XX/100 ([低估/合理/高估])
- PE: XX | PB: XX

### 💬 情绪面
- 新闻情绪: [看涨/中性/看跌] (XX分)
- 热度: XX条信号

### 🎯 综合判断
**操作建议**: [买入/持有/观望/止损]
**目标价**: XX元 | **止损价**: XX元 (-7%)
**理由**: [2-3句话核心逻辑]
```

## 止损规则（铁律）

- 单票止损: -7% 无条件止损
- 每日最大亏损: -3% 当日停止交易
- 仓位: 单票不超过总资金 30%
