# -*- coding: utf-8 -*-
"""
Screener Module - 选股器模块
Tool Wrapper Pattern: 按行业/市值/PE/量比等条件筛选股票
"""

import urllib.request
import json
import re
from datetime import datetime
from typing import Dict, Any, List, Optional


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


def normalize_symbol(s: str) -> str:
    s = s.strip().upper()
    if s.startswith(("SH", "SZ", "BJ")):
        return s[:6]
    if len(s) == 6:
        if s.startswith(("0", "3")):
            return "sz" + s
        elif s.startswith("6"):
            return "sh" + s
    return s


def screen_stocks(market: str = "cn", filters: Dict = None) -> Dict[str, Any]:
    """
    选股器
    filters 支持:
      - top_gainers: 今日涨幅前N
      - top_losers: 今日跌幅前N
      - high_volume: 今日放量
      - by_industry: 行业板块
      - by_pe: PE区间
      - by_pb: PB区间
    """
    f = filters or {}

    if f.get("top_gainers"):
        return _screen_top(f.get("top_gainers", 10), sort="desc")
    elif f.get("top_losers"):
        return _screen_top(f.get("top_losers", 10), sort="asc")
    elif f.get("high_volume"):
        return _screen_volume(f.get("high_volume", 10))
    elif f.get("by_industry"):
        return _screen_industry(f.get("by_industry"), f.get("limit", 20))
    elif f.get("hot_concept"):
        return _screen_concept(f.get("hot_concept", 20))
    else:
        return _screen_top(20, sort="desc")


def _screen_top(limit: int = 20, sort: str = "desc") -> Dict[str, Any]:
    """涨幅榜/跌幅榜"""
    # 东财排行榜API
    url = f"http://push2.eastmoney.com/api/qt/clist/get?cb=jQuery&pn=1&pz={limit}&po=1&np=1&ut=bd1d9ddb04089700cf9c27f6f7426281&fltt=2&invt=2&fid=f3&fs=m:0+t:6,m:0+t:13,m:0+t:14,m:1+t:2,m:1+t:23&fields=f2,f3,f4,f5,f6,f7,f12,f13,f14,f15,f16,f17,f18,f20,f21,f23,f24,f25,f22,f11,f62,f128,f136,f115,f152&_={int(datetime.now().timestamp())}"

    content = fetch(url)
    if not content:
        return {"type": "top", "stocks": [], "status": "error", "error": "获取失败"}

    try:
        m = re.search(r'jQuery\((.+)\)', content)
        if m:
            data = json.loads(m.group(1))
            items = data.get("data", {}).get("diff", [])
        else:
            items = []

        results = []
        for item in items:
            pct = item.get("f3", 0)
            if (sort == "desc" and pct > 0) or (sort == "asc" and pct < 0):
                results.append({
                    "symbol": item.get("f12", ""),
                    "name": item.get("f14", ""),
                    "price": item.get("f2", 0),
                    "pct_change": pct,
                    "change": item.get("f4", 0),
                    "volume": item.get("f6", 0),
                    "amount": item.get("f6", 0) * item.get("f2", 0) / 10000 if item.get("f2") else 0,
                    "turnover": item.get("f8", 0),  # 换手率%
                    "status": "ok"
                })

        return {
            "type": "top_gainers" if sort == "desc" else "top_losers",
            "count": len(results),
            "stocks": results,
            "status": "ok",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {"type": "top", "stocks": [], "status": "error", "error": str(e)}


def _screen_volume(limit: int = 20) -> Dict[str, Any]:
    """放量股"""
    url = f"http://push2.eastmoney.com/api/qt/clist/get?pn=1&pz={limit}&po=1&np=1&fltt=2&invt=2&fid=f10&fs=m:0+t:6,m:0+t:13,m:0+t:14,m:1+t:2,m:1+t:23&fields=f2,f3,f5,f6,f10,f12,f14&_={int(datetime.now().timestamp())}"

    content = fetch(url)
    if not content:
        return {"type": "volume", "stocks": [], "status": "error", "error": "获取失败"}

    try:
        m = re.search(r'jQuery\((.+)\)', content)
        if m:
            data = json.loads(m.group(1))
            items = data.get("data", {}).get("diff", [])
        else:
            items = []

        results = []
        for item in items:
            turnover = item.get("f10", 0)
            if turnover and turnover > 5:  # 换手率>5%
                results.append({
                    "symbol": item.get("f12", ""),
                    "name": item.get("f14", ""),
                    "price": item.get("f2", 0),
                    "pct_change": item.get("f3", 0),
                    "volume_ratio": turnover,
                    "volume": item.get("f5", 0),
                    "turnover_rate": turnover,
                    "status": "ok"
                })

        return {
            "type": "high_volume",
            "count": len(results),
            "stocks": results,
            "status": "ok"
        }
    except Exception as e:
        return {"type": "volume", "stocks": [], "status": "error", "error": str(e)}


def _screen_industry(industry: str, limit: int = 20) -> Dict[str, Any]:
    """按行业板块筛选"""
    # 先获取行业板块列表
    url = "http://push2.eastmoney.com/api/qt/clist/get?pn=1&pz=100&po=1&np=1&fltt=2&invt=2&fid=f3&fs=m:90+t:2+f:!50&fields=f2,f3,f4,f5,f6,f7,f12,f13,f14,f20,f104,f105,f106"
    content = fetch(url)
    if not content:
        return {"type": "industry", "industry": industry, "stocks": [], "status": "error", "error": "获取失败"}

    try:
        m = re.search(r'jQuery\((.+)\)', content)
        if m:
            data = json.loads(m.group(1))
            items = data.get("data", {}).get("diff", [])
        else:
            items = []

        # 找到对应行业
        matched = []
        for item in items:
            if industry in item.get("f14", ""):
                matched.append({
                    "symbol": item.get("f12", ""),
                    "name": item.get("f14", ""),
                    "pct_change": item.get("f3", 0),
                    "lead_stock": item.get("f20", ""),
                    "pe": item.get("f104", ""),
                    "status": "ok"
                })
                if len(matched) >= limit:
                    break

        return {
            "type": "industry",
            "industry": industry,
            "count": len(matched),
            "stocks": matched,
            "status": "ok"
        }
    except Exception as e:
        return {"type": "industry", "stocks": [], "status": "error", "error": str(e)}


def _screen_concept(limit: int = 20) -> Dict[str, Any]:
    """热点概念板块"""
    url = f"http://push2.eastmoney.com/api/qt/clist/get?pn=1&pz={limit}&po=1&np=1&fltt=2&invt=2&fid=f3&fs=m:90+t:3+f:!50&fields=f2,f3,f4,f12,f14,f20,f104,f105,f106&_={int(datetime.now().timestamp())}"

    content = fetch(url)
    if not content:
        return {"type": "concept", "concepts": [], "status": "error", "error": "获取失败"}

    try:
        m = re.search(r'jQuery\((.+)\)', content)
        if m:
            data = json.loads(m.group(1))
            items = data.get("data", {}).get("diff", [])
        else:
            items = []

        results = []
        for item in items:
            pct = item.get("f3", 0)
            if pct > 0:  # 只显示上涨板块
                results.append({
                    "concept_code": item.get("f12", ""),
                    "concept_name": item.get("f14", ""),
                    "pct_change": pct,
                    "lead_stock": item.get("f20", ""),
                    "stock_count": item.get("f104", ""),
                    "status": "ok"
                })

        return {
            "type": "hot_concept",
            "count": len(results),
            "concepts": results,
            "status": "ok"
        }
    except Exception as e:
        return {"type": "concept", "concepts": [], "status": "error", "error": str(e)}
