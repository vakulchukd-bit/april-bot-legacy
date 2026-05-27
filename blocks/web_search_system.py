# =====================================================
# 🌐 APRIL WEB SEARCH SYSTEM
# =====================================================

"""
APRIL WEB EXECUTION LAYER

ROLE:
- real internet execution;
- verified web access;
- safe realtime lookup;
- structured web transport;
- provider-safe internet support.

NOT ROLE:
- orchestration;
- semantic authority;
- hallucination;
- dialogue generation;
- trigger routing;
- renderer ownership.

APRIL WEB PRINCIPLES:

1. semantic decides
2. web layer executes
3. links must be verified
4. no fake internet
5. no keyword authority
6. structured transport only
7. continuity-safe execution
8. predictable routing
9. renderer-safe behavior
10. calm internet assistance
"""

# =====================================================
# 🔥 IMPORTS
# =====================================================

import re
import requests

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

MAX_LINKS_EXTRACT = 40


# =====================================================
# 🌐 SAFE HELPERS
# =====================================================

def normalize(
    text
):

    return str(
        text or ""
    ).strip()


def normalize_lower(
    text
):

    return normalize(
        text
    ).lower()


def clamp(
    value,
    minimum=0.0,
    maximum=1.0
):

    if value < minimum:
        return minimum

    if value > maximum:
        return maximum

    return value


def contains_any(
    text,
    words
):

    return any(
        word in text
        for word in words
    )


# =====================================================
# 🌐 PLATFORM MAP
# =====================================================

SUPPORTED_PLATFORMS = {

    # =================================================
    # 🌍 SOCIAL
    # =====================================================

    "youtube": [

        "youtube.com",
        "youtu.be"
    ],

    "telegram": [

        "t.me",
        "telegram.me"
    ],

    "github": [

        "github.com"
    ],

    "reddit": [

        "reddit.com"
    ],

    # =================================================
    # ✈️ TRANSPORT
    # =====================================================

    "flight": [

        "flightradar24.com",
        "flightaware.com"
    ],

    "ship": [

        "marinetraffic.com",
        "vesselfinder.com"
    ],

    # =================================================
    # 🗺 MAPS
    # =====================================================

    "maps": [

        "google.com/maps",
        "openstreetmap.org",
        "apple.com/maps"
    ],

    # =================================================
    # 🏨 TRAVEL
    # =====================================================

    "travel": [

        "booking.com",
        "airbnb.com",
        "tripadvisor.com",
        "rome2rio.com",
        "kayak.com",
        "skyscanner.com",
        "omio.com",
        "12go.asia"
    ]
}


# =====================================================
# 🌐 SAFE REQUEST
# =====================================================

def safe_request(
    url: str
):

    try:

        response = requests.get(

            url,

            headers=HEADERS,

            timeout=SEARCH_TIMEOUT
        )

        if response.status_code == 200:

            return {

                "success": True,

                "status_code":
                    response.status_code,

                "html":
                    response.text
            }

        return {

            "success": False,

            "status_code":
                response.status_code,

            "html": None
        }

    except Exception as e:

        print(
            "WEB REQUEST ERROR:",
            e
        )

        return {

            "success": False,

            "status_code": None,

            "html": None
        }


# =====================================================
# 🌐 URL VALIDATION
# =====================================================

def validate_url(
    url: str
):

    try:

        response = requests.head(

            url,

            headers=HEADERS,

            timeout=5,

            allow_redirects=True
        )

        return {

            "valid":
                response.status_code < 400,

            "status_code":
                response.status_code
        }

    except Exception as e:

        print(
            "VALIDATION ERROR:",
            e
        )

        return {

            "valid": False,

            "status_code": None
        }


# =====================================================
# 🌐 EXTRACT LINKS
# =====================================================

