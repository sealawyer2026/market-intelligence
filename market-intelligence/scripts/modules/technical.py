# -*- coding: utf-8 -*-
"""
Technical Module - 技术指标模块 v1.2
支持: A股 / 港股 / 美股 K线及指标计算
Tool Wrapper Pattern: 封装MACD/KDJ/RSI/布林带/均线计算
"""

import urllib.request
import json
import re
import statistics
from typing import Dict, Any, List, Optional


def fetch(url: str, encoding: str = "utf-8") -> Optional[str]:
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer": "http://finance.sina.com.cn"
        })
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.read().decode(encoding, errors="replace")
    except Exception:
        return None


def detect_market(symbol: str) -> str:
    """检测市场"""
    s = symbol.strip().upper()
    if ".HK" in s or s.startswith("HK") or len(s) == 5 and s.isdigit():
        return "hk"
    if ".US" in s or ":US" in s:
        return "us"
    if s.startswith(("SH", "SZ", "BJ")):
        return "cn"
    if len(s) == 6 and s.isdigit():
        if s.startswith(("4", "8")):
            return "cn_bj"
        return "cn"
    # 美股代码
    us_symbols = ("AAPL", "TSLA", "NVDA", "MSFT", "GOOGL", "AMZN", "META",
                  "NFLX", "AMD", "INTC", "BABA", "JD", "PDD", "NIO",
                  "GME", "AMC", "COIN", "PLTR", "SNOW", "CRWD")
    if s in us_symbols or re.match(r'^[A-Z]{1,5}$', s):
        return "us"
    return "cn"


def get_kline(symbol: str, period: str = "D", count: int = 120) -> Dict[str, Any]:
    """
    获取K线数据
    period: D=日K, W=周K, M=月K, 5/15/30/60=分钟K
    支持: A股(腾讯) / 港股(腾讯) / 美股(Yahoo)
    """
    market = detect_market(symbol)

    if market == "us":
        return _get_kline_us(symbol, period, count)
    elif market == "hk":
        return _get_kline_hk(symbol, period, count)
    else:
        return _get_kline_cn(symbol, period, count)


def _get_kline_cn(symbol: str, period: str = "D", count: int = 120) -> Dict[str, Any]:
    """A股/沪深K线 - 腾讯"""
    s = symbol.strip().upper()
    if s.startswith(("SH", "SZ")):
        code = s[:6]
        market = 1 if s.startswith("SH") else 0
    else:
        # 从数字推断
        num = re.search(r'(\d+)', s)
        code = num.group(1)[:6] if num else s[:6]
        market = 1 if code.startswith("6") else 0

    period_map = {"D": "day", "W": "week", "M": "month",
                  "5": "5min", "15": "15min", "30": "30min", "60": "60min"}
    p = period_map.get(period, "day")

    url = (f"http://web.ifzq.gtimg.cn/appstock/app/fqkline/get"
           f"?_var=kline_{p}qfq&param={code},{p},,,,{count},qfq")
    content = fetch(url)
    if not content:
        return {"symbol": symbol, "status": "error", "error": "K线获取失败"}

    try:
        json_str = re.sub(r'^[^=]+=', '', content.strip())
        data = json.loads(json_str)
        qt_key = list(data.get("data", {}).keys())[0]
        qt_data = data["data"][qt_key]
        k_data = qt_data.get("qfq" if p != "day" else "day", qt_data.get("day", []))

        candles = []
        for item in k_data[-count:]:
            if len(item) >= 6:
                candles.append({
                    "time": item[0],
                    "open": float(item[1]),
                    "close": float(item[2]),
                    "high": float(item[3]),
                    "low": float(item[4]),
                    "volume": float(item[5]) if len(item) > 5 else 0
                })
        return {"symbol": symbol, "market": "cn", "period": period,
                "count": len(candles), "candles": candles, "status": "ok"}
    except Exception as e:
        return {"symbol": symbol, "status": "error", "error": str(e)}


def _get_kline_hk(symbol: str, period: str = "D", count: int = 120) -> Dict[str, Any]:
    """港股K线 - 腾讯"""
    num = re.search(r'(\d+)', symbol)
    code = num.group(1).zfill(5) if num else symbol.strip()[-5:]
    p_map = {"D": "day", "W": "week", "M": "month"}
    p = p_map.get(period, "day")

    url = (f"http://web.ifzq.gtimg.cn/appstock/app/fqkline/get"
           f"?_var=kline_{p}&param=hk{code},{p},,,,{count}")
    content = fetch(url)
    if not content:
        return {"symbol": symbol, "status": "error", "error": "港股K线获取失败"}

    try:
        json_str = re.sub(r'^[^=]+=', '', content.strip())
        data = json.loads(json_str)
        qt_key = list(data.get("data", {}).keys())[0]
        qt_data = data["data"][qt_key]
        k_data = qt_data.get("day", qt_data.get(p, []))

        candles = []
        for item in k_data[-count:]:
            if len(item) >= 6:
                candles.append({
                    "time": item[0],
                    "open": float(item[1]),
                    "close": float(item[2]),
                    "high": float(item[3]),
                    "low": float(item[4]),
                    "volume": float(item[5]) if len(item) > 5 else 0
                })
        return {"symbol": symbol, "market": "hk", "period": period,
                "count": len(candles), "candles": candles, "status": "ok"}
    except Exception as e:
        return {"symbol": symbol, "status": "error", "error": str(e)}


