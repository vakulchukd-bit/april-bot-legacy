"""C.World — request-scoped routing, places search and real map artifacts.

The room never fabricates streets or turn-by-turn directions. It requests real
Routes/Places data with a server-restricted key, then lets GalleryBlock load a
Static Maps image directly from Google using a separate browser-restricted key.
Provider map content is not downloaded, cached, or persisted by this service.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import re
import urllib.parse
import urllib.request
from typing import Any, Dict, Optional

from blocks.C_ARTIFACT_CONTRACT import (
    MachineRequest,
    MachineResponse,
    add_room_contribution,
    create_artifact,
)

ROOM_ID = "C_WORLD_ROOM"
GOOGLE_API_KEY_ENV_NAMES = ("APRIL_GOOGLE_MAPS_API_KEY", "GOOGLE_MAPS_API_KEY")
STATIC_MAPS_BROWSER_KEY_ENV_NAMES = ("APRIL_GOOGLE_STATIC_MAPS_BROWSER_KEY",)
STATIC_MAPS_SIGNING_SECRET_ENV = "APRIL_GOOGLE_STATIC_MAPS_URL_SIGNING_SECRET"
ROUTES_ENDPOINT = "https://routes.googleapis.com/directions/v2:computeRoutes"
STATIC_MAPS_ENDPOINT = "https://maps.googleapis.com/maps/api/staticmap"
PLACES_ENDPOINT = "https://places.googleapis.com/v1/places:searchText"

_ROUTE_WORDS = (
    "маршрут", "путь", "проезд", "пройти", "проехать", "добраться", "как попасть",
    "directions", "route", "get to", "get there", "how do i get", "how to get",
    "navigate", "navigation", "show me the way", "map route",
    "карту проезда", "карту маршрута", "этот маршрут",
    "this route", "this journey", "that route",
)
_PLACE_WORDS = (
    "ресторан", "рестораны", "кафе", "бар", "бары", "паб", "пабы", "кофейня",
    "кофейни", "restaurant", "restaurants", "bar", "bars", "pub", "cafe", "cafes",
    "coffee shop", "places near", "nearby places", "рядом со мной", "поблизости",
)
_FOLLOWUP_WORDS = (
    "этот маршрут", "тот маршрут", "этот путь", "этот проезд", "сделай этот",
    "покажи его", "на карте изображением", "this route", "that route", "this journey",
    "make this route", "show it on the map", "same route",
    # A route link is part of the same active navigation task. These phrases
    # must restore the previous USER route request even when State Manager
    # classifies the short correction as a new topic.
    "где ссылка", "где ссылку", "ссылку не дал", "ты ссылку не дал",
    "нету ссылки", "нет ссылки", "ссылка пропала", "ссылка исчезла",
    "ссылка не отображается", "ссылку не видно", "повтори ссылку",
    "пришли ссылку еще раз", "where is the link", "no link", "link is missing",
    "link disappeared", "link is not showing",
)

_STREET_TYPE_RE = (
    r"(?:улиц[аеиуы]|ул\.?|проспект[ае]?|просп\.?|пр-т|"
    r"площад[ьи]|пл\.?|переулк[еа]?|пер\.?|бульвар[е]?|бул\.?|"
    r"шоссе|набережн[аяе]|проезд[е]?)"
)

_ROUTE_DESTINATION_ACTION_RE = re.compile(
    r"\b(?:надо|нужно|необходимо|хочу|мне\s+бы)?\s*"
    r"(?:пройти|дойти|добраться|попасть|доехать|направиться|поехать|идти|ехать)"
    r"\s+(?:к|ко|до|в|во|на|по|в\s+сторону)\b|"
    r"\bкак\s+(?:мне\s+)?(?:к\s+нему\s+|туда\s+)?"
    r"(?:пройти|дойти|добраться|попасть|доехать)\b",
    re.IGNORECASE,
)
_ROUTE_LINK_REPAIR_RE = re.compile(
    r"(?:где.{0,35}ссылк\w*|ссылк\w*.{0,45}(?:не\s+дал|не\s+вид|пропад\w*|исчез\w*|не\s+появ|не\s+отображ)|"
    r"(?:нет|нету)\s+ссылк\w*|повтор\w*.{0,25}ссылк\w*|ссылк\w*.{0,25}повтор|"
    r"where.{0,35}link|no\s+link|link.{0,35}(?:missing|disappeared|not\s+showing))",
    re.IGNORECASE | re.DOTALL,
)


def _text(value: Any) -> str:
    return str(value or "").strip()


def _normalize(value: Any) -> str:
    return re.sub(r"\s+", " ", _text(value).replace("ё", "е")).strip()


def _current_query(request: Any) -> str:
    conversation = getattr(request, "conversation", {})
    if isinstance(request, dict):
        conversation = request.get("conversation") if isinstance(request.get("conversation"), dict) else {}
    if isinstance(conversation, dict):
        for key in ("current_request", "resolved_request", "current_text", "query", "user_message"):
            value = _text(conversation.get(key))
            if value:
                return value[:1600]
    return _text(getattr(request, "goal", ""))[:1600]


def _selected_user_requests(request: Any) -> list[str]:
    memory = getattr(request, "memory", {})
    routing = getattr(request, "routing", {})
    if isinstance(request, dict):
        memory = request.get("memory") if isinstance(request.get("memory"), dict) else {}
        routing = request.get("routing") if isinstance(request.get("routing"), dict) else {}
    pairs: list[Any] = []
    if isinstance(memory, dict):
        pairs.extend(memory.get("selected_pairs") or [])
        pairs.extend(memory.get("recent_exchange_window") or [])
    if isinstance(routing, dict):
        plan = routing.get("provider_context_plan") if isinstance(routing.get("provider_context_plan"), dict) else {}
        pairs.extend(plan.get("selected_dialogue_chain") or [])
    result: list[str] = []
    seen: set[str] = set()
    for pair in reversed(pairs):
        if not isinstance(pair, dict):
            continue
        # Read user-side text only. Prior assistant responses are never valid
        # sources for route endpoints; this prevents stale answer contamination.
        candidate = _normalize(pair.get("user") or pair.get("user_text") or pair.get("user_request") or pair.get("request") or pair.get("input"))
        if candidate and candidate not in seen:
            seen.add(candidate)
            result.append(candidate[:1600])
    return result


def _extract_city(text: str) -> str:
    """Resolve only an explicitly named, supported city; never infer GPS/IP."""
    city_patterns = (
        (r"\b(одесса|одессе|одеси|odesa|odessa)\b", "Odesa, Ukraine"),
        (r"\b(киев|києві|kyiv|kiev)\b", "Kyiv, Ukraine"),
        (r"\b(львов|львів|lviv)\b", "Lviv, Ukraine"),
        (r"\b(харьков|харків|kharkiv)\b", "Kharkiv, Ukraine"),
        (r"\b(днепр|дніпро|dnipro)\b", "Dnipro, Ukraine"),
        (r"\b(запорожье|запоріжжя|zaporizhzhia|zaporozhye)\b", "Zaporizhzhia, Ukraine"),
        (r"\b(николаев|миколаїв|mykolaiv|nikolaev)\b", "Mykolaiv, Ukraine"),
        (r"\b(черновцы|чернівці|chernivtsi)\b", "Chernivtsi, Ukraine"),
        (r"\b(винница|вінниця|vinnytsia)\b", "Vinnytsia, Ukraine"),
        (r"\b(луцк|луцьк|lutsk)\b", "Lutsk, Ukraine"),
        (r"\b(ужгород|uzhhorod)\b", "Uzhhorod, Ukraine"),
        (r"\b(варшава|warsaw|warszawa)\b", "Warsaw, Poland"),
        (r"\b(краков|краків|krakow|kraków)\b", "Krakow, Poland"),
        (r"\b(прага|prague|praha)\b", "Prague, Czechia"),
        (r"\b(берлин|берлін|berlin)\b", "Berlin, Germany"),
        (r"\b(лондон|london)\b", "London, United Kingdom"),
        (r"\b(париж|paris)\b", "Paris, France"),
        (r"\b(рим|rome|roma)\b", "Rome, Italy"),
        (r"\b(мадрид|madrid)\b", "Madrid, Spain"),
        (r"\b(барселона|barcelona)\b", "Barcelona, Spain"),
        (r"\b(стамбул|истанбул|istanbul)\b", "Istanbul, Turkey"),
        (r"\b(вена|vienna|wien)\b", "Vienna, Austria"),
        (r"\b(бухарест|bucharest|bucurești)\b", "Bucharest, Romania"),
        (r"\b(кишинев|кишинів|chisinau|chișinău)\b", "Chisinau, Moldova"),
        (r"\b(амстердам|amsterdam)\b", "Amsterdam, Netherlands"),
        (r"\b(лиссабон|lisbon|lisboa)\b", "Lisbon, Portugal"),
        (r"\b(афины|атени|athens)\b", "Athens, Greece"),
        (r"\b(будапешт|budapest)\b", "Budapest, Hungary"),
        (r"\b(софия|sofia)\b", "Sofia, Bulgaria"),
        (r"\b(нью-йорк|new york)\b", "New York, NY, USA"),
        (r"\b(торонто|toronto)\b", "Toronto, Canada"),
        (r"\b(дубай|dubai)\b", "Dubai, United Arab Emirates"),
        (r"\b(токио|tokyo)\b", "Tokyo, Japan"),
    )
    lowered = _normalize(text).lower()
    for pattern, canonical in city_patterns:
        if re.search(pattern, lowered, re.IGNORECASE):
            return canonical
    # Allow other explicitly named cities without relying on a fixed world-city
    # catalogue. The qualifier must be explicit ("in X", "в городе X", etc.);
    # words like "nearby" or "in the center" are not treated as a city.
    generic_location_patterns = (
        r"\b(?:в\s+городе|в\s+г\.?|городе|у\s+місті|місто|в|во|у|in|near)\s+([\w][\w'’.-]*(?:\s+[\w][\w'’.-]*){0,2})",
    )
    excluded_location_words = {
        "the", "a", "an", "city", "town", "center", "centre", "downtown",
        "центр", "центре", "центру", "район", "районе", "району", "область",
        "области", "поблизости", "рядом", "me", "here", "there", "nearby",
        "місті", "районі", "центрі", "поруч", "около", "возле",
    }
    generic_matches = list(re.finditer(generic_location_patterns[0], _normalize(text), re.IGNORECASE))
    for match in reversed(generic_matches):
        candidate = _normalize(match.group(1)).strip(" .,-").lower()
        first_word = candidate.split(" ", 1)[0].lower() if candidate else ""
        if candidate and first_word not in excluded_location_words and not first_word.isdigit():
            return candidate
    return ""


def _clean_endpoint(value: str) -> str:
    value = re.sub(r"^(?:пожалуйста\s+|будь ласка\s+|please\s+)", "", value.strip(), flags=re.I)
    value = re.sub(r"^(?:улиц[аеиы]?|ул\.?|вулиц[яі]?|вул\.?|адрес)\s+", "", value, flags=re.I)
    value = re.sub(r"\b(?:в\s+городе|в\s+г\.?|город|місто)\s*$", "", value, flags=re.I)
    value = re.sub(r"\s+(?:in|at|to|into|в|у|до)$", "", value, flags=re.I)
    value = re.sub(r"\s+", " ", value).strip(" \t\r\n,.;:!?()[]{}\"'«»")
    return value[:180]


def _extract_street_phrase(text: str) -> str:
    """Extract a user-stated street/address fragment without inventing a number."""
    source = _normalize(text)
    patterns = (
        rf"\b(?:на|по)\s+{_STREET_TYPE_RE}\s+(?P<value>[^.!?;]{{2,110}})",
        r"\bпо\s+адресу\s*[:：]?\s*(?P<value>[^.!?;]{2,110})",
    )
    for pattern in patterns:
        match = re.search(pattern, source, re.IGNORECASE)
        if not match:
            continue
        value = match.group("value")
        # Stop at the beginning of a new instruction or a relative clause, but
        # retain a comma followed by the street number (e.g. "Косвенная, 42").
        value = re.split(
            r"\s*,?\s*(?:котор\w*|где\s+(?:находится|расположен)|"
            r"а\s+мне\b|мне\s+(?:надо|нужно|необходимо)\b|"
            r"я\s+не\s+помню\b|можешь\s+мне\b|покажи\b|укажи\b|"
            r"как\s+(?:к|до|мне)\b|please\b|show\b|tell\s+me\b)",
            value,
            maxsplit=1,
            flags=re.IGNORECASE,
        )[0]
        value = re.sub(r"^\s*(?:улиц[аеиуы]|ул\.?|проспект[ае]?|просп\.?|пр-т|площад[ьи]|пл\.?)\s+", "", value, flags=re.I)
        value = _clean_endpoint(value)
        if value:
            return value
    return ""


def _extract_origin_from_natural_text(text: str) -> str:
    """Resolve an origin from statements such as 'я нахожусь ... на улице X'."""
    source = _normalize(text)
    anchor = re.search(
        r"\b(?:я\s+)?(?:сейчас\s+)?(?:нахожусь|стою|пребываю|расположен[ао]?|живу)\b"
        r"(?P<tail>[^.!?]{0,200})",
        source,
        re.IGNORECASE,
    )
    if anchor:
        origin = _extract_street_phrase(anchor.group("tail"))
        if origin:
            return origin

    # Also support concise location statements such as "я на улице X, 12".
    concise = re.search(
        rf"\bя\s+(?:сейчас\s+)?(?:стою\s+)?(?:на|по)\s+{_STREET_TYPE_RE}\s+(?P<value>[^.!?;]{{2,100}})",
        source,
        re.IGNORECASE,
    )
    if concise:
        value = _clean_endpoint(concise.group("value"))
        if value:
            return value
    return ""


def _normalize_destination_label(value: str) -> str:
    """Make common Russian place names searchable while preserving user facts."""
    label = _clean_endpoint(value)
    low = label.lower().replace("ё", "е")
    if re.search(r"\bцентральн\w*\s+автовокзал\w*\b", low):
        return "Центральный автовокзал"
    if re.search(r"\bглавн\w*\s+автовокзал\w*\b", low):
        return "Главный автовокзал"
    if re.search(r"\bавтовокзал\w*\b", low) and len(low.split()) <= 3:
        return "Автовокзал"
    return label


def _extract_destination_from_natural_text(text: str) -> str:
    """Resolve the destination from 'мне надо пройти к ...' constructions."""
    source = _normalize(text)
    match = _ROUTE_DESTINATION_ACTION_RE.search(source)
    if not match:
        return ""
    tail = source[match.end():].strip(" \t,.:;—-")
    if not tail:
        return ""

    # Keep the named destination, and also keep an explicitly supplied street
    # clause after phrases like "который находится на улице Колонтаевская".
    street = _extract_street_phrase(tail)
    place_part = re.split(
        r"\s*(?:,\s*)?(?:котор\w*|где\s+(?:находится|расположен)|"
        r"(?:котор\w*\s+)?(?:находится|расположен[ао]?)\s+на\s+улиц)",
        tail,
        maxsplit=1,
        flags=re.IGNORECASE,
    )[0]
    place_part = re.split(
        r"\s+(?:я\s+не\s+помню|можешь\s+мне|покажи|укажи|построй|проложи|"
        r"как\s+(?:к|до)|please|show\s+me|tell\s+me)\b",
        place_part,
        maxsplit=1,
        flags=re.IGNORECASE,
    )[0]
    place = _normalize_destination_label(place_part)
    if street:
        street_label = f"улица {street}"
        if place and street.lower() not in place.lower():
            return f"{place}, {street_label}"
        return street_label
    return place


def _parse_route(text: str) -> dict[str, Any]:
    city = _extract_city(text)
    normalized = _normalize(text)
    patterns = (
        r"(?:^|\s)(?:с|со|из|от|з|із|від|від|from)\s+(.+?)\s+(?:до|к|в|во|на|у|вiд|to|towards)\s+(.+?)\s*$",
        r"(?:^|\s)(?:от|from)\s+(.+?)\s+(?:до|to)\s+(.+?)\s*$",
    )
    match = None
    for pattern in patterns:
        match = re.search(pattern, normalized, re.IGNORECASE)
        if match:
            break

    if match:
        origin = _clean_endpoint(match.group(1))
        destination = _clean_endpoint(match.group(2))
        # Remove trailing city clauses and common request tails from destination.
        destination = re.split(r"\s+(?:в\s+городе|в\s+г\.?|городе|одессе|одесса|одеси|odesa|odessa)\b", destination, maxsplit=1, flags=re.I)[0]
        destination = re.split(r"\s+(?:покажи|нарисуй|сделай|построй|please|show|draw|make)\b", destination, maxsplit=1, flags=re.I)[0]
        origin = _clean_endpoint(origin)
        destination = _clean_endpoint(destination)
    else:
        origin = _extract_origin_from_natural_text(normalized)
        destination = _extract_destination_from_natural_text(normalized)

    if city:
        city_name = city.split(",", 1)[0]
        for endpoint_name in ("origin", "destination"):
            endpoint = origin if endpoint_name == "origin" else destination
            if endpoint and city_name.lower() not in endpoint.lower():
                endpoint = f"{endpoint}, {city}"
            if endpoint_name == "origin":
                origin = endpoint
            else:
                destination = endpoint
    # Never infer an origin from device/IP location. A route must have both
    # explicitly supplied endpoints before C.World can return a directions link.
    return {"origin": origin, "destination": destination, "city": city}


def _travel_mode(text: str) -> str:
    low = text.lower()
    if any(word in low for word in ("пешком", "пішки", "пройти", "дойти", "walk", "walking", "on foot")):
        return "WALK"
    if any(word in low for word in ("велосипед", "велосипедом", "bike", "bicycle", "cycling")):
        return "BICYCLE"
    if any(word in low for word in ("общественн", "автобус", "трамва", "троллейбус", "маршрутка", "транспорт", "transit", "bus", "train", "metro")):
        return "TRANSIT"
    return "DRIVE"


def _navigation_intent(text: str) -> tuple[bool, bool]:
    normalized = _normalize(text)
    low = normalized.lower()
    route_keyword = any(word in low for word in _ROUTE_WORDS)
    route_action = any(term in low for term in (
        "покажи", "построй", "проложи", "рассчитай", "сделай маршрут",
        "нужен маршрут", "дай маршрут", "карта проезда", "карту проезда",
        "как добраться", "как попасть", "как проехать", "как пройти",
        "укажи путь", "показать на карте", "покажи на карте", "путь на карте",
        "navigate", "navigation", "directions", "show me the way", "get to",
        "how do i get", "how to get", "this route", "that route", "этот маршрут",
        "тот маршрут", "этот путь", "этот проезд",
    ))
    has_endpoints = bool(re.search(
        r"\b(?:с|со|из|от|з|із|від|from)\s+.+?\s+(?:до|к|в|во|на|у|to|towards)\s+.+",
        normalized, re.IGNORECASE,
    ))
    natural_destination_action = bool(_ROUTE_DESTINATION_ACTION_RE.search(normalized))
    natural_origin_anchor = bool(re.search(
        r"\b(?:я\s+)?(?:сейчас\s+)?(?:нахожусь|стою|пребываю|расположен[ао]?|живу)\b|"
        r"\bя\s+(?:сейчас\s+)?(?:на|по)\s+" + _STREET_TYPE_RE,
        normalized,
        re.IGNORECASE,
    ))
    # Natural speech often states a starting location and then says "мне надо
    # пройти к ...". Accept that as navigation without requiring "от X до Y".
    route = bool(
        route_keyword
        and (route_action or has_endpoints or natural_destination_action)
        or (natural_origin_anchor and natural_destination_action)
        or (natural_origin_anchor and route_action and any(term in low for term in ("на карте", "карту", "укажи путь")))
    )
    place_keyword = any(word in low for word in _PLACE_WORDS)
    place_action = any(term in low for term in (
        "найди", "найти", "покажи", "подскажи", "посоветуй", "рекомендуй",
        "подбери", "ищу", "где найти", "где есть", "на карте", "рядом",
        "поблизости", "ближайш", "find", "search", "show", "recommend",
        "suggest", "best", "nearest", "nearby", "looking for", "on the map",
    ))
    place_location_context = bool(_extract_city(text)) or any(
        term in low for term in ("рядом со мной", "near me", "nearby", "в районе", "в центре", "на карте")
    )
    abstract_place_question = bool(re.search(
        r"^(?:что такое|что означает|объясни|what is|what does|define)\s+(?:a\s+|the\s+)?(?:бар|бары|ресторан|рестораны|кафе|паб|пабов|bar|bars|restaurant|restaurants|cafe|cafes)\b",
        low,
    ))
    places = bool(place_keyword and (place_action or place_location_context) and not abstract_place_question)
    return route, places


def resolve_navigation_plan(current_text: str, selected_pairs: Optional[list[Any]] = None) -> Optional[dict[str, Any]]:
    """Return a deterministic route/places plan, or None for normal chat."""
    current = _normalize(current_text)
    route_intent, place_intent = _navigation_intent(current)
    contextual = (
        any(word in current.lower() for word in _FOLLOWUP_WORDS)
        or bool(_ROUTE_LINK_REPAIR_RE.search(current))
    )
    previous_route = ""
    if contextual and isinstance(selected_pairs, list):
        for pair in reversed(selected_pairs):
            if not isinstance(pair, dict):
                continue
            previous_user_text = _normalize(pair.get("user") or pair.get("user_text") or pair.get("user_request") or pair.get("request") or pair.get("input"))
            if previous_user_text and _navigation_intent(previous_user_text)[0]:
                previous_route = previous_user_text
                break
    source_text = current
    parsed = _parse_route(source_text)
    if not (parsed.get("origin") and parsed.get("destination")) and previous_route:
        parsed = _parse_route(previous_route)
        source_text = previous_route
        route_intent = True
    if route_intent:
        return {
            "kind": "route",
            "source_text": source_text[:1600],
            "origin": parsed.get("origin", ""),
            "destination": parsed.get("destination", ""),
            "city": parsed.get("city", ""),
            "travel_mode": _travel_mode(
                current if any(term in current.lower() for term in (
                    "пешком", "пішки", "пройти", "дойти", "walk", "walking", "on foot",
                    "автомобил", "на машине", "на авто", "за рулем", "driving", "by car",
                    "автобус", "трамва", "троллейбус", "общественн", "transit", "bus", "train", "metro",
                    "велосипед", "bike", "bicycle", "cycling",
                )) else source_text
            ),
            "followup": bool(previous_route),
            "needs_map_image": any(term in current.lower() for term in ("изображен", "фото", "картин", "image", "picture", "photo")),
        }
    if place_intent:
        city = _extract_city(current)
        query = current
        # The actual query should describe the desired category and area; leave
        # full user language intact for Google Places' semantic search.
        return {
            "kind": "places",
            "query": query[:300],
            "city": city,
            "needs_map_image": False,
        }
    return None


def _api_key() -> str:
    for name in GOOGLE_API_KEY_ENV_NAMES:
        value = os.getenv(name, "").strip()
        if value:
            return value
    return ""

def _static_maps_browser_key() -> str:
    """A separate key intended for direct client requests to Static Maps.

    This key is public in the image URL by design. Restrict it to the Static
    Maps API and the application's allowed HTTP referrers. Never reuse the
    server-side Routes/Places key here.
    """
    for name in STATIC_MAPS_BROWSER_KEY_ENV_NAMES:
        value = os.getenv(name, "").strip()
        if value:
            return value
    return ""


def _sign_static_maps_url(url: str) -> str:
    """Optionally sign a direct Static Maps URL using Google's URL secret.

    The signing secret stays on the server. It is never included in the image
    URL or in logs. If configured but malformed, fail closed rather than emit
    a URL that may be rejected by a signed-only Static Maps configuration.
    """
    secret = os.getenv(STATIC_MAPS_SIGNING_SECRET_ENV, "").strip()
    if not secret:
        return url
    try:
        padded_secret = secret + ("=" * ((4 - len(secret) % 4) % 4))
        decoded_secret = base64.urlsafe_b64decode(padded_secret.encode("ascii"))
        parts = urllib.parse.urlsplit(url)
        path_and_query = parts.path + ("?" + parts.query if parts.query else "")
        digest = hmac.new(decoded_secret, path_and_query.encode("utf-8"), hashlib.sha1).digest()
        signature = base64.urlsafe_b64encode(digest).decode("ascii")
        signed_query = parts.query + "&signature=" + urllib.parse.quote(signature, safe="-_= ")
        return urllib.parse.urlunsplit((parts.scheme, parts.netloc, parts.path, signed_query, parts.fragment))
    except Exception:
        return ""


def _http_json(url: str, *, method: str = "GET", headers: Optional[dict[str, str]] = None, body: Optional[dict[str, Any]] = None, timeout: float = 7.0) -> dict[str, Any]:
    data = json.dumps(body).encode("utf-8") if body is not None else None
    request = urllib.request.Request(url, data=data, headers=headers or {}, method=method)
    with urllib.request.urlopen(request, timeout=timeout) as response:
        raw = response.read(2 * 1024 * 1024)
    parsed = json.loads(raw.decode("utf-8"))
    return parsed if isinstance(parsed, dict) else {}


def _maps_directions_url(origin: str, destination: str, mode: str) -> str:
    mode_map = {"DRIVE": "driving", "WALK": "walking", "BICYCLE": "bicycling", "TRANSIT": "transit"}
    query = urllib.parse.urlencode({
        "api": "1", "origin": origin, "destination": destination,
        "travelmode": mode_map.get(mode, "driving"),
    })
    return f"https://www.google.com/maps/dir/?{query}"


def _maps_search_url(query: str) -> str:
    return "https://www.google.com/maps/search/?" + urllib.parse.urlencode({"api": "1", "query": query})


def _route_api(plan: dict[str, Any], language: str) -> dict[str, Any]:
    key = _api_key()
    if not key:
        return {}
    mode = plan.get("travel_mode") if plan.get("travel_mode") in {"DRIVE", "WALK", "BICYCLE", "TRANSIT"} else "DRIVE"
    body = {
        "origin": {"address": plan["origin"]},
        "destination": {"address": plan["destination"]},
        "travelMode": mode,
        "polylineQuality": "OVERVIEW",
        "polylineEncoding": "ENCODED_POLYLINE",
        "languageCode": (language or "ru").split("-")[0],
        "units": "METRIC",
    }
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": key,
        "X-Goog-FieldMask": ",".join((
            "routes.distanceMeters", "routes.duration", "routes.polyline.encodedPolyline",
            "routes.legs.steps.navigationInstruction.instructions", "routes.legs.steps.distanceMeters",
            "routes.legs.steps.staticDuration", "routes.legs.startLocation.latLng",
            "routes.legs.endLocation.latLng", "routes.legs.steps.endLocation.latLng",
        )),
    }
    try:
        data = _http_json(ROUTES_ENDPOINT, method="POST", headers=headers, body=body, timeout=8.0)
        routes = data.get("routes") if isinstance(data.get("routes"), list) else []
        route = routes[0] if routes and isinstance(routes[0], dict) else {}
        encoded = _text((route.get("polyline") or {}).get("encodedPolyline"))
        if not encoded or not route.get("distanceMeters") or not _text(route.get("duration")):
            return {}
        return route
    except Exception:
        return {}


def _static_map(route: dict[str, Any]) -> str:
    """Return a direct Google Static Maps URL; never fetch/cache its image."""
    key = _static_maps_browser_key()
    polyline = _text((route.get("polyline") or {}).get("encodedPolyline"))
    legs = route.get("legs") if isinstance(route.get("legs"), list) else []
    if not key or not polyline or not legs or not isinstance(legs[0], dict):
        return ""
    start = ((legs[0].get("startLocation") or {}).get("latLng") or {})
    end = ((legs[0].get("endLocation") or {}).get("latLng") or {})
    if not all(start.get(key) is not None for key in ("latitude", "longitude")):
        return ""
    if not all(end.get(key) is not None for key in ("latitude", "longitude")):
        return ""
    params = {
        "size": "640x480", "scale": "2", "format": "png", "maptype": "roadmap",
        "path": f"color:0x1B70E2FF|weight:6|enc:{polyline}",
        "markers": [
            f"color:green|label:A|{start.get('latitude')},{start.get('longitude')}",
            f"color:red|label:B|{end.get('latitude')},{end.get('longitude')}",
        ],
        "key": key,
    }
    unsigned_url = STATIC_MAPS_ENDPOINT + "?" + urllib.parse.urlencode(params, doseq=True)
    return _sign_static_maps_url(unsigned_url)


def _static_places_map(places: list[dict[str, Any]]) -> str:
    """Return a direct Static Maps URL for verified Places coordinates."""
    key = _static_maps_browser_key()
    if not key:
        return ""
    markers: list[str] = []
    for index, place in enumerate(places[:5]):
        if not isinstance(place, dict):
            continue
        location = place.get("location") if isinstance(place.get("location"), dict) else {}
        lat, lng = location.get("latitude"), location.get("longitude")
        try:
            lat_f, lng_f = float(lat), float(lng)
        except (TypeError, ValueError):
            continue
        if not (-90 <= lat_f <= 90 and -180 <= lng_f <= 180):
            continue
        marker_label = chr(ord("A") + index)
        markers.append(f"color:blue|label:{marker_label}|{lat_f},{lng_f}")
    if not markers:
        return ""
    params = {
        "size": "640x480", "scale": "2", "format": "png", "maptype": "roadmap",
        "markers": markers, "key": key,
    }
    unsigned_url = STATIC_MAPS_ENDPOINT + "?" + urllib.parse.urlencode(params, doseq=True)
    return _sign_static_maps_url(unsigned_url)


def _places_api(plan: dict[str, Any], language: str) -> list[dict[str, Any]]:
    key = _api_key()
    if not key:
        return []
    query = _text(plan.get("query"))
    city = _text(plan.get("city"))
    if city and city.lower() not in query.lower():
        query = f"{query} in {city}"
    try:
        data = _http_json(
            PLACES_ENDPOINT,
            method="POST",
            headers={
                "Content-Type": "application/json",
                "X-Goog-Api-Key": key,
                "X-Goog-FieldMask": "places.displayName,places.formattedAddress,places.location,places.rating,places.userRatingCount,places.googleMapsUri",
            },
            body={"textQuery": query, "languageCode": (language or "ru").split("-")[0], "maxResultCount": 5},
            timeout=7.0,
        )
        places = data.get("places") if isinstance(data.get("places"), list) else []
        return [item for item in places[:5] if isinstance(item, dict)]
    except Exception:
        return []


def _localized(language: str, key: str, **values: Any) -> str:
    lang = (language or "ru").lower().replace("_", "-").split("-", 1)[0]
    if lang == "uk":
        lang = "ua"
    table = {
        "route_missing": {
            "ru": "Чтобы построить маршрут, пришлите обе точки: откуда вы отправляетесь и куда нужно попасть. Я не буду угадывать начальную точку или рисовать вымышленные улицы.",
            "ua": "Щоб побудувати маршрут, надішліть обидві точки: звідки ви вирушаєте та куди потрібно дістатися. Я не вгадуватиму початкову точку й не малюватиму вигадані вулиці.",
            "en": "Please provide both endpoints: where you are starting and where you want to go. I will not guess your starting point or invent streets.",
        },
        "route_no_city": {
            "ru": "Точки маршрута получены, но не указан город. Напишите город, чтобы не построить маршрут в неверном месте.",
            "ua": "Точки маршруту отримано, але не вказано місто. Напишіть місто, щоб не побудувати маршрут у неправильному місці.",
            "en": "I have both route endpoints, but the city is missing. Please provide the city so I do not route you to the wrong place.",
        },
        "route_fallback": {
            "ru": "Я подготовила ссылку с указанными начальной и конечной точками. После открытия Google Maps рассчитает актуальный путь и навигацию. Встроенную проверенную карту сейчас получить не удалось, поэтому я не показываю приблизительный рисунок.",
            "ua": "Я підготувала посилання із зазначеними початковою та кінцевою точками. Після відкриття Google Maps розрахує актуальний шлях і навігацію. Не вдалося отримати перевірену вбудовану карту, тому я не показую приблизний малюнок.",
            "en": "I prepared a Google Maps link with your supplied start and destination. Google Maps will calculate the current route when you open it. I could not retrieve a verified embedded map, so I am not showing an approximate drawing.",
        },
        "route_verified": {
            "ru": "Нашла маршрут по указанным точкам. Расстояние: {distance}. Время в пути: {duration}. Ниже — карта и основные повороты. Проверьте дорожные условия перед выездом.",
            "ua": "Знайдено маршрут за вказаними точками. Відстань: {distance}. Час у дорозі: {duration}. Нижче — карта й основні повороти. Перевірте дорожні умови перед виїздом.",
            "en": "I found a route for the supplied endpoints. Distance: {distance}. Travel time: {duration}. The map and main turns are below. Check road conditions before departure.",
        },
        "route_history_safe": {
            "ru": "Карта маршрута была показана в предыдущем сообщении. Данные карты не сохраняются в истории; исходные точки сохранены, поэтому маршрут можно построить заново.",
            "ua": "Карту маршруту було показано в попередньому повідомленні. Дані карти не зберігаються в історії; початкові точки збережено, тому маршрут можна побудувати знову.",
            "en": "The route map was shown in the previous message. Map content is not stored in chat history; your original endpoints are retained so the route can be rebuilt.",
        },
        "places_history_safe": {
            "ru": "Поиск мест был показан в предыдущем сообщении. Результаты Google Maps не сохраняются в истории; исходный запрос сохранён, поэтому поиск можно повторить.",
            "ua": "Пошук місць було показано в попередньому повідомленні. Результати Google Maps не зберігаються в історії; початковий запит збережено, тому пошук можна повторити.",
            "en": "The place search was shown in the previous message. Google Maps results are not stored in chat history; your original query is retained so the search can be repeated.",
        },
        "map_unavailable": {
            "ru": "Встроенную карту получить не удалось, поэтому откройте ссылку Google Maps ниже — там будут карта и навигация.",
            "ua": "Не вдалося отримати вбудовану мапу, тому відкрийте посилання Google Maps нижче — там будуть мапа й навігація.",
            "en": "I could not retrieve the embedded map. Open the Google Maps link below to view the map and navigation.",
        },
        "places_fallback": {
            "ru": "Откройте поиск мест на карте по вашему запросу. Без настроенного картографического сервиса я не буду придумывать названия заведений, рейтинги или адреса.",
            "ua": "Відкрийте пошук місць на карті за вашим запитом. Без налаштованого картографічного сервісу я не вигадуватиму назви закладів, рейтинги чи адреси.",
            "en": "Open the map search for your request. Without a configured places provider, I will not invent business names, ratings or addresses.",
        },
        "places_need_location": {
            "ru": "Уточните город или район, где искать бары и рестораны. Точное местоположение устройства мне недоступно, поэтому я не буду выдавать случайные заведения из другого города за ближайшие к вам.",
            "ua": "Уточніть місто або район, де шукати бари й ресторани. Точне місцезнаходження пристрою мені недоступне, тому я не показуватиму випадкові заклади з іншого міста як найближчі до вас.",
            "en": "Please specify the city or area for bars and restaurants. I do not have your device's precise location, so I will not present random businesses from another city as nearby.",
        },
        "places_found": {
            "ru": "Нашла места по запросу. Ниже — названия, адреса и ссылки на карточки карты. Рейтинги показаны только там, где их вернул сервис.",
            "ua": "Знайдено місця за запитом. Нижче — назви, адреси та посилання на картки мапи. Рейтинги наведено лише там, де їх повернув сервіс.",
            "en": "I found places matching your request. Names, addresses and map links are below. Ratings are shown only when returned by the provider.",
        },
    }
    messages = table.get(key, {})
    template = messages.get(lang) or messages.get("en") or ""
    return template.format(**values)


def _duration_label(value: str) -> str:
    try:
        seconds = int(re.sub(r"[^0-9]", "", value or "0"))
    except (TypeError, ValueError):
        return "неизвестно"
    minutes = max(1, round(seconds / 60))
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours} ч {minutes} мин" if minutes else f"{hours} ч"
    return f"{minutes} мин"


def _distance_label(meters: Any) -> str:
    try:
        number = float(meters)
    except (TypeError, ValueError):
        return "неизвестно"
    return f"{number / 1000:.1f} км" if number >= 1000 else f"{number:.0f} м"


def build_navigation_response(request: MachineRequest, *, plan: Optional[dict[str, Any]] = None, language: str = "ru") -> Optional[dict[str, Any]]:
    """Execute the room's bounded fast path; return None for unrelated requests."""
    if plan is None:
        current = _current_query(request)
        memory = getattr(request, "memory", {})
        selected = memory.get("selected_pairs") if isinstance(memory, dict) else []
        plan = resolve_navigation_plan(current, selected if isinstance(selected, list) else [])
    if not isinstance(plan, dict):
        return None

    answer = ""
    links: list[dict[str, str]] = []
    map_url = ""
    route_data: dict[str, Any] = {}
    places_verified = False
    if plan.get("kind") == "route":
        origin = _text(plan.get("origin"))
        destination = _text(plan.get("destination"))
        city = _text(plan.get("city"))
        if not origin or not destination:
            answer = _localized(language, "route_missing")
        elif not city and not re.search(r"\b(?:ukraine|poland|germany|romania|moldova|united states|canada|united kingdom|france|italy|spain|turkey|czechia|austria|netherlands|japan|united arab emirates|portugal|greece|hungary|bulgaria)\b", origin + " " + destination, re.I):
            answer = _localized(language, "route_no_city")
        else:
            mode = _text(plan.get("travel_mode") or "DRIVE")
            directions_url = _maps_directions_url(origin, destination, mode)
            route_data = _route_api(plan, language)
            if route_data:
                map_url = _static_map(route_data)
                if map_url:
                    answer = _localized(
                        language, "route_verified",
                        distance=_distance_label(route_data.get("distanceMeters")),
                        duration=_duration_label(_text(route_data.get("duration"))),
                    )
                    steps: list[str] = []
                    legs = route_data.get("legs") if isinstance(route_data.get("legs"), list) else []
                    for leg in legs[:1]:
                        for step in (leg.get("steps") or [])[:8] if isinstance(leg, dict) else []:
                            if not isinstance(step, dict):
                                continue
                            instruction = _text((step.get("navigationInstruction") or {}).get("instructions"))
                            if instruction:
                                steps.append(instruction)
                    if steps:
                        answer += "\n\n" + "\n".join(f"{index + 1}. {value}" for index, value in enumerate(steps))
                else:
                    # Do not detach Google-derived route facts from their map
                    # attribution when Static Maps cannot be displayed.
                    answer = _localized(language, "map_unavailable")
            else:
                answer = _localized(language, "route_fallback")
            # A deep link is built locally from the user's own endpoints. It does
            # not call Routes/Static Maps and therefore works before API keys are
            # configured. Keep it both in the canonical answer and as LinkCard;
            # SceneContract normalizes the duplicate into one dedicated link node.
            answer += f"\n\n[Открыть маршрут в Google Maps]({directions_url})"
            links.append({"url": directions_url, "title": "Открыть маршрут в Google Maps", "description": f"{origin} → {destination}"})
    elif plan.get("kind") == "places":
        query = _text(plan.get("query"))
        city = _text(plan.get("city"))
        if city and city.lower() not in query.lower():
            query += f" {city}"
        search_url = _maps_search_url(query)
        # Text search without a city/area can return unrelated global results.
        # Do not infer the user's location from IP or account metadata.
        places = _places_api(plan, language) if city else []
        places_verified = bool(places)
        if places:
            map_url = _static_places_map(places)
            if map_url:
                answer = _localized(language, "places_found")
                for place in places:
                    title = _text((place.get("displayName") or {}).get("text")) or "Место на карте"
                    address = _text(place.get("formattedAddress"))
                    uri = _text(place.get("googleMapsUri")) or search_url
                    rating = place.get("rating")
                    rating_text = f" · рейтинг {rating}" if isinstance(rating, (int, float)) else ""
                    links.append({"url": uri, "title": title, "description": address + rating_text})
                    answer += f"\n\n**{title}** — {address}{rating_text}"
            else:
                # Place names, addresses and ratings are shown only alongside
                # the Google Map attribution. Otherwise link directly to Maps.
                answer = _localized(language, "map_unavailable")
                links.append({"url": search_url, "title": "Искать места в Google Maps", "description": query})
        else:
            answer = _localized(language, "places_need_location" if not city else "places_fallback")
            links.append({"url": search_url, "title": "Искать места в Google Maps", "description": query})

    renderer_text = {"type": "text", "renderer": "MessageTextBlock", "viewer": "MessageTextBlock", "content": answer}
    render_blocks: list[dict[str, Any]] = [renderer_text]
    if map_url:
        map_alt = (
            "Verified route map"
            if plan.get("kind") == "route"
            else "Map of verified nearby places"
        )
        render_blocks.append({
            "type": "image", "renderer": "GalleryBlock", "viewer": "GalleryBlock",
            "content": "", "payload": {
                "title": "Карта маршрута" if plan.get("kind") == "route" else "Места на карте",
                "images": [{
                    "src": map_url,
                    "mime_type": "image/png",
                    "alt": map_alt,
                    "width": 1280,
                    "height": 960,
                    "caption": "Карта загружается напрямую из Google Maps",
                }],
            },
        })
    for item in links:
        render_blocks.append({
            "type": "link", "renderer": "LinkCard", "viewer": "LinkCard",
            "content": "", "payload": {
                "url": item["url"], "title": item["title"], "description": item["description"],
                "links": [{"url": item["url"], "title": item["title"], "description": item["description"]}],
            },
        })
    machine_response = {
        "answer": answer, "content": answer, "summary": answer[:180],
        "render_blocks": render_blocks, "artifacts": [],
        "metadata": {
            "identity": {}, "provider_calls": 0, "world_room": True,
            "world_kind": _text(plan.get("kind")),
            "route_verified": bool(route_data),
            "places_verified": places_verified,
        },
        "internal_answer_en": answer,
    }
    return {
        "handled": True,
        "machine_response": machine_response,
        "plan": plan,
        "route_data": route_data,
        "map_image_url": map_url,
    }


