# -*- coding: utf-8 -*-
"""
News Module - 市场资讯与新闻情绪模块
Tool Wrapper Pattern: 封装东方财富/同花顺新闻接口
"""

import urllib.request
import json
import re
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional


def fetch(url: str, encoding: str = "utf-8", timeout: int = 10) -> Optional[str]:
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer": "http://www.eastmoney.com"
        })
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode(encoding, errors="replace")
    except Exception:
        return None


def get_market_news(category: str = "general", count: int = 20) -> Dict[str, Any]:
    """
    获取市场快讯/新闻
    category: general / industry / concept / macro
    """
    # 东方财富快讯API
    url = f"http://np-anotice-stock.eastmoney.com/api/security/ann?sr=-1&page_size={count}&page_index=1&ann_type=SHA,SZA&client_source=web"

    content = fetch(url)
    if not content:
        return {"category": category, "news": [], "status": "error", "error": "获取失败"}

    try:
        data = json.loads(content)
        list_data = data.get("data", {}).get("list", [])
        news_items = []

        for item in list_data[:count]:
            news_items.append({
                "id": item.get("notice_id", ""),
                "title": item.get("title", ""),
                "time": item.get("notice_date", ""),
                "symbol": item.get("secu_fullcode", ""),
                "exchange": item.get("exchange", ""),
                "summary": item.get("summary", ""),
                "art_url": f"https://data.eastmoney.com/notices/detail/{item.get('notice_id', '')}.html"
            })

        return {
            "category": category,
            "count": len(news_items),
            "news": news_items,
            "status": "ok",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {"category": category, "news": [], "status": "error", "error": str(e)}


def get_stock_news(symbol: str, from_date: str = None, to_date: str = None, count: int = 20) -> Dict[str, Any]:
    """
    获取个股新闻/公告
    Finnhub-equivalent: /company-news
    """
    # 标准化代码
    s = symbol.strip().upper()
    if len(s) == 6:
        if s.startswith("6"):
            full_code = "sh" + s
        elif s.startswith(("0", "3")):
            full_code = "sz" + s
        else:
            full_code = s
    else:
        full_code = s

    # 东方财富个股资讯
    url = f"http://push2.eastmoney.com/api/qt/clist/get?fid=f3&op=1&pn=1&np=1&fltt=2&invt=2&cb=jQuery&page={count}&_=1&newsType=&ntype=&ut=1&fields=1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31,32,33,34,35,36,37,38,39,40,41,42,43,44&keyword={full_code}"

    content = fetch(url)
    if not content:
        return {"symbol": symbol, "news": [], "status": "error", "error": "获取失败"}

    try:
        # 提取JSON
        m = re.search(r'jQuery\((.+)\)', content)
        if m:
            data = json.loads(m.group(1))
            diff = data.get("data", {}).get("diff", [])
        else:
            diff = []

        news_items = []
        for item in (diff[:count] if diff else []):
            news_items.append({
                "id": item.get("id", ""),
                "title": item.get("title", ""),
                "time": item.get("datetime", ""),
                "summary": item.get("digest", ""),
                "source": item.get("media", "")
            })

        return {
            "symbol": symbol,
            "count": len(news_items),
            "news": news_items,
            "status": "ok"
        }
    except Exception as e:
        return {"symbol": symbol, "news": [], "status": "error", "error": str(e)}


def get_news_sentiment(symbol: str) -> Dict[str, Any]:
    """
    新闻情绪分析（简化版）
    Finnhub-equivalent: /news-sentiment
    通过近7天新闻标题关键词打分
    """
    # 获取近7天新闻
    news_data = get_stock_news(symbol, count=30)
    articles = news_data.get("news", [])

    if not articles:
        return {
            "symbol": symbol,
            "sentiment_score": 0,
            "label": "中性",
            "buzz": 0,
            "articles": 0,
            "status": "ok"
        }

    # 情绪关键词
    positive_words = ["涨停", "大涨", "看好", "买入", "增持", "超预期", "突破", "爆发",
                      "爆发", "领涨", "创新高", "净利润", "增长", "业绩", "中标", "合作"]
    negative_words = ["跌停", "大跌", "亏损", "减持", "预警", "风险", "调查", "造假",
                      "涉嫌", "违规", "减持", "业绩下滑", "商誉", "质押", "诉讼"]
    neutral_words = ["公告", "会议", "决议", "公告", "通知", "变更", "说明"]

    scores = []
    for item in articles:
        title = item.get("title", "")
        score = 0
        for pw in positive_words:
            if pw in title:
                score += 1
        for nw in negative_words:
            if nw in title:
                score -= 1

        scores.append(score)

    avg_score = sum(scores) / len(scores) if scores else 0

    # 归一化到 -1 到 1
    sentiment_score = max(-1, min(1, avg_score / 3))

    if sentiment_score > 0.3:
        label = "看涨"
    elif sentiment_score < -0.3:
        label = "看跌"
    else:
        label = "中性"

    # 热度指数：新闻数量 * |sentiment_score|
    buzz = len([s for s in scores if s != 0])

    return {
        "symbol": symbol,
        "sentiment_score": round(sentiment_score, 3),
        "sentiment_label": label,
        "buzz": buzz,
        "article_count": len(articles),
        "positive_signals": len([s for s in scores if s > 0]),
        "negative_signals": len([s for s in scores if s < 0]),
        "top_positive": [item["title"] for item in articles[:3] if positive_words[0] in item.get("title", "")],
        "status": "ok"
    }


def get_market_briefing() -> Dict[str, Any]:
    """
    每日市场简报：综合盘面+板块+资金
    Pipeline 模式标准输出
    """
    try:
        from .quote import get_quote
        from .finance import get_index

        indices = get_index()
        index_data = indices.get("data", {})

        news = get_market_news("general", 10)
        latest_news = news.get("news", [])[:5]

        return {
            "title": f"市场简报 {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            "indices": index_data,
            "top_news": latest_news,
            "market_status": _get_market_status(),
            "status": "ok"
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


def _get_market_status() -> str:
    now = datetime.now()
    h = now.hour
    w = now.weekday()
    if w >= 5:
        return "周末休市"
    elif 9 <= h < 11 or 13 <= h < 15:
        return "盘中"
    elif 9 <= h < 9.3 or 13 <= h < 13.3:
        return "集合竞价"
    elif 15 <= h < 18:
        return "盘后"
    elif h < 9:
        return "开盘前"
    else:
        return "已休市"
