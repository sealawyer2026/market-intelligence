# -*- coding: utf-8 -*-
"""
Quote Module - 实时行情模块 v1.2
支持: A股(沪深京) / 港股 / 美股
Tool Wrapper Pattern: 封装腾讯财经/新浪财经/多源美股接口
"""

import urllib.request
import urllib.error
import json
import re
from typing import List, Dict, Any, Optional


def fetch(url: str, encoding: str = "utf-8", timeout: int = 8) -> Optional[str]:
    """通用HTTP请求"""
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode(encoding, errors="replace")
    except Exception:
        return None


def fetch_all(urls: List[tuple], encoding: str = "utf-8") -> Optional[str]:
    """尝试多个URL，返回第一个成功的"""
    for url, enc in urls:
        result = fetch(url, enc)
        if result and len(result) > 50:
            return result
    return None


def detect_market(symbol: str) -> str:
    """检测市场类型，返回: 'cn_a' / 'cn_bj' / 'hk' / 'us' / 'unknown'"""
    s = symbol.strip().upper()

    if ".HK" in s or s.startswith("HK") or ":HK" in s:
        return "hk"
    if ".US" in s or ":US" in s or s.startswith("US:"):
        return "us"
    if s.startswith(("SH", "SZ")):
        return "cn_a" if not s.startswith("BJ") else "cn_bj"
    if s.startswith("BJ"):
        return "cn_bj"

    # 港股: 5位数字
    if len(s) == 5 and s.isdigit():
        return "hk"
    if len(s) == 4 and s.isdigit():
        return "hk"

    # 港股常见代码前缀
    hk_prefixes = ("00700", "00939", "00941", "03690", "09988", "09618",
                   "02318", "02382", "01398", "02628", "01088", "01299",
                   "01810", "02015", "02382", "06160", "06618", "02600")
    if any(s.startswith(p) for p in hk_prefixes) and len(s) <= 6:
        return "hk"

    # 美股代码（全大写字母1-5个）
    if re.match(r'^[A-Z]{1,5}$', s) and len(s) >= 1:
        # 排除A股代码
        return "us"

    # A股: 6位数字
    if len(s) == 6 and s.isdigit():
        if s.startswith(("4", "8")):
            return "cn_bj"
        return "cn_a"

    return "cn_a"


def normalize_symbol(symbol: str) -> str:
    """标准化股票代码"""
    s = symbol.strip().upper()
    if ".HK" in s:
        num = re.search(r'(\d+)', s)
        return f"hk{num.group(1).zfill(5)}" if num else symbol.lower()
    if ".US" in s:
        return s.replace(".US", "")
    if ":US" in s:
        return s[3:]

    market = detect_market(symbol)
    if market == "hk":
        num = re.search(r'(\d+)', s)
        return f"hk{num.group(1).zfill(5)}" if num else symbol.lower()
    elif market == "us":
        return s
    else:
        num = re.search(r'(\d+)', s)
        code = num.group(1)[:6] if num else s[:6]
        if code.startswith(("0", "3")):
            return f"sz{code}"
        elif code.startswith("6"):
            return f"sh{code}"
        return code


def get_quote(symbol: str) -> Dict[str, Any]:
    """获取单只股票实时报价，自动识别: A股 / 港股 / 美股"""
    market = detect_market(symbol)
    if market == "hk":
        return _get_quote_hk(symbol)
    elif market == "us":
        return _get_quote_us(symbol)
    else:
        return _get_quote_cn(symbol)


# ============ A股行情 ============

def _get_quote_cn(symbol: str) -> Dict[str, Any]:
    norm = normalize_symbol(symbol)
    url = f"http://qt.gtimg.cn/q={norm}"
    content = fetch(url, "gbk")
    if not content:
        return _get_quote_sina(symbol)
    return _parse_tencent_quote(content, symbol)


def _parse_tencent_quote(content: str, symbol: str) -> Dict[str, Any]:
    try:
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

        return {
            "symbol": symbol, "market": detect_market(symbol),
            "name": fields[40] if len(fields) > 40 else symbol,
            "price": price, "prev_close": prev_close,
            "change": round(change, 2), "pct_change": round(pct, 2),
            "open": open_p, "high": high, "low": low,
            "volume": int(vol), "volume_hands": round(vol / 100, 2),
            "amount_wan": round(price * vol / 10000, 2) if price and vol else 0,
            "bid1": float(fields[9]) if fields[9] else 0,
            "ask1": float(fields[19]) if fields[19] else 0,
            "bid_vol1": int(fields[10]) if fields[10] else 0,
            "ask_vol1": int(fields[20]) if fields[20] else 0,
            "currency": "CNY", "status": "ok"
        }
    except Exception as e:
        return _get_quote_sina(symbol)


def _get_quote_sina(symbol: str) -> Dict[str, Any]:
    norm = normalize_symbol(symbol)
    if len(norm) == 6:
        norm = ("sz" if norm.startswith(("0", "3")) else "sh") + norm
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
            "symbol": symbol, "market": detect_market(symbol),
            "name": fields[0] if fields[0] else symbol,
            "price": price, "prev_close": prev_close,
            "change": round(change, 2), "pct_change": round(pct, 2),
            "open": open_p, "high": high, "low": low,
            "volume": int(vol), "currency": "CNY", "status": "ok"
        }
    except Exception as e:
        return {"symbol": symbol, "status": "error", "error": str(e)}