def build_persistence_safe_turn(world_result: dict[str, Any], language: str = "ru") -> dict[str, Any]:
    """Build a provider-content-free history record for C.World responses.

    Maps-derived distances, instructions, place names, addresses, ratings,
    encoded polylines and image URLs are intentionally ephemeral. User-supplied
    endpoints/query are converted to a fresh Google Maps deep link; only that
    link and a short notice are retained with the dialogue turn.
    """
    plan = world_result.get("plan") if isinstance(world_result.get("plan"), dict) else {}
    if _text(plan.get("kind")) == "route":
        origin = _text(plan.get("origin"))
        destination = _text(plan.get("destination"))
        mode = _text(plan.get("travel_mode") or "DRIVE")
        url = _maps_directions_url(origin, destination, mode) if origin and destination else ""
        title = "Открыть маршрут в Google Maps"
        description = f"{origin} → {destination}" if origin and destination else "Маршрут из сообщения пользователя"
        safe_answer = _localized(language, "route_history_safe")
    else:
        query = _text(plan.get("query"))
        city = _text(plan.get("city"))
        if city and city.lower() not in query.lower():
            query = f"{query} {city}".strip()
        url = _maps_search_url(query) if query else ""
        title = "Повторить поиск в Google Maps"
        description = query
        safe_answer = _localized(language, "places_history_safe")

    blocks: list[dict[str, Any]] = [{
        "type": "text", "renderer": "MessageTextBlock", "viewer": "MessageTextBlock",
        "content": safe_answer,
    }]
    if url:
        blocks.append({
            "type": "link", "renderer": "LinkCard", "viewer": "LinkCard",
            "content": "", "payload": {
                "url": url, "title": title, "description": description,
                "links": [{"url": url, "title": title, "description": description}],
            },
        })
    return {"answer": safe_answer, "render_blocks": blocks, "artifacts": []}