def extract_links(
    html: str
):

    if not html:

        return []

    try:

        soup = BeautifulSoup(

            html,
            "html.parser"
        )

        links = []

        for a in soup.find_all(
            "a",
            href=True
        ):

            href = str(
                a["href"]
            ).strip()

            if not href.startswith(
                "http"
            ):

                continue

            links.append(href)

        unique = list(
            dict.fromkeys(
                links
            )
        )

        return unique[
            :MAX_LINKS_EXTRACT
        ]

    except Exception as e:

        print(
            "LINK EXTRACT ERROR:",
            e
        )

        return []


# =====================================================
# 🌐 PLATFORM DETECTION
# =====================================================

def detect_platform(
    url: str
):

    lower = normalize_lower(
        url
    )

    for platform, domains in (

        SUPPORTED_PLATFORMS.items()
    ):

        for domain in domains:

            if domain in lower:

                return platform

    return "generic"


# =====================================================
# 🌐 FILTER SAFE LINKS
# =====================================================

def filter_links(
    links: list
):

    filtered = []

    for link in links:

        platform = detect_platform(
            link
        )

        if platform != "generic":

            filtered.append({

                "url": link,

                "platform":
                    platform
            })

    return filtered


# =====================================================
# 🌐 WEB INTENT DETECTION
# =====================================================

def detect_web_context(
    semantic: dict,
    cognition: dict,
    reasoning: dict,
    query: str
):

    result = {

        "internet_needed": False,

        "realtime": False,

        "geo": False,

        "travel": False,

        "renderer_safe": True,

        "provider_safe": True,

        "source": "semantic"
    }

    # =================================================
    # 🔥 SEMANTIC
    # =====================================================

    if semantic.get(
        "internet_context_needed"
    ):

        result[
            "internet_needed"
        ] = True

    if semantic.get(
        "realtime_context"
    ):

        result[
            "realtime"
        ] = True

    if semantic.get(
        "geo_context"
    ):

        result[
            "geo"
        ] = True

    if semantic.get(
        "travel_context"
    ):

        result[
            "travel"
        ] = True

    # =================================================
    # 🔥 COGNITION
    # =====================================================

    if cognition.get(
        "internet_context_needed"
    ):

        result[
            "internet_needed"
        ] = True

    # =================================================
    # 🔥 SAFE FALLBACK
    # =====================================================

    lower = normalize_lower(
        query
    )

    weak_geo_words = [

        "карта",
        "маршрут",
        "рейс",
        "отель",
        "поезд"
    ]

    if (

        not result[
            "internet_needed"
        ]

        and contains_any(
            lower,
            weak_geo_words
        )
    ):

        result[
            "internet_needed"
        ] = True

        result[
            "geo"
        ] = True

        result[
            "source"
        ] = "fallback"

    return result


# =====================================================
# 🌐 SEARCH CATEGORY
# =====================================================

def detect_search_category(
    query: str,
    web_context: dict
):

    lower = normalize_lower(
        query
    )

    if web_context.get(
        "realtime"
    ):

        return "realtime"

    if web_context.get(
        "travel"
    ):

        return "travel"

    if web_context.get(
        "geo"
    ):

        return "geo"

    if contains_any(

        lower,

        [
            "github",
            "repository",
            "repo"
        ]
    ):

        return "developer"

    return "general"


# =====================================================
# 🌐 BUILD SEARCH QUERY
# =====================================================

def build_search_query(
    query: str,
    category: str
):

    query = normalize(
        query
    )

    if category == "realtime":

        return (
            query
            + " realtime live"
        )

    if category == "travel":

        return (
            query
            + " booking maps route"
        )

    if category == "geo":

        return (
            query
            + " maps location"
        )

    if category == "developer":

        return (
            query
            + " github"
        )

    return query


# =====================================================
# 🌐 STRUCTURED RESULT
# =====================================================

def build_result_item(
    url,
    validation,
    category
):

    return {

        "url": url,

        "verified":
            validation.get(
                "valid",
                False
            ),

        "status_code":
            validation.get(
                "status_code"
            ),

        "platform":
            detect_platform(
                url
            ),

        "category":
            category,

        "provider_safe": True,

        "renderer_safe": True,

        "hallucination_safe": True
    }


