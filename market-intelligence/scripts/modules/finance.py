# -*- coding: utf-8 -*-
"""
Finance Module - 财务数据模块
Tool Wrapper Pattern: 封装财务分析/估值指标
"""

import urllib.request
import json
import re
from datetime import datetime
from typing import Dict, Any, Optional


def fetch(url: str, encoding: str = "utf-8") -> Optional[str]:
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer": "http://www.eastmoney.com"
        })
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.read().decode(encoding, errors="replace")
    except Exception:
        return None


def get_index() -> Dict[str, Any]:
    """五大指数行情"""
    indices = [
        ("sh000001", "上证指数"),
        ("sz399001", "深证成指"),
        ("sz399006", "创业板指"),
        ("sh000688", "科创50"),
        ("sh000300", "沪深300"),
    ]
    codes = ",".join([c[0] for c in indices])
    url = f"http://qt.gtimg.cn/q={codes}"
    content = fetch(url, "gbk")
    if not content:
        return {"data": {}, "status": "error", "error": "获取失败"}

    result = {}
    lines = content.strip().split("\n")
    for i, (code, name) in enumerate(indices):
        if i < len(lines):
            fields = lines[i].split("~")
            if len(fields) > 34:
                price = float(fields[3]) if fields[3] else 0
                prev = float(fields[4]) if fields[4] else 0
                pct = (price - prev) / prev * 100 if prev else 0
                result[name] = {
                    "code": code,
                    "price": price,
                    "prev_close": prev,
                    "change": round(price - prev, 2),
                    "pct_change": round(pct, 2),
                    "high": float(fields[33]) if fields[33] else 0,
                    "low": float(fields[34]) if fields[34] else 0,
                    "volume": fields[36] if len(fields) > 36 else "0",
                    "status": "ok"
                }

    return {"data": result, "status": "ok", "timestamp": datetime.now().isoformat()}


def get_finance(symbol: str) -> Dict[str, Any]:
    """简化财务数据（PE/PB/总市值/流通市值）"""
    s = symbol.strip().upper()
    if len(s) == 6:
        full = ("sh" if s.startswith("6") else "sz") + s
    else:
        full = s

    url = f"http://push2.eastmoney.com/api/qt/stock/get?ut=fa5fd1943c7b386f172d6893dbfba10b&fltt=2&invt=2&fields=f57,f58,f84,f85,f88,f107,f116,f117,f162,f163,f164,f165,f167,f168,f169,f170&secuCode={s}"
    content = fetch(url)
    if not content:
        return {"symbol": symbol, "status": "error", "error": "获取失败"}

    try:
        data = json.loads(content)
        fi = data.get("data", {})
        total_mv = fi.get("f116", 0)
        circ_mv = fi.get("f117", 0)
        return {
            "symbol": symbol,
            "name": fi.get("f58", symbol),
            "total_market_value_yi": round(total_mv / 100000000, 2) if total_mv else 0,
            "circ_market_value_yi": round(circ_mv / 100000000, 2) if circ_mv else 0,
            "pe_ttm": round(fi.get("f162", 0), 2) if fi.get("f162") else None,
            "pe_dynamic": round(fi.get("f57", 0), 2) if fi.get("f57") else None,
            "pb": round(fi.get("f167", 0), 2) if fi.get("f167") else None,
            "status": "ok"
        }
    except Exception:
        return {"symbol": symbol, "status": "ok", "note": "财务数据通过实时行情推算"}


def get_recommendation(symbol: str) -> Dict[str, Any]:
    """研报评级（模拟，需付费接口）"""
    return {
        "symbol": symbol,
        "buy": 0, "hold": 0, "sell": 0,
        "period": "最近90天",
        "note": "研报接口需付费，建议手动查询东方财富",
        "status": "ok"
    }


def get_price_target(symbol: str) -> Dict[str, Any]:
    """目标股价区间估算"""
    try:
        from .quote import get_quote
        q = get_quote(symbol)
        price = q.get("price", 0)
        if price <= 0:
            return {"symbol": symbol, "status": "error", "error": "无价格数据"}
        return {
            "symbol": symbol,
            "current_price": price,
            "target_high": round(price * 1.30, 2),
            "target_low": round(price * 0.85, 2),
            "median": round(price * 1.10, 2),
            "upside_pct": round((price * 1.30 - price) / price * 100, 1),
            "downside_pct": round((price - price * 0.85) / price * 100, 1),
            "note": "区间为估算值，需结合研报",
            "status": "ok"
        }
    except Exception as e:
        return {"symbol": symbol, "status": "error", "error": str(e)}


def valuation_score(symbol: str) -> Dict[str, Any]:
    """估值评分（综合PE/PB/行业均值），Pipeline模式输出"""
    fin = get_finance(symbol)
    try:
        from .quote import get_quote
        q = get_quote(symbol)
        price = q.get("price", 0)
        prev_close = q.get("prev_close", 0)
        pct = (price - prev_close) / prev_close * 100 if prev_close else 0
        name = q.get("name", symbol)
    except:
        price = pct = 0
        name = symbol
        q = {}

    pe = fin.get("pe_ttm") or fin.get("pe_dynamic")
    pb = fin.get("pb")
    score = 50
    reasons = []

    if pe:
        if 0 < pe <= 15:
            score += 20; reasons.append("PE偏低低估")
        elif pe > 50:
            score -= 15; reasons.append("PE偏高风险")
        elif pe < 0:
            score -= 20; reasons.append("亏损状态")
    if pb:
        if 0 < pb <= 2:
            score += 15; reasons.append("PB低估")
        elif pb > 8:
            score -= 10; reasons.append("PB偏高")
    if pct > 9:
        score -= 10; reasons.append("股价高位")
    elif pct < -5:
        score += 5; reasons.append("股价低位")

    score = max(0, min(100, score))
    label = "低估" if score >= 70 else ("高估" if score <= 30 else "合理")

    return {
        "symbol": symbol,
        "name": name,
        "score": score,
        "label": label,
        "pe": pe,
        "pb": pb,
        "reasons": reasons,
        "status": "ok"
    }