# ============ 港股行情 ============

def _get_quote_hk(symbol: str) -> Dict[str, Any]:
    num_match = re.search(r'(\d+)', symbol)
    if not num_match:
        return {"symbol": symbol, "status": "error", "error": "无效港股代码"}
    code = num_match.group(1).zfill(5)
    url = f"http://qt.gtimg.cn/q=hk{code}"
    content = fetch(url, "gbk")
    if not content:
        return {"symbol": symbol, "status": "error", "error": "港股数据获取失败"}

    try:
        m = re.search(r'="([^"]+)"', content)
        if not m:
            return {"symbol": symbol, "status": "error", "error": "解析失败"}
        fields = m.group(1).split("~")
        if len(fields) < 40:
            return {"symbol": symbol, "status": "error", "error": "字段不足"}

        price = float(fields[3]) if fields[3] else 0
        prev_close = float(fields[4]) if fields[4] else 0
        open_p = float(fields[5]) if fields[5] else 0
        vol = float(fields[6]) if fields[6] else 0
        high = float(fields[33]) if fields[33] else 0
        low = float(fields[34]) if fields[34] else 0
        change = price - prev_close
        pct = (change / prev_close * 100) if prev_close else 0

        return {
            "symbol": symbol, "market": "hk",
            "name": fields[40] if len(fields) > 40 else symbol,
            "code_hk": code,
            "price": price, "prev_close": prev_close,
            "change": round(change, 3), "pct_change": round(pct, 2),
            "open": open_p, "high": high, "low": low,
            "volume": int(vol), "amount_hk": round(price * vol, 2) if price and vol else 0,
            "bid1": float(fields[9]) if fields[9] else 0,
            "ask1": float(fields[19]) if fields[19] else 0,
            "currency": "HKD", "status": "ok"
        }
    except Exception as e:
        return {"symbol": symbol, "status": "error", "error": str(e)}


# ============ 美股行情（多源） ============

def _get_quote_us(symbol: str) -> Dict[str, Any]:
    """美股行情：多源自动切换 Yahoo → Sina → Stooq"""
    s = symbol.strip().upper().replace(".US", "").replace("US:", "")

    # 源1: Yahoo Finance
    try:
        url = (f"https://query1.finance.yahoo.com/v8/finance/chart/{s}"
               f"?interval=1d&range=1d")
        content = fetch(url, timeout=10)
        if content and "chart" in content:
            data = json.loads(content)
            meta = data.get("chart", {}).get("result", [{}])[0].get("meta", {})
            price = meta.get("regularMarketPrice", 0)
            if price > 0:
                prev_close = meta.get("chartPreviousClose", 0) or meta.get("previousClose", 0)
                change = round(price - prev_close, 2) if prev_close else 0
                pct = round(change / prev_close * 100, 2) if prev_close else 0
                return {
                    "symbol": s, "market": "us",
                    "name": meta.get("shortName", s),
                    "price": price, "prev_close": prev_close,
                    "change": change, "pct_change": pct,
                    "open": meta.get("regularMarketOpen", 0),
                    "high": meta.get("regularMarketDayHigh", 0),
                    "low": meta.get("regularMarketDayLow", 0),
                    "volume": meta.get("regularMarketVolume", 0),
                    "volume_fmt": _fmt_number(meta.get("regularMarketVolume", 0)),
                    "currency": meta.get("currency", "USD"),
                    "exchange": meta.get("exchangeName", "US"),
                    "market_cap": meta.get("marketCap", 0),
                    "market_cap_fmt": _fmt_number(meta.get("marketCap", 0)),
                    "fifty_two_high": meta.get("fiftyTwoWeekHigh", 0),
                    "fifty_two_low": meta.get("fiftyTwoWeekLow", 0),
                    "data_source": "Yahoo Finance",
                    "status": "ok"
                }
    except Exception:
        pass

    # 源2: 新浪美股行情
    try:
        content = fetch(f"http://hq.sinajs.cn/list=gb_{s.lower()}", "gbk", timeout=8)
        if content and "=" in content:
            m = re.search(r'="([^"]+)"', content)
            if m:
                fields = m.group(1).split(",")
                if len(fields) >= 5:
                    price = float(fields[0]) if fields[0] else 0
                    prev_close = float(fields[1]) if fields[1] else 0
                    change = round(price - prev_close, 2) if prev_close else 0
                    pct = round(change / prev_close * 100, 2) if prev_close else 0
                    return {
                        "symbol": s, "market": "us",
                        "name": fields[13] if len(fields) > 13 else s,
                        "price": price, "prev_close": prev_close,
                        "change": change, "pct_change": pct,
                        "open": float(fields[5]) if len(fields) > 5 and fields[5] else 0,
                        "high": float(fields[6]) if len(fields) > 6 and fields[6] else 0,
                        "low": float(fields[7]) if len(fields) > 7 and fields[7] else 0,
                        "currency": "USD",
                        "data_source": "Sina Finance",
                        "status": "ok"
                    }
    except Exception:
        pass

    # 源3: Stooq (CSV)
    try:
        content = fetch(f"https://stooq.com/q/d/l/?s={s}.us&i=d", timeout=8)
        if content and "Date" not in content and len(content) > 20:
            lines = content.strip().split("\n")
            if len(lines) >= 2:
                last = lines[-1].split(",")
                prev = lines[-2].split(",") if len(lines) > 2 else last
                price = float(last[4]) if len(last) > 4 and last[4] else 0
                prev_p = float(prev[4]) if len(prev) > 4 and prev[4] else price
                change = round(price - prev_p, 2)
                pct = round(change / prev_p * 100, 2) if prev_p else 0
                return {
                    "symbol": s, "market": "us",
                    "name": s, "price": price, "prev_close": prev_p,
                    "change": change, "pct_change": pct,
                    "date": last[0] if last else "",
                    "currency": "USD",
                    "data_source": "Stooq",
                    "status": "ok"
                }
    except Exception:
        pass

    return {
        "symbol": s, "market": "us",
        "status": "error",
        "error": "所有数据源均不可用（网络限制），请手动查询"
    }


