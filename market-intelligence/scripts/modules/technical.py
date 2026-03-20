# -*- coding: utf-8 -*-
"""
Technical Module - 技术指标模块
Tool Wrapper Pattern: 封装MACD/KDJ/RSI/布林带/均线计算
"""

import urllib.request
import json
import re
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta


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


def normalize_symbol(symbol: str) -> str:
    s = symbol.strip().upper()
    if s.startswith(("SH", "SZ", "BJ")):
        return s[:6]
    if len(s) == 6:
        if s.startswith(("0", "3")):
            return "sz" + s
        elif s.startswith("6"):
            return "sh" + s
        elif s.startswith(("4", "8")):
            return "bj" + s
    return symbol


def get_kline(symbol: str, period: str = "D", count: int = 120) -> Dict[str, Any]:
    """
    获取K线数据（前复权）
    period: D=日K, W=周K, M=月K, 5/15/30/60=分钟K
    """
    norm = normalize_symbol(symbol)
    if len(norm) == 8:
        market = 1 if norm[:2] == "sh" else 0
        code = norm[2:]
    else:
        market = 1 if norm.startswith("6") else 0
        code = norm

    # 腾讯行情K线API（日K）
    period_map = {"D": "day", "W": "week", "M": "month",
                  "5": "5min", "15": "15min", "30": "30min", "60": "60min"}
    p = period_map.get(period, "day")

    url = f"http://web.ifzq.gtimg.cn/appstock/app/fqkline/get?_var=kline_{p}qfq&param={code},{p},,,,{count},qfq"
    content = fetch(url)
    if not content:
        return {"symbol": symbol, "status": "error", "error": "K线获取失败"}

    try:
        # 去掉变量声明，解析JSON
        json_str = re.sub(r'^[^=]+=', '', content.strip())
        data = json.loads(json_str)
        qt_key = list(data.get("data", {}).keys())[0]
        qt_data = data["data"][qt_key]
        qfq_data = qt_data.get("qfq" if p != "day" else "day", [])

        candles = []
        for item in qfq_data[-count:]:
            if len(item) >= 6:
                candles.append({
                    "time": item[0],
                    "open": float(item[1]),
                    "close": float(item[2]),
                    "high": float(item[3]),
                    "low": float(item[4]),
                    "volume": float(item[5]) if len(item) > 5 else 0
                })

        return {
            "symbol": symbol,
            "period": period,
            "count": len(candles),
            "candles": candles,
            "status": "ok"
        }
    except Exception as e:
        return {"symbol": symbol, "status": "error", "error": str(e)}


def _calc_ma(prices: List[float], period: int) -> Optional[float]:
    if len(prices) < period:
        return None
    return round(sum(prices[-period:]) / period, 3)


def _calc_ema(prices: List[float], period: int) -> Optional[float]:
    if len(prices) < period:
        return None
    k = 2 / (period + 1)
    ema = prices[0]
    for p in prices[1:]:
        ema = p * k + ema * (1 - k)
    return round(ema, 3)


def _calc_std(prices: List[float], period: int) -> Optional[float]:
    if len(prices) < period:
        return None
    import statistics
    return round(statistics.stdev(prices[-period:]), 3)


def get_technical_indicators(symbol: str, indicator_type: str = "macd", params: Dict = None) -> Dict[str, Any]:
    """
    计算技术指标
    indicator_type: macd / kdj / rsi / boll / ma
    """
    p = params or {}
    n = p.get("n", 20)  # 周期

    kline_data = get_kline(symbol, period="D", count=120)
    if kline_data.get("status") != "ok" or not kline_data.get("candles"):
        return {"symbol": symbol, "indicator": indicator_type, "status": "error", "error": "数据不足"}

    closes = [c["close"] for c in kline_data["candles"]]
    highs = [c["high"] for c in kline_data["candles"]]
    lows = [c["low"] for c in kline_data["candles"]]

    if indicator_type == "macd":
        return _calc_macd(closes, symbol, n)
    elif indicator_type == "kdj":
        period = p.get("period", 9)
        return _calc_kdj(closes, highs, lows, symbol, period)
    elif indicator_type == "rsi":
        period = p.get("period", 14)
        return _calc_rsi(closes, symbol, period)
    elif indicator_type == "boll":
        return _calc_boll(closes, symbol, n)
    elif indicator_type == "ma":
        periods = p.get("periods", [5, 10, 20, 60])
        return _calc_ma_multi(closes, symbol, periods)
    else:
        return {"symbol": symbol, "indicator": indicator_type, "status": "error", "error": "未知指标"}


def _calc_macd(closes: List[float], symbol: str, n: int = 20) -> Dict[str, Any]:
    """MACD计算: DIF / DEA / MACD柱"""
    if len(closes) < 35:
        return {"symbol": symbol, "indicator": "macd", "status": "error", "error": "数据不足35根K线"}

    ema12 = _ema(closes, 12)
    ema26 = _ema(closes, 26)
    dif = round(ema12 - ema26, 3) if ema12 and ema26 else 0

    # DEA = EMA(DIF, 9)
    dif_series = []
    for i in range(26, len(closes)):
        e12 = _ema(closes[:i+1], 12)
        e26 = _ema(closes[:i+1], 26)
        if e12 and e26:
            dif_series.append(e12 - e26)
    dea = _calc_ema(dif_series, 9) if len(dif_series) >= 9 else round(sum(dif_series)/len(dif_series), 3) if dif_series else 0

    macd_bar = round(2 * (dif - dea), 3) if dea else 0

    # 趋势判断
    trend = "金叉看涨" if dif > dea else "死叉看跌"

    return {
        "symbol": symbol,
        "indicator": "macd",
        "dif": dif,
        "dea": dea,
        "macd_bar": macd_bar,
        "trend": trend,
        "signal": "买入" if dif > dea and macd_bar > 0 else ("观望" if abs(macd_bar) < 0.05 else "卖出"),
        "status": "ok"
    }