def _get_kline_us(symbol: str, period: str = "D", count: int = 120) -> Dict[str, Any]:
    """美股K线 - Yahoo Finance"""
    s = symbol.strip().upper().replace(".US", "").replace("US:", "")

    # interval映射
    interval_map = {"D": "1d", "W": "1wk", "M": "1mo",
                     "5": "5m", "15": "15m", "30": "30m", "60": "1h"}
    interval = interval_map.get(period, "1d")

    # range: 根据count估算
    range_map = {"1d": "1d", "1wk": "1mo", "1mo": "3mo",
                 "5m": "5d", "15m": "5d", "30m": "5d", "1h": "1mo"}
    r = range_map.get(period, "3mo")

    url = (f"https://query1.finance.yahoo.com/v8/finance/chart/{s}"
           f"?interval={interval}&range={r}")
    content = fetch(url)
    if not content:
        return {"symbol": symbol, "status": "error", "error": "Yahoo Finance获取失败"}

    try:
        data = json.loads(content)
        result = data["chart"]["result"][0]
        timestamps = result.get("timestamp", [])
        quote = result.get("indicators", {}).get("quote", [{}])[0]

        opens = quote.get("open", [])
        closes = quote.get("close", [])
        highs = quote.get("high", [])
        lows = quote.get("low", [])
        vols = quote.get("volume", [])

        from datetime import datetime
        candles = []
        data_count = min(count, len(timestamps))
        for i in range(len(timestamps) - data_count, len(timestamps)):
            ts = timestamps[i]
            dt = datetime.fromtimestamp(ts).strftime("%Y-%m-%d") if ts else ""
            candles.append({
                "time": dt,
                "open": round(opens[i], 2) if opens[i] is not None else 0,
                "close": round(closes[i], 2) if closes[i] is not None else 0,
                "high": round(highs[i], 2) if highs[i] is not None else 0,
                "low": round(lows[i], 2) if lows[i] is not None else 0,
                "volume": int(vols[i]) if vols[i] is not None else 0
            })

        return {"symbol": s, "market": "us", "period": period,
                "count": len(candles), "candles": candles, "status": "ok"}
    except Exception as e:
        return {"symbol": symbol, "status": "error", "error": str(e)}


# ============ 指标计算 ============

def _ema(prices: List[float], period: int) -> Optional[float]:
    if len(prices) < period:
        return None
    k_val = 2 / (period + 1)
    ema = sum(prices[:period]) / period
    for p in prices[period:]:
        ema = p * k_val + ema * (1 - k_val)
    return round(ema, 3)


def _calc_ma(prices: List[float], period: int) -> Optional[float]:
    if len(prices) < period:
        return None
    return round(sum(prices[-period:]) / period, 3)


def get_technical_indicators(symbol: str, indicator_type: str = "macd",
                               params: Dict = None) -> Dict[str, Any]:
    """
    计算技术指标
    indicator_type: macd / kdj / rsi / boll / ma / all
    """
    p = params or {}
    n = p.get("n", 20)

    # 自动检测市场
    market = detect_market(symbol)
    kline_data = get_kline(symbol, period="D", count=120)

    if kline_data.get("status") != "ok" or not kline_data.get("candles"):
        return {"symbol": symbol, "market": market, "indicator": indicator_type,
                "status": "error", "error": "数据不足"}

    closes = [c["close"] for c in kline_data["candles"] if c["close"] > 0]
    highs = [c["high"] for c in kline_data["candles"] if c["high"] > 0]
    lows = [c["low"] for c in kline_data["candles"] if c["low"] > 0]

    if len(closes) < 10:
        return {"symbol": symbol, "indicator": indicator_type,
                "status": "error", "error": "数据不足"}

    if indicator_type == "all":
        return {
            "symbol": symbol,
            "market": market,
            "indicators": "all",
            "macd": _calc_macd(closes, symbol),
            "kdj": _calc_kdj(closes, highs, lows, symbol, 9),
            "rsi": _calc_rsi(closes, symbol, 14),
            "boll": _calc_boll(closes, symbol, 20),
            "ma": _calc_ma_multi(closes, symbol, [5, 10, 20, 60]),
            "status": "ok"
        }

    dispatch = {
        "macd": lambda: _calc_macd(closes, symbol, n),
        "kdj": lambda: _calc_kdj(closes, highs, lows, symbol, p.get("period", 9)),
        "rsi": lambda: _calc_rsi(closes, symbol, p.get("period", 14)),
        "boll": lambda: _calc_boll(closes, symbol, n),
        "ma": lambda: _calc_ma_multi(closes, symbol, p.get("periods", [5, 10, 20, 60])),
    }
    fn = dispatch.get(indicator_type)
    if not fn:
        return {"symbol": symbol, "indicator": indicator_type, "status": "error", "error": "未知指标"}
    return fn()