def _fmt_number(n: float) -> str:
    if not n:
        return "N/A"
    if n >= 1e12:
        return f"${n/1e12:.2f}T"
    elif n >= 1e9:
        return f"${n/1e9:.2f}B"
    elif n >= 1e6:
        return f"${n/1e6:.2f}M"
    elif n >= 1e3:
        return f"${n/1e3:.2f}K"
    return f"${n:.2f}"


# ============ 批量 & 搜索 ============

def get_quotes_batch(symbols: List[str]) -> List[Dict[str, Any]]:
    return [get_quote(sym) for sym in symbols]


def search_stocks(query: str, market: str = "cn") -> List[Dict[str, str]]:
    results = []
    if market in ("cn", "all"):
        results.extend(_search_cn(query))
    if market in ("hk", "all"):
        results.extend(_search_hk(query))
    if market in ("us", "all"):
        results.extend(_search_us(query))
    return results[:20]


def _search_cn(query: str) -> List[Dict[str, str]]:
    try:
        url = f"http://suggest3.sinajs.cn/suggest/type=11,12,13,14&key={query}"
        content = fetch(url, "utf-8")
        if not content:
            return []
        m = re.search(r'"([^"]+)"', content)
        if not m:
            return []
        results = []
        for item in m.group(1).split(";")[:8]:
            parts = item.split(",")
            if len(parts) >= 4:
                results.append({
                    "symbol": parts[3] if len(parts) > 3 else "",
                    "name": parts[0] if parts else query,
                    "market": "A-shares",
                    "type": parts[2] if len(parts) > 2 else "股票"
                })
        return results
    except Exception:
        return []


def _search_hk(query: str) -> List[Dict[str, str]]:
    try:
        url = f"http://suggest3.sinajs.cn/suggest/type=151,152,153,154&key={query}"
        content = fetch(url, "utf-8")
        if not content:
            return []
        m = re.search(r'"([^"]+)"', content)
        if not m:
            return []
        results = []
        for item in m.group(1).split(";")[:5]:
            parts = item.split(",")
            if len(parts) >= 3:
                results.append({
                    "symbol": f"hk.{parts[1]}" if len(parts) > 1 else query,
                    "code": parts[1] if len(parts) > 1 else "",
                    "name": parts[0] if parts else query,
                    "market": "HK",
                    "type": "港股"
                })
        return results
    except Exception:
        return []


def _search_us(query: str) -> List[Dict[str, str]]:
    try:
        # 新浪美股搜索
        url = f"http://suggest3.sinajs.cn/suggest/type=61,62,63,64&key={query}"
        content = fetch(url, "utf-8")
        if not content:
            return []
        m = re.search(r'"([^"]+)"', content)
        if not m:
            return []
        results = []
        for item in m.group(1).split(";")[:5]:
            parts = item.split(",")
            if len(parts) >= 3:
                sym = parts[1].upper() if len(parts) > 1 else query.upper()
                results.append({
                    "symbol": f"{sym}.US",
                    "name": parts[0] if parts else query,
                    "market": "US",
                    "type": parts[2] if len(parts) > 2 else "Stock"
                })
        return results
    except Exception:
        return []


def get_profile(symbol: str) -> Dict[str, Any]:
    q = get_quote(symbol)
    m = detect_market(symbol)
    return {
        "symbol": symbol, "name": q.get("name", symbol),
        "market": m,
        "exchange": "US" if m == "us" else ("HKEx" if m == "hk" else "SSE/SZSE"),
        "currency": "USD" if m == "us" else ("HKD" if m == "hk" else "CNY"),
        "price": q.get("price", 0),
        "market_cap": q.get("market_cap", 0),
        "market_cap_fmt": q.get("market_cap_fmt", "N/A"),
        "pe": q.get("pe", None),
        "status": "ok"
    }
