# -*- coding: utf-8 -*-
"""
Quote Module - 实时行情模块
Tool Wrapper Pattern: 封装腾讯财经/新浪财经实时行情接口
"""

import urllib.request
import urllib.error
import json
import re
from typing import List, Dict, Any, Optional


def fetch(url: str, encoding: str = "gbk") -> Optional[str]:
    """通用HTTP请求"""
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })
        with urllib.request.urlopen(req, timeout=8) as resp:
            return resp.read().decode(encoding, errors="replace")
    except Exception:
        return None


def normalize_symbol(symbol: str) -> str:
    """标准化股票代码为腾讯格式"""
    s = symbol.strip().upper()
    if s.startswith("SH") or s.startswith("SZ"):
        return s[:6]
    # A股默认
    if len(s) == 6:
        if s.startswith(("0", "3")):
            return "sz" + s
        elif s.startswith(("6",)):
            return "sh" + s
        elif s.startswith(("4", "8")):
            return "bj" + s
    return symbol.lower()


def get_quote(symbol: str) -> Dict[str, Any]:
    """
    获取单只股票实时报价
    兼容沪深京港美股
    """
    norm = normalize_symbol(symbol)
    if len(norm) == 8:
        url = f"http://qt.gtimg.cn/q={norm}"
    else:
        # 尝试腾讯格式
        url = f"http://qt.gtimg.cn/q={norm}"

    content = fetch(url)
    if not content:
        # fallback to 新浪
        return _get_quote_sina(symbol)

    return _parse_tencent_quote(content, symbol)


def _parse_tencent_quote(content: str, symbol: str) -> Dict[str, Any]:
    """解析腾讯行情数据"""
    try:
        # 格式: v_sh600519="1,...", 共约40个字段
        m = re.search(r'="([^"]+)"', content)
        if not m:
            return _get_quote_sina(symbol)

        fields = m.group(1).split("~")
        if len(fields) < 40:
            return _get_quote_sina(symbol)

        price = float(fields[3]) if fields[3] else 0
        prev_close = float(fields[4]) if fields[4] else 0
        open_p = float(fields[5]) if fields[5] else 0
        vol = float(fields[6]) if fields[6] else 0
        high = float(fields[33]) if fields[33] else 0
        low = float(fields[34]) if fields[34] else 0

        change = price - prev_close
        pct = (change / prev_close * 100) if prev_close else 0

        # 成交量转换为手
        vol_hands = vol / 100 if vol else 0
        # 成交额(万元)
        amount_wan = (price * vol / 10000) if (price and vol) else 0

        return {
            "symbol": symbol,
            "name": fields[40] if len(fields) > 40 else symbol,
            "price": price,
            "prev_close": prev_close,
            "change": round(change, 2),
            "pct_change": round(pct, 2),
            "open": open_p,
            "high": high,
            "low": low,
            "volume": int(vol),  # 股数
            "volume_hands": round(vol_hands, 2),
            "amount_wan": round(amount_wan, 2),  # 万元
            "bid1": float(fields[9]) if fields[9] else 0,
            "ask1": float(fields[19]) if fields[19] else 0,
            "bid_vol1": int(fields[10]) if fields[10] else 0,
            "ask_vol1": int(fields[20]) if fields[20] else 0,
            "timestamp": fields[30] if len(fields) > 30 else "",
            "status": "ok"
        }
    except Exception as e:
        return {"symbol": symbol, "status": "error", "error": str(e)}


def _get_quote_sina(symbol: str) -> Dict[str, Any]:
    """Sina财经行情备用"""
    norm = normalize_symbol(symbol)
    if len(norm) == 6:
        if norm.startswith(("0", "3")):
            norm = "sz" + norm
        elif norm.startswith("6"):
            norm = "sh" + norm

    url = f"http://hq.sinajs.cn/list={norm}"
    content = fetch(url, "gbk")
    if not content:
        return {"symbol": symbol, "status": "error", "error": "数据获取失败"}

    try:
        m = re.search(r'="([^"]+)"', content)
        if not m:
            return {"symbol": symbol, "status": "error", "error": "解析失败"}

        fields = m.group(1).split(",")
        if len(fields) < 10:
            return {"symbol": symbol, "status": "error", "error": "字段不足"}

        price = float(fields[3]) if fields[3] else 0
        prev_close = float(fields[2]) if fields[2] else 0
        open_p = float(fields[1]) if fields[1] else 0
        high = float(fields[4]) if fields[4] else 0
        low = float(fields[5]) if fields[5] else 0
        vol = float(fields[8]) if fields[8] else 0

        change = price - prev_close
        pct = (change / prev_close * 100) if prev_close else 0

        return {
            "symbol": symbol,
            "name": fields[0] if fields[0] else symbol,
            "price": price,
            "prev_close": prev_close,
            "change": round(change, 2),
            "pct_change": round(pct, 2),
            "open": open_p,
            "high": high,
            "low": low,
            "volume": int(vol),
            "status": "ok"
        }
    except Exception as e:
        return {"symbol": symbol, "status": "error", "error": str(e)}


def get_quotes_batch(symbols: List[str]) -> List[Dict[str, Any]]:
    """批量获取行情"""
    results = []
    for sym in symbols:
        try:
            q = get_quote(sym)
            results.append(q)
        except:
            results.append({"symbol": sym, "status": "error", "error": "获取失败"})
    return results


def search_stocks(query: str, market: str = "cn") -> List[Dict[str, str]]:
    """
    Finnhub-equivalent: /symbol/search
    搜索股票（按代码或名称模糊搜索）
    """
    try:
        # 使用新浪股票搜索API
        url = f"http://suggest3.sinajs.cn/suggest/type=11,12,13,14&key={query}"
        content = fetch(url, "utf-8")
        if not content:
            return []

        results = []
        # 解析格式: var suggestvalue_11="...数据..."
        m = re.search(r'"([^"]+)"', content)
        if m:
            items = m.group(1).split(";")
            for item in items[:10]:  # 最多10条
                parts = item.split(",")
                if len(parts) >= 4:
                    results.append({
                        "symbol": parts[3] if len(parts) > 3 else "",
                        "code": parts[3] if len(parts) > 3 else "",
                        "name": parts[0] if parts else query,
                        "market": parts[4] if len(parts) > 4 else "SH/SZ",
                        "type": parts[2] if len(parts) > 2 else "股票"
                    })
        return results
    except Exception:
        return []


def get_profile(symbol: str) -> Dict[str, Any]:
    """
    公司概况（简化版，基于公开数据）
    """
    q = get_quote(symbol)
    return {
        "symbol": symbol,
        "name": q.get("name", symbol),
        "exchange": "SSE/SZSE",
        "ipoDate": "",
        "marketCapitalization": q.get("price", 0) * q.get("volume", 0) / 100000000 if q.get("price") and q.get("volume") else 0,
        "currency": "CNY",
        "currentPrice": q.get("price", 0),
        "prevClose": q.get("prev_close", 0),
        "status": "active"
    }
