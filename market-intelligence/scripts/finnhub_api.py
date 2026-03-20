#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
market-intelligence: Unified Finnhub-like API
统一封装所有市场数据接口，模拟 Finnhub 功能
"""

import sys
import json
import argparse
from typing import Optional, List, Dict, Any

# 内部模块
from modules.quote import get_quote, get_quotes_batch, search_stocks
from modules.technical import get_technical_indicators, get_kline
from modules.news import get_market_news, get_stock_news, get_news_sentiment
from modules.screener import screen_stocks
from modules.finance import get_finance, get_index


def format_response(success: bool, data: Any = None, error: str = None):
    """统一响应格式"""
    return {
        "success": success,
        "data": data,
        "error": error
    }


# ============ Finnhub 核心 API 映射 ============

def api_quote(symbol: str) -> Dict[str, Any]:
    """
    Finnhub-equivalent: /quote
    返回股票实时报价（最新价、开盘、收盘、最高、最低、成交量）
    """
    try:
        result = get_quote(symbol)
        return format_response(True, result)
    except Exception as e:
        return format_response(False, error=str(e))


def api_company_profile(symbol: str) -> Dict[str, Any]:
    """
    Finnhub-equivalent: /stock/profile
    返回公司基本信息（名称、行业、市值、PE等）
    """
    try:
        from modules.quote import get_profile
        result = get_profile(symbol)
        return format_response(True, result)
    except Exception as e:
        return format_response(False, error=str(e))


def api_candles(symbol: str, resolution: str = "D", from_ts: int = None, to_ts: int = None) -> Dict[str, Any]:
    """
    Finnhub-equivalent: /stock/candle
    返回K线数据（支持 D/W/M/5/15/30/60 分钟）
    """
    try:
        result = get_kline(symbol, period=resolution)
        return format_response(True, result)
    except Exception as e:
        return format_response(False, error=str(e))


def api_technical_indicator(symbol: str, indicator: str = "macd", params: Dict = None) -> Dict[str, Any]:
    """
    Finnhub-equivalent: /scan/technical-indicator
    返回技术指标（MACD/KDJ/RSI/布林带）
    """
    try:
        result = get_technical_indicators(symbol, indicator_type=indicator, params=params or {})
        return format_response(True, result)
    except Exception as e:
        return format_response(False, error=str(e))


def api_news(category: str = "general") -> Dict[str, Any]:
    """
    Finnhub-equivalent: /news
    返回市场新闻（按类别：general/forex/crypto/merger）
    """
    try:
        result = get_market_news(category)
        return format_response(True, result)
    except Exception as e:
        return format_response(False, error=str(e))


def api_company_news(symbol: str, from_date: str = None, to_date: str = None) -> Dict[str, Any]:
    """
    Finnhub-equivalent: /company-news
    返回个股新闻
    """
    try:
        result = get_stock_news(symbol, from_date=from_date, to_date=to_date)
        return format_response(True, result)
    except Exception as e:
        return format_response(False, error=str(e))


def api_sentiment(symbol: str) -> Dict[str, Any]:
    """
    Finnhub-equivalent: /news-sentiment
    返回新闻情绪指标（buzz/positive/negative/sectorAvgBullish）
    """
    try:
        result = get_news_sentiment(symbol)
        return format_response(True, result)
    except Exception as e:
        return format_response(False, error=str(e))


def api_recommendation(symbol: str) -> Dict[str, Any]:
    """
    Finnhub-equivalent: /stock/recommendation
    返回分析师推荐（买入/持有/卖出）
    """
    try:
        from modules.finance import get_recommendation
        result = get_recommendation(symbol)
        return format_response(True, result)
    except Exception as e:
        return format_response(False, error=str(e))


def api_price_target(symbol: str) -> Dict[str, Any]:
    """
    Finnhub-equivalent: /stock/price-target
    返回股价目标区间
    """
    try:
        from modules.finance import get_price_target
        result = get_price_target(symbol)
        return format_response(True, result)
    except Exception as e:
        return format_response(False, error=str(e))


def api_screener(market: str = "cn", filters: Dict = None) -> Dict[str, Any]:
    """
    Finnhub-equivalent: /stock/symbol
    选股器：按行业/市值/PE等条件筛选
    """
    try:
        result = screen_stocks(market=market, filters=filters or {})
        return format_response(True, result)
    except Exception as e:
        return format_response(False, error=str(e))


def api_market_status(symbol: str = None) -> Dict[str, Any]:
    """
    Finnhub-equivalent: /market/status
    返回市场状态（开盘/收盘/盘前/盘后）
    """
    try:
        from datetime import datetime
        now = datetime.now()
        hour = now.hour
        weekday = now.weekday()

        # A股: 9:30-15:00 UTC+8
        if weekday >= 5:
            status = "closed"
        elif 9 <= hour < 11 or 13 <= hour < 15:
            status = "open"
        elif 9 <= hour < 9.3 or 13 <= hour < 13.3:
            status = "pre_market"
        elif 15 <= hour < 18:
            status = "after_hours"
        else:
            status = "closed"

        result = {
            "status": status,
            "session": "A-share",
            "timezone": "Asia/Shanghai",
            "timestamp": now.isoformat()
        }
        return format_response(True, result)
    except Exception as e:
        return format_response(False, error=str(e))


def api_major_indices(symbol: str = None) -> Dict[str, Any]:
    """
    Finnhub-equivalent: /market/index
    返回主要指数（上证/深证/创业板/科创50/沪深300）
    """
    try:
        indices = ["000001", "399001", "399006", "000688", "000300"]
        from modules.finance import get_index
        result = get_index()
        return format_response(True, result)
    except Exception as e:
        return format_response(False, error=str(e))


# ============ 路由入口 ============

API_MAP = {
    "quote": api_quote,
    "profile": api_company_profile,
    "candles": api_candles,
    "technical": api_technical_indicator,
    "news": api_news,
    "company-news": api_company_news,
    "sentiment": api_sentiment,
    "recommendation": api_recommendation,
    "price-target": api_price_target,
    "screener": api_screener,
    "market-status": api_market_status,
    "indices": api_major_indices,
    "batch-quote": lambda symbols: format_response(True, get_quotes_batch(symbols)),
    "search": lambda query: format_response(True, search_stocks(query)),
}


def main():
    parser = argparse.ArgumentParser(description="Market Intelligence - Finnhub-like API")
    parser.add_argument("endpoint", help="API endpoint (e.g. quote, news, technical)")
    parser.add_argument("--symbol", "-s", help="Stock symbol/code")
    parser.add_argument("--params", "-p", help="JSON params")
    parser.add_argument("--output", "-o", help="Output file (default: stdout)")

    args = parser.parse_args()

    endpoint_fn = API_MAP.get(args.endpoint)
    if not endpoint_fn:
        print(json.dumps(format_response(False, error=f"Unknown endpoint: {args.endpoint}"), ensure_ascii=False, indent=2))
        sys.exit(1)

    # 解析额外参数
    extra_params = {}
    if args.params:
        try:
            extra_params = json.loads(args.params)
        except:
            pass

    # 调用对应API
    if args.endpoint in ("batch-quote", "search"):
        result = endpoint_fn(args.symbol or "")
    else:
        result = endpoint_fn(args.symbol or "", **(extra_params))

    output = json.dumps(result, ensure_ascii=False, indent=2)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(output)
    else:
        print(output)


if __name__ == "__main__":
    main()
