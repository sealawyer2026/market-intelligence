# API 参考手册

## 统一 API 入口

```bash
python scripts/finnhub_api.py <endpoint> --symbol <代码> [--params '{}']
```

## 全部 API 端点

| 端点 | 功能 | 参数 |
|------|------|------|
| `quote` | 实时报价 | --symbol 600519 |
| `batch-quote` | 批量报价 | --symbol "600519,000001" |
| `search` | 股票搜索 | --symbol "贵州茅台" |
| `candles` | K线数据 | --symbol 600519 |
| `technical` | 技术指标 | --symbol 600519 --params '{"indicator":"macd"}' |
| `news` | 市场新闻 | --symbol CN (默认) |
| `company-news` | 个股新闻 | --symbol 600519 |
| `sentiment` | 新闻情绪 | --symbol 600519 |
| `indices` | 主要指数 | 无 |
| `market-status` | 市场状态 | 无 |
| `screener` | 选股器 | --params '{"top_gainers":10}' |
| `recommendation` | 研报评级 | --symbol 600519 |
| `price-target` | 目标区间 | --symbol 600519 |

## 技术指标类型

- `macd` — MACD (DIF/DEA/MACD柱)
- `kdj` — KDJ 随机指标 (K/D/J)
- `rsi` — RSI 相对强弱 (周期14)
- `boll` — 布林带 (上轨/中轨/下轨)
- `ma` — 均线系统 (MA5/10/20/60)

## 选股过滤器

```json
{"top_gainers": 10}   // 今日涨幅前10
{"top_losers": 10}    // 今日跌幅前10
{"high_volume": 10}   // 放量前10
{"by_industry": "芯片"} // 行业板块
{"hot_concept": 20}   // 热点概念
```