# =====================================================
# 🌐 SEARCH WEB
# =====================================================

def search_web(
    query: str,
    semantic: dict = None,
    cognition: dict = None,
    reasoning: dict = None
):

    semantic = semantic or {}

    cognition = cognition or {}

    reasoning = reasoning or {}

    query = normalize(
        query
    )

    if not query:

        return {

            "success": False,

            "results": [],

            "reason":
                "empty_query"
        }

    try:

        # =================================================
        # 🌐 MACHINE CONTEXT
        # =====================================================

        web_context = detect_web_context(

            semantic,
            cognition,
            reasoning,
            query
        )

        category = detect_search_category(

            query,
            web_context
        )

        smart_query = build_search_query(

            query,
            category
        )

        encoded = quote(
            smart_query
        )

        url = (

            "https://duckduckgo.com/html/?q="
            + encoded
        )

        request_result = safe_request(
            url
        )

        if not request_result.get(
            "success"
        ):

            return {

                "success": False,

                "results": [],

                "reason":
                    "request_failed",

                "web_context":
                    web_context
            }

        html = request_result.get(
            "html"
        )

        links = extract_links(
            html
        )

        links = filter_links(
            links
        )

        verified = []

        for item in links[:MAX_RESULTS]:

            link = item.get(
                "url"
            )

            validation = validate_url(
                link
            )

            if validation.get(
                "valid"
            ):

                verified.append(

                    build_result_item(

                        link,
                        validation,
                        category
                    )
                )

        return {

            "success": True,

            "results": verified,

            "query":
                smart_query,

            "category":
                category,

            "web_context":
                web_context,

            "provider_safe": True,

            "renderer_safe": True,

            "continuity_safe": True
        }

    except Exception as e:

        print(
            "SEARCH WEB ERROR:",
            e
        )

        return {

            "success": False,

            "results": [],

            "reason":
                str(e)
        }


# =====================================================
# 🌐 BUILD SUMMARY
# =====================================================

def build_search_summary(
    results: dict
):

    if not results:

        return ""

    if not results.get(
        "success"
    ):

        return (
            "Не удалось получить "
            "подтверждённые web results."
        )

    links = results.get(
        "results",
        []
    )

    if not links:

        return (
            "Подтверждённые ссылки "
            "не найдены."
        )

    lines = []

    category = results.get(
        "category",
        "general"
    )

    # =================================================
    # 🌐 CATEGORY
    # =====================================================

    category_titles = {

        "realtime":
            "🌍 Realtime web sources:",

        "travel":
            "✈️ Travel sources:",

        "geo":
            "🗺 Geo sources:",

        "developer":
            "💻 Developer sources:",

        "general":
            "🌐 Verified sources:"
    }

    lines.append(

        category_titles.get(
            category,
            "🌐 Sources:"
        )
    )

    # =================================================
    # 🌐 LINKS
    # =====================================================

    for item in links:

        url = item.get(
            "url",
            ""
        )

        platform = item.get(
            "platform",
            "generic"
        )

        if url:

            lines.append(

                f"• [{platform}] {url}"
            )

    return "\n".join(lines)


# =====================================================
# 🌐 LEGACY COMPATIBILITY
# =====================================================

def detect_live_lookup_intent(
    query: str
):

    """
    Legacy compatibility wrapper.

    Старые модули могут вызывать
    detect_live_lookup_intent().

    Wrapper сохранён
    для DeepHub stability.
    """

    query = normalize_lower(
        query
    )

    weak_live_words = [

        "рейс",
        "flight",
        "карта",
        "маршрут",
        "отель",
        "поезд",
        "метро",
        "такси",
        "где находится",
        "локация"
    ]

    return contains_any(
        query,
        weak_live_words
    )