def _calc_macd(closes: List[float], symbol: str, n: int = 20) -> Dict[str, Any]:
    if len(closes) < 35:
        return {"symbol": symbol, "indicator": "macd", "status": "error", "error": "数据不足"}

    ema12 = _ema(closes, 12)
    ema26 = _ema(closes, 26)
    dif = round(ema12 - ema26, 3) if ema12 and ema26 else 0

    # 计算历史DIF用于DEA
    dif_series = []
    for i in range(26, len(closes)):
        e12 = _ema(closes[:i+1], 12)
        e26 = _ema(closes[:i+1], 26)
        if e12 and e26:
            dif_series.append(e12 - e26)
    dea = _calc_ema(dif_series, 9) if len(dif_series) >= 9 else round(sum(dif_series)/len(dif_series), 3) if dif_series else 0

    macd_bar = round(2 * (dif - dea), 3) if dea else 0

    return {
        "symbol": symbol, "indicator": "macd",
        "dif": dif, "dea": dea, "macd_bar": macd_bar,
        "trend": "金叉看涨" if dif > dea else "死叉看跌",
        "signal": "买入" if dif > dea and macd_bar > 0 else ("观望" if abs(macd_bar) < 0.05 else "卖出"),
        "status": "ok"
    }


def _calc_kdj(closes: List[float], highs: List[float], lows: List[float],
               symbol: str, period: int = 9) -> Dict[str, Any]:
    if len(closes) < period:
        return {"symbol": symbol, "indicator": "kdj", "status": "error", "error": "数据不足"}

    k, d = 50.0, 50.0
    for i in range(-period + 1, 1):
        ln = min(lows[i:i+period]) if lows[i:i+period] else lows[-1]
        hn = max(highs[i:i+period]) if highs[i:i+period] else highs[-1]
        rsv = 100 * (closes[-1] - ln) / (hn - ln) if hn != ln else 50
        k = 2/3 * k + 1/3 * rsv
        d = 2/3 * d + 1/3 * k

    k_v, d_v, j_v = round(k, 2), round(d, 2), round(3*k - 2*d, 2)
    signal = ("严重超买" if k_v > 80 else "超买区金叉" if k_v > d_v else
              "严重超卖" if k_v < 20 else "超卖区死叉" if k_v < d_v else "中性")

    return {"symbol": symbol, "indicator": "kdj",
            "k": k_v, "d": d_v, "j": j_v, "signal": signal, "status": "ok"}


def _calc_rsi(closes: List[float], symbol: str, period: int = 14) -> Dict[str, Any]:
    if len(closes) < period + 1:
        return {"symbol": symbol, "indicator": "rsi", "status": "error", "error": "数据不足"}

    gains, losses = [], []
    for i in range(1, len(closes)):
        diff = closes[i] - closes[i-1]
        gains.append(max(diff, 0))
        losses.append(max(-diff, 0))

    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period
    rsi = 100 if avg_loss == 0 else round(100 - 100 / (1 + avg_gain / avg_loss), 2)
    signal = "超买" if rsi > 70 else ("超卖" if rsi < 30 else "中性")

    return {"symbol": symbol, "indicator": "rsi",
            "rsi": rsi, "period": period, "signal": signal, "status": "ok"}


def _calc_boll(closes: List[float], symbol: str, n: int = 20) -> Dict[str, Any]:
    if len(closes) < n:
        return {"symbol": symbol, "indicator": "boll", "status": "error", "error": "数据不足"}

    mid = round(statistics.mean(closes[-n:]), 3)
    std = round(statistics.stdev(closes[-n:]), 3)
    upper = round(mid + 2 * std, 3)
    lower = round(mid - 2 * std, 3)
    current = closes[-1]
    pct_b = round((current - lower) / (upper - lower) * 100, 2) if upper != lower else 50
    signal = "突破上轨" if current > upper else ("突破下轨" if current < lower else "轨道内运行")

    return {"symbol": symbol, "indicator": "boll",
            "upper": upper, "mid": mid, "lower": lower,
            "current": current, "pct_b": pct_b, "signal": signal, "status": "ok"}


def _calc_ma_multi(closes: List[float], symbol: str, periods: List[int]) -> Dict[str, Any]:
    result = {}
    for period in periods:
        ma = _calc_ma(closes, period)
        if ma:
            current = closes[-1]
            result[f"ma{period}"] = ma
            result[f"ma{period}_diff"] = round((current - ma) / ma * 100, 2)

    ma_values = [(p, result.get(f"ma{p}")) for p in sorted(periods) if result.get(f"ma{p}")]
    if len(ma_values) >= 3:
        is_bullish = all(ma_values[i][1] > ma_values[i+1][1] for i in range(len(ma_values)-1))
        is_bearish = all(ma_values[i][1] < ma_values[i+1][1] for i in range(len(ma_values)-1))
        arrangement = "多头排列" if is_bullish else ("空头排列" if is_bearish else "混乱")
    else:
        arrangement = "数据不足"

    return {"symbol": symbol, "indicator": "ma",
            "mas": result, "arrangement": arrangement, "close": closes[-1], "status": "ok"}