def build_machine_contribution(
    machine_request: MachineRequest,
    *,
    plan: Optional[dict[str, Any]] = None,
) -> Dict[str, Any]:
    if plan is None:
        current = _current_query(machine_request)
        memory = getattr(machine_request, "memory", {})
        selected = memory.get("selected_pairs") if isinstance(memory, dict) else []
        recent = memory.get("recent_exchange_window") if isinstance(memory, dict) else []
        user_history = list(selected or []) if isinstance(selected, list) else []
        if isinstance(recent, list):
            user_history.extend(recent)
        plan = resolve_navigation_plan(current, user_history)
    return {
        "room": ROOM_ID,
        "knowledge_context": {
            "room": ROOM_ID,
            "navigation_requested": bool(plan),
            "navigation_plan": plan or {},
            "rules": [
                "Never invent a route, street, address, place name, rating, distance or travel time.",
                "Use user-supplied origin and destination; retrieve prior endpoints only from selected user messages in the active dialogue branch.",
                "For current route geometry and duration, use Google Routes API; render Static Maps directly from Google's URL using a separate referrer-restricted browser key.",
                "Never download, proxy, cache, or persist Google Maps image/content; persist only the user's own route request and a user-input-derived deep link.",
                "If map provider data is unavailable, provide a Google Maps deep link and clearly disclose that no verified embedded map was returned.",
                "For nearby restaurants, bars and other places, use a verified Places result or a Google Maps search link; never fabricate businesses.",
                "Explain in the user's language and distinguish provider facts from estimates.",
            ],
        },
        "prompt_fragments": [
            "C.World handles physical-world routes and place discovery.",
            "Use exact endpoints and provider-returned route/place data only; never draw invented geography.",
            "Render Google Static Maps only via direct client image URLs with the separately restricted browser key; do not fetch or persist map bytes.",
            "Never store Google Maps route or Places results in the persistent dialogue cache; retain only the user's own request for follow-up resolution.",
            "When the live map provider is not configured or fails, offer the external Google Maps link and disclose that limitation.",
        ],
        "artifact_hints": {"text": True, "link": True, "image": True, "diagram": False},
        "domain": "world_navigation",
        "knowledge_scope": ["maps", "directions", "routes", "restaurants", "bars", "places", "public_transport"],
        "artifact_outputs": ["text", "link", "image"],
        "capabilities": ["route_planning", "places_search", "map_preview", "navigation_guidance"],
        "scene_contributions": [], "focus_contributions": [], "memory_contributions": [],
        "trajectory_hints": ["preserve_origin_and_destination_across_route_followups"],
        "scene_hints": ["map_geometry_must_come_from_verified_routing_provider"],
        "room_identity": {"specialization": "maps_and_navigation", "knowledge_class": "world_information"},
    }


