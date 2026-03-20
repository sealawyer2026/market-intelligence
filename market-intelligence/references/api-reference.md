# API 参考手册 v1.2

## 全部 API 端点

| 端点 | 功能 | 示例 |
|------|------|------|
| `quote` | 实时报价 | `--symbol 600519` / `--symbol 00700` / `--symbol AAPL` |
| `batch-quote` | 批量报价 | `--symbol "600519,00700,AAPL"` |
| `search` | 跨市场搜索 | `--symbol "腾讯"` / `--symbol "Apple"` |
| `candles` | K线数据 | `--symbol AAPL` |
| `technical` | 技术指标 | `--symbol 600519 --params '{"indicator":"all"}'` |
| `news` | 市场新闻 | 默认最新20条 |
| `company-news` | 个股公告 | `--symbol 600519` |
| `sentiment` | 新闻情绪 | `--symbol 600519` |
| `indices` | 主要指数 | 上证/深证/创业板/科创50/沪深300 |
| `market-status` | **三市场状态** | 返回A股/港股/美股开盘状态 |
| `screener` | 选股器 | `--params '{"top_gainers":10}'` |
| `recommendation` | 研报评级 | `--symbol 600519` |
| `price-target` | 目标区间 | `--symbol AAPL` |

## 市场自动识别

```
A股:  600519 / sh600519 / 000858 / bj000001
港股: 00700 / 00700.HK / hk00700 / 5位数字腾讯代码
美股: AAPL / TSLA.US / US:TSLA / 全大写字母符号
```

## 技术指标

| 指标 | 说明 | 参数 |
|------|------|------|
| `macd` | DIF/DEA/MACD柱 | `{"n":20}` |
| `kdj` | K/D/J值 | `{"period":9}` |
| `rsi` | RSI | `{"period":14}` |
| `boll` | 布林带 | `{"n":20}` |
| `ma` | 均线 | `{"periods":[5,10,20,60]}` |
| `all` | **全量指标** | 一次获取全部 |

## 选股过滤器

```json
{"top_gainers": 10}   // 今日涨幅前10
{"top_losers": 10}     // 今日跌幅前10
{"high_volume": 10}    // 放量前10
{"by_industry": "芯片"} // 行业板块
{"hot_concept": 20}    // 热点概念
```

## 批量混合市场报价

```bash
python scripts/finnhub_api.py batch-quote --symbol "600519,00700,AAPL,TSLA"
```

## 新增功能（v1.2 vs v1.0）

- ✅ 港股实时报价（腾讯行情）
- ✅ 美股实时报价（Yahoo Finance）
- ✅ 三市场K线（腾讯/Yahoo）
- ✅ 三市场技术指标
- ✅ 三市场状态监控
- ✅ 跨市场股票搜索
- ✅ 批量混合市场报价