def _ema(prices: List[float], period: int) -> Optional[float]:
    if len(prices) < period:
        return None
    k = 2 / (period + 1)
    ema = sum(prices[:period]) / period
    for p in prices[period:]:
        ema = p * k + ema * (1 - k)
    return round(ema, 3)


def _calc_kdj(closes: List[float], highs: List[float], lows: List[float],
              symbol: str, period: int = 9) -> Dict[str, Any]:
    """KDJ随机指标"""
    if len(closes) < period:
        return {"symbol": symbol, "indicator": "kdj", "status": "error", "error": "数据不足"}

    k, d = 50.0, 50.0
    j = 3 * k - 2 * d

    for i in range(-period + 1, 1):
        low_n = min(lows[i:i+period]) if lows[i:i+period] else lows[-1]
        high_n = max(highs[i:i+period]) if highs[i:i+period] else highs[-1]
        rsv = 100 * (closes[-1] - low_n) / (high_n - low_n) if high_n != low_n else 50

        k = 2/3 * k + 1/3 * rsv
        d = 2/3 * d + 1/3 * k
        j = 3 * k - 2 * d

    k_val = round(k, 2)
    d_val = round(d, 2)
    j_val = round(j, 2)

    # 信号判断
    if k_val > d_val and k_val < 80:
        signal = "超买区金叉"
    elif k_val < d_val and k_val > 20:
        signal = "超卖区死叉"
    elif k_val > 80:
        signal = "严重超买"
    elif k_val < 20:
        signal = "严重超卖"
    else:
        signal = "中性"

    return {
        "symbol": symbol,
        "indicator": "kdj",
        "k": k_val,
        "d": d_val,
        "j": j_val,
        "signal": signal,
        "status": "ok"
    }


def _calc_rsi(closes: List[float], symbol: str, period: int = 14) -> Dict[str, Any]:
    """RSI相对强弱指标"""
    if len(closes) < period + 1:
        return {"symbol": symbol, "indicator": "rsi", "status": "error", "error": "数据不足"}

    gains, losses = [], []
    for i in range(1, len(closes)):
        diff = closes[i] - closes[i-1]
        gains.append(max(diff, 0))
        losses.append(max(-diff, 0))

    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period

    if avg_loss == 0:
        rsi = 100
    else:
        rs = avg_gain / avg_loss
        rsi = round(100 - 100 / (1 + rs), 2)

    signal = "超买" if rsi > 70 else ("超卖" if rsi < 30 else "中性")

    return {
        "symbol": symbol,
        "indicator": "rsi",
        "rsi": rsi,
        "period": period,
        "signal": signal,
        "status": "ok"
    }


def _calc_boll(closes: List[float], symbol: str, n: int = 20) -> Dict[str, Any]:
    """布林带"""
    if len(closes) < n:
        return {"symbol": symbol, "indicator": "boll", "status": "error", "error": "数据不足"}

    import statistics
    mid = round(statistics.mean(closes[-n:]), 3)
    std = round(statistics.stdev(closes[-n:]), 3)
    upper = round(mid + 2 * std, 3)
    lower = round(mid - 2 * std, 3)
    current = closes[-1]

    pct_b = round((current - lower) / (upper - lower) * 100, 2) if upper != lower else 50

    signal = "突破上轨" if current > upper else ("突破下轨" if current < lower else "轨道内运行")

    return {
        "symbol": symbol,
        "indicator": "boll",
        "upper": upper,
        "mid": mid,
        "lower": lower,
        "current": current,
        "pct_b": pct_b,
        "signal": signal,
        "status": "ok"
    }


def _calc_ma_multi(closes: List[float], symbol: str, periods: List[int]) -> Dict[str, Any]:
    """多周期均线"""
    result = {}
    for period in periods:
        ma = _calc_ma(closes, period)
        if ma:
            current = closes[-1]
            result[f"ma{period}"] = ma
            result[f"ma{period}_diff"] = round((current - ma) / ma * 100, 2)

    # 均线多头/空头排列
    ma_values = [(p, result.get(f"ma{p}")) for p in sorted(periods) if result.get(f"ma{p}")]
    if len(ma_values) >= 3:
        is_bullish = all(ma_values[i][1] > ma_values[i+1][1] for i in range(len(ma_values)-1))
        is_bearish = all(ma_values[i][1] < ma_values[i+1][1] for i in range(len(ma_values)-1))
        arrangement = "多头排列" if is_bullish else ("空头排列" if is_bearish else "混乱")
    else:
        arrangement = "数据不足"

    return {
        "symbol": symbol,
        "indicator": "ma",
        "mas": result,
        "arrangement": arrangement,
        "close": closes[-1],
        "status": "ok"
    }
