# =====================================================
# 🌐 APRIL WEB SEARCH SYSTEM
# =====================================================

"""
REAL INTERNET EXECUTION LAYER

Этот модуль:
- НЕ roleplay;
- НЕ hallucination layer;
- НЕ formatter;
- НЕ отвечает пользователю напрямую.

Он:
- выполняет реальный web search;
- валидирует ссылки;
- проверяет существование URL;
- извлекает verified links;
- помогает April работать с интернетом честно.

Главная цель:
НЕ выдумывать ссылки.
"""

# =====================================================
# 🔥 IMPORTS
# =====================================================

import requests
import re

from bs4 import BeautifulSoup
from urllib.parse import quote


# =====================================================
# 🌐 CONFIG
# =====================================================

HEADERS = {

    "User-Agent": (
        "Mozilla/5.0 "
        "(Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 "
        "(KHTML, like Gecko) "
        "Chrome/122.0 Safari/537.36"
    )
}

SEARCH_TIMEOUT = 10

MAX_RESULTS = 5


# =====================================================
# 🌐 REALTIME TRANSPORT KEYWORDS
# =====================================================

TRANSPORT_KEYWORDS = [

    "самолет",
    "рейс",
    "flight",
    "airbus",
    "boeing",

    "корабль",
    "судно",
    "лайнер",
    "ship",

    "поезд",
    "train",

    "автобус",
    "bus",

    "маршрут",
    "route",

    "где я",
    "где сейчас",
    "tracking",
    "live"
]


# =====================================================
# 🌐 GEO KEYWORDS
# =====================================================

GEO_KEYWORDS = [

    "страна",
    "город",
    "локация",
    "местоположение",
    "координаты",
    "карта",
    "map",
    "gps"
]


# =====================================================
# 🌐 SAFE REQUEST
# =====================================================

def safe_request(url: str):

    try:

        response = requests.get(

            url,

            headers=HEADERS,

            timeout=SEARCH_TIMEOUT
        )

        if response.status_code == 200:

            return response.text

    except Exception as e:

        print(
            "WEB REQUEST ERROR:",
            e
        )

    return None


# =====================================================
# 🌐 URL VALIDATION
# =====================================================

def validate_url(url: str):

    try:

        response = requests.head(

            url,

            headers=HEADERS,

            timeout=5,

            allow_redirects=True
        )

        return response.status_code < 400

    except:

        return False


# =====================================================
# 🌐 EXTRACT LINKS
# =====================================================

def extract_links(html: str):

    if not html:

        return []

    soup = BeautifulSoup(
        html,
        "html.parser"
    )

    results = []

    for a in soup.find_all(
        "a",
        href=True
    ):

        href = a["href"]

        if href.startswith(
            "http"
        ):

            results.append(href)

    return list(set(results))


# =====================================================
# 🌐 FILTER SOCIAL LINKS
# =====================================================

def filter_platform_links(
    links: list
):

    allowed = [

        "youtube.com",
        "youtu.be",

        "t.me",
        "telegram.me",

        "instagram.com",
        "facebook.com",

        "x.com",
        "twitter.com",

        "github.com",

        "linkedin.com",

        "reddit.com",

        "tiktok.com",

        # =============================================
        # 🌐 NEW
        # =============================================

        "flightradar24.com",

        "marinetraffic.com",

        "vesselfinder.com",

        "flightaware.com",

        "airnavradar.com",

        "google.com/maps",

        "openstreetmap.org"
    ]

    filtered = []

    for link in links:

        for platform in allowed:

            if platform in link:

                filtered.append(
                    link
                )

                break

    return list(set(filtered))


# =====================================================
# 🌐 DETECT LIVE INTENT
# =====================================================

def detect_live_lookup_intent(
    query: str
):

    query = (
        query or ""
    ).lower()

    for keyword in (
        TRANSPORT_KEYWORDS
        + GEO_KEYWORDS
    ):

        if keyword in query:

            return True

    return False


# =====================================================
# 🌐 BUILD SMART SEARCH QUERY
# =====================================================

def build_search_query(
    query: str
):

    query = (
        query or ""
    ).strip()

    lower = query.lower()

    # =============================================
    # ✈️ FLIGHTS
    # =============================================

    if any(

        x in lower

        for x in [

            "рейс",
            "flight",
            "самолет"
        ]
    ):

        return (
            query
            + " flightradar24"
        )

    # =============================================
    # 🚢 SHIPS
    # =============================================

    if any(

        x in lower

        for x in [

            "судно",
            "корабль",
            "ship"
        ]
    ):

        return (
            query
            + " marinetraffic"
        )

    # =============================================
    # 🗺 MAPS
    # =============================================

    if any(

        x in lower

        for x in [

            "карта",
            "локация",
            "координаты"
        ]
    ):

        return (
            query
            + " map"
        )

    return query


# =====================================================
# 🌐 SEARCH WEB
# =====================================================

def search_web(
    query: str
):

    query = (
        query or ""
    ).strip()

    if not query:

        return {

            "success": False,

            "results": []
        }

    try:

        smart_query = (
            build_search_query(
                query
            )
        )

        encoded = quote(
            smart_query
        )

        url = (
            f"https://duckduckgo.com/html/?q={encoded}"
        )

        html = safe_request(
            url
        )

        if not html:

            return {

                "success": False,

                "results": []
            }

        links = extract_links(
            html
        )

        links = (
            filter_platform_links(
                links
            )
        )

        verified = []

        for link in links[:MAX_RESULTS]:

            if validate_url(link):

                verified.append({

                    "url": link,

                    "verified": True,

                    "live_related":
                        detect_live_lookup_intent(
                            query
                        )
                })

        return {

            "success": True,

            "results": verified,

            "live_intent":
                detect_live_lookup_intent(
                    query
                )
        }

    except Exception as e:

        print(
            "SEARCH WEB ERROR:",
            e
        )

        return {

            "success": False,

            "results": []
        }


# =====================================================
# 🌐 BUILD SEARCH SUMMARY
# =====================================================

def build_search_summary(
    results: dict
):

    if not results:

        return ""

    if not results.get(
        "success"
    ):

        return ""

    links = results.get(
        "results",
        []
    )

    if not links:

        return (
            "Ничего подтверждённого "
            "найти не удалось."
        )

    lines = []

    # =================================================
    # 🌐 LIVE CONTEXT
    # =================================================

    if results.get(
        "live_intent"
    ):

        lines.append(
            "🌍 Найдены live/realtime источники:"
        )

    for item in links:

        url = item.get(
            "url",
            ""
        )

        if url:

            lines.append(
                f"• {url}"
            )

    return "\n".join(lines)