class WorldRoom:
    name = "C.World"
    id = ROOM_ID
    room_type = "knowledge"

    def get_context(self, machine_request: MachineRequest) -> Dict[str, Any]:
        return build_machine_contribution(machine_request)["knowledge_context"]

    def build_machine_contribution(self, machine_request: MachineRequest) -> Dict[str, Any]:
        return build_machine_contribution(machine_request)

    def evaluate(self, request: MachineRequest) -> Dict[str, Any]:
        contribution = self.build_machine_contribution(request)
        active = bool((contribution.get("knowledge_context") or {}).get("navigation_requested"))
        return {"room": self.id, "score": 1.0 if active else 0.0, "active": active, "reason": "navigation_match" if active else "no_match"}

    def execute(self, machine_request: MachineRequest):
        contribution = self.build_machine_contribution(machine_request)
        return create_artifact("function", self.id, contribution)

    async def handle(self, request: MachineRequest, run=None) -> MachineResponse:
        evaluation = self.evaluate(request)
        response = MachineResponse()
        response.fiber = request.fiber
        response.confidence = evaluation["score"]
        response.routing_decision = evaluation
        if evaluation["active"]:
            response.artifacts.append(self.execute(request))
            add_room_contribution(response, self.id, {"status": "navigation_context_ready"})
            response.executor_hints["room"] = self.id
            response.executor_hints["outputs"] = ["text", "link", "image"]
        else:
            add_room_contribution(response, self.id, {"status": "no_match"})
        return response


ROOM = WorldRoom()
