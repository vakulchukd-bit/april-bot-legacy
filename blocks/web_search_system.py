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

MAX_RESULTS = 7


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

    "такси",
    "taxi",

    "метро",

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
    "gps",

    "рядом",
    "поблизости",
    "nearby",

    "улица",
    "адрес",

    "аэропорт",
    "вокзал",
    "порт"
]


# =====================================================
# 🌐 TRAVEL / SURVIVAL KEYWORDS
# =====================================================

TRAVEL_SUPPORT_KEYWORDS = [

    "билет",
    "купить билет",
    "где купить",

    "отель",
    "гостиница",
    "хостел",

    "еда",
    "ресторан",
    "кафе",

    "банкомат",
    "обмен валют",

    "аптека",
    "больница",

    "туалет",

    "зарядка",
    "wifi",
    "сим карта",

    "полиция",
    "экстренно",

    "какой валютой",
    "чем платить",

    "сколько стоит",

    "как добраться",

    "маршрут"
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
# 🌐 FILTER PLATFORM LINKS
# =====================================================

def filter_platform_links(
    links: list
):

    allowed = [

        # =============================================
        # 🌐 SOCIAL / MEDIA
        # =============================================

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
        # ✈️ FLIGHTS
        # =============================================

        "flightradar24.com",

        "flightaware.com",

        "airnavradar.com",

        # =============================================
        # 🚢 SHIPS
        # =============================================

        "marinetraffic.com",

        "vesselfinder.com",

        # =============================================
        # 🗺 MAPS
        # =============================================

        "google.com/maps",

        "openstreetmap.org",

        # =============================================
        # 🚌 TRAVEL
        # =============================================

        "booking.com",

        "airbnb.com",

        "tripadvisor.com",

        "rome2rio.com",

        "kayak.com",

        "skyscanner.com",

        "omio.com",

        "12go.asia",

        "uber.com",

        "bolt.eu",

        "blaBlaCar",

        # =============================================
        # 🌍 SERVICES
        # =============================================

        "google.com",

        "apple.com/maps"
    ]

    filtered = []

    for link in links:

        for platform in allowed:

            if platform.lower() in link.lower():

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

    all_keywords = (

        TRANSPORT_KEYWORDS
        + GEO_KEYWORDS
        + TRAVEL_SUPPORT_KEYWORDS
    )

    for keyword in all_keywords:

        if keyword in query:

            return True

    return False


# =====================================================
# 🌐 DETECT NEED TYPE
# =====================================================

def detect_support_category(
    query: str
):

    q = (
        query or ""
    ).lower()

    # =============================================
    # ✈️ TRANSPORT
    # =============================================

    if any(

        x in q

        for x in [

            "рейс",
            "самолет",
            "поезд",
            "автобус",
            "такси",
            "метро",
            "корабль"
        ]
    ):

        return "transport"

    # =============================================
    # 🏨 HOTELS
    # =============================================

    if any(

        x in q

        for x in [

            "отель",
            "гостиница",
            "хостел"
        ]
    ):

        return "hotel"

    # =============================================
    # 🍔 FOOD
    # =============================================

    if any(

        x in q

        for x in [

            "еда",
            "ресторан",
            "кафе"
        ]
    ):

        return "food"

    # =============================================
    # 💳 MONEY
    # =============================================

    if any(

        x in q

        for x in [

            "валюта",
            "обмен",
            "банкомат",
            "чем платить"
        ]
    ):

        return "money"

    # =============================================
    # 🚨 EMERGENCY
    # =============================================

    if any(

        x in q

        for x in [

            "экстренно",
            "больница",
            "аптека",
            "полиция"
        ]
    ):

        return "emergency"

    return "general"


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
            + " google maps"
        )

    # =============================================
    # 🏨 HOTELS
    # =============================================

    if any(

        x in lower

        for x in [

            "отель",
            "гостиница",
            "хостел"
        ]
    ):

        return (
            query
            + " booking"
        )

    # =============================================
    # 🍔 FOOD
    # =============================================

    if any(

        x in lower

        for x in [

            "еда",
            "ресторан",
            "кафе"
        ]
    ):

        return (
            query
            + " nearby food"
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

        support_category = (
            detect_support_category(
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
                        ),

                    "support_category":
                        support_category
                })

        return {

            "success": True,

            "results": verified,

            "live_intent":
                detect_live_lookup_intent(
                    query
                ),

            "support_category":
                support_category
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
    # 🌍 LIVE CONTEXT
    # =================================================

    if results.get(
        "live_intent"
    ):

        lines.append(
            "🌍 Найдены live/realtime источники:"
        )

    # =================================================
    # 🧠 SUPPORT CATEGORY
    # =================================================

    category = results.get(
        "support_category",
        "general"
    )

    if category == "transport":

        lines.append(
            "🚌 Найдены транспортные сервисы:"
        )

    elif category == "hotel":

        lines.append(
            "🏨 Найдены сервисы жилья:"
        )

    elif category == "food":

        lines.append(
            "🍔 Найдены сервисы еды:"
        )

    elif category == "money":

        lines.append(
            "💳 Найдены финансовые сервисы:"
        )

    elif category == "emergency":

        lines.append(
            "🚨 Найдены emergency сервисы:"
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
