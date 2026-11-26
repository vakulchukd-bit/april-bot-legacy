"""C.World — shared OpenStreetMap search/routes and Waze navigation links.

The room does not synthesize map pictures or invent road geometry. It creates
provider URLs and hands them to the existing Scene Contract LinkCard renderer.
OpenStreetMap is the general-purpose map surface; Waze is offered for driving.
No Google Cloud key, billing account, new renderer, or image-generation call is
required for this link-based mode. Provider route calculation happens after the
user opens the selected map/navigation service.
"""
from __future__ import annotations

import re
import urllib.parse
from typing import Any, Dict, Optional

from blocks.C_ARTIFACT_CONTRACT import (
    MachineRequest,
    MachineResponse,
    add_room_contribution,
    create_artifact,
)

ROOM_ID = "C_WORLD_ROOM"
OSM_SEARCH_BASE = "https://www.openstreetmap.org/search"
OSM_DIRECTIONS_BASE = "https://www.openstreetmap.org/directions"
WAZE_DEEP_LINK_BASE = "https://waze.com/ul"
GOOGLE_MAPS_DIRECTIONS_BASE = "https://www.google.com/maps/dir/"

_ROUTE_WORDS = (
    "маршрут", "путь", "проезд", "пройти", "проехать", "добраться", "как попасть",
    "directions", "route", "get to", "get there", "how do i get", "how to get",
    "navigate", "navigation", "show me the way", "map route",
    "карту проезда", "карту маршрута", "этот маршрут",
    "this route", "this journey", "that route",
)
_PLACE_WORDS = (
    "ресторан", "рестораны", "кафе", "бар", "бары", "паб", "пабы", "кофейня",
    "кофейни", "магазин", "магазины", "супермаркет", "рынок", "торговый центр",
    "больниц", "клиник", "аптек", "поликлиник", "вокзал", "автовокзал",
    "железнодорожная станция", "железнодорожный вокзал", "аэропорт", "автостанция",
    "музе", "парк", "отел", "гостиниц", "заправк", "автозаправк", "банкомат",
    "банк", "почта", "почтовое отделение", "школа", "университет", "достопримечательност",
    "restaurant", "restaurants", "bar", "bars", "pub", "cafe", "cafes", "coffee shop",
    "shop", "shops", "store", "supermarket", "market", "shopping mall", "hospital",
    "clinic", "pharmacy", "railway station", "train station", "bus station", "airport",
    "museum", "park", "hotel", "gas station", "fuel station", "atm", "bank", "post office",
    "school", "university", "tourist attraction", "places near", "nearby places",
    "рядом со мной", "поблизости",
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
            "needs_map_image": False,
        }
    if place_intent:
        city = _extract_city(current)
        query = current
        # Keep the user's full phrase here; the map-link builder strips command
        # language and the explicit city before sending the search to OSM.
        return {
            "kind": "places",
            "query": query[:300],
            "city": city,
            "needs_map_image": False,
        }
    return None




def _clean_places_query(query: str, city: str = "") -> str:
    """Turn conversational place requests into a concise map-search phrase."""
    value = _normalize(query)
    value = re.sub(
        r"^(?:(?:пожалуйста|будь ласка|please)\s+)?(?:найди(?:те)?|найти|покажи(?:те)?|подскажи(?:те)?|подбери(?:те)?|посоветуй(?:те)?|ищу|find|search for|show me|look for|recommend)\s+",
        "",
        value,
        flags=re.IGNORECASE,
    )
    value = re.sub(
        r"\b(?:мне нужен|мне нужна|мне нужны|нужен|нужна|нужны|ближайш\w*|поблизости|рядом со мной|near me|nearest|nearby)\b",
        " ",
        value,
        flags=re.IGNORECASE,
    )
    # A location clause at the end is removed because the canonical city is
    # appended separately. This avoids queries such as "cafe in Tokyo Tokyo".
    value = re.sub(
        r"\s+(?:в городе|в г\.?|у місті|в|у|in|near)\s+(?:центре\s+)?[^,;.!?]+$",
        " ",
        value,
        flags=re.IGNORECASE,
    )
    value = re.sub(r"\s+на карте$", "", value, flags=re.IGNORECASE)
    value = re.sub(r"\s+", " ", value).strip(" ,.;:-")
    if city and not value:
        value = "places"
    return value[:220]

def _osm_search_url(query: str) -> str:
    """Open an OpenStreetMap search for a user-provided place/query."""
    clean = _normalize(query)[:400]
    return OSM_SEARCH_BASE + "?" + urllib.parse.urlencode({"query": clean})


def _osm_directions_url(origin: str, destination: str, mode: str) -> str:
    """Open OSM's directions page with both user-provided endpoints filled."""
    engine_by_mode = {
        "DRIVE": "fossgis_osrm_car",
        "WALK": "fossgis_osrm_foot",
        "BICYCLE": "fossgis_osrm_bike",
    }
    engine = engine_by_mode.get(mode)
    params = {"from": _normalize(origin), "to": _normalize(destination)}
    if engine:
        params["engine"] = engine
    return OSM_DIRECTIONS_BASE + "?" + urllib.parse.urlencode(params)


def _waze_directions_url(destination: str) -> str:
    """Open Waze search/navigation for a destination; Waze uses device location."""
    params = {
        "q": _normalize(destination),
        "utm_source": "april",
    }
    return WAZE_DEEP_LINK_BASE + "?" + urllib.parse.urlencode(params)


def _google_transit_url(origin: str, destination: str) -> str:
    """Keyless Google Maps URL used only as an optional public-transport handoff."""
    params = {
        "api": "1",
        "origin": _normalize(origin),
        "destination": _normalize(destination),
        "travelmode": "transit",
    }
    return GOOGLE_MAPS_DIRECTIONS_BASE + "?" + urllib.parse.urlencode(params)


def _localized(language: str, key: str, **values: Any) -> str:
    lang = (language or "ru").lower().replace("_", "-").split("-", 1)[0]
    if lang == "uk":
        lang = "ua"
    table = {
        "route_missing": {
            "ru": "Чтобы подготовить маршрут, пришлите обе точки: откуда вы отправляетесь и куда нужно попасть. Я не буду угадывать начальную точку или придумывать улицы.",
            "ua": "Щоб підготувати маршрут, надішліть обидві точки: звідки ви вирушаєте та куди потрібно дістатися. Я не вгадуватиму початкову точку й не вигадуватиму вулиці.",
            "en": "Please provide both endpoints: where you are starting and where you want to go. I will not guess your starting point or invent streets.",
        },
        "route_no_city": {
            "ru": "Точки маршрута получены, но не указан город или страна. Уточните их, чтобы не открыть маршрут в неправильном месте.",
            "ua": "Точки маршруту отримано, але не вказано місто або країну. Уточніть їх, щоб не відкрити маршрут у неправильному місці.",
            "en": "I have both route endpoints, but the city or country is missing. Please specify it so the route opens in the correct place.",
        },
        "route_link_ready": {
            "ru": "Подготовила маршрут в OpenStreetMap. На открывшейся странице проверьте найденные начальную и конечную точки и запустите расчёт пути. April не показывает расстояние или время, пока они не рассчитаны картографическим сервисом.",
            "ua": "Підготувала маршрут в OpenStreetMap. На відкритій сторінці перевірте знайдені початкову й кінцеву точки та запустіть розрахунок шляху. April не показує відстань або час, доки їх не розрахує картографічний сервіс.",
            "en": "I prepared an OpenStreetMap route link. Check the selected start and destination on the map page and calculate the route there. April does not claim a distance or duration before the map service calculates it.",
        },
        "route_transit_link": {
            "ru": "Для общественного транспорта подготовила отдельную ссылку на расчёт маршрута. Расписание, пересадки и время будут показаны сервисом после открытия.",
            "ua": "Для громадського транспорту підготувала окреме посилання для розрахунку маршруту. Розклад, пересадки й час покаже сервіс після відкриття.",
            "en": "I prepared a separate public-transport directions link. The provider will show schedules, transfers and travel time after you open it.",
        },
        "places_found": {
            "ru": "Открываю поиск объектов в OpenStreetMap. Выберите нужный результат на карте и проверьте адрес и расположение.",
            "ua": "Відкриваю пошук об'єктів в OpenStreetMap. Виберіть потрібний результат на мапі та перевірте адресу й розташування.",
            "en": "I am opening an OpenStreetMap place search. Select the correct result on the map and verify its address and location.",
        },
        "places_fallback": {
            "ru": "Не удалось определить город или район. Уточните место поиска, чтобы не показывать случайные объекты из другого региона.",
            "ua": "Не вдалося визначити місто або район. Уточніть місце пошуку, щоб не показувати випадкові об'єкти з іншого регіону.",
            "en": "I could not identify the city or area. Please specify it so I do not show unrelated places from another region.",
        },
        "places_need_location": {
            "ru": "Уточните город или район для поиска. Точное местоположение устройства мне недоступно, поэтому я не буду выдавать случайные объекты за ближайшие к вам.",
            "ua": "Уточніть місто або район для пошуку. Точне місцезнаходження пристрою мені недоступне, тому я не показуватиму випадкові об'єкти як найближчі до вас.",
            "en": "Please specify a city or area. I do not have your device's precise location, so I will not present random places as nearby.",
        },
        "route_history_safe": {
            "ru": "Ссылка на маршрут была показана в предыдущем сообщении. Исходные точки сохранены, поэтому ссылку можно восстановить без сохранения внешних картографических данных.",
            "ua": "Посилання на маршрут було показано в попередньому повідомленні. Початкові точки збережено, тому посилання можна відновити без збереження зовнішніх картографічних даних.",
            "en": "The route link was shown in the previous message. The original endpoints are retained so the link can be rebuilt without storing external map data.",
        },
        "places_history_safe": {
            "ru": "Ссылка на поиск мест была показана в предыдущем сообщении. Исходный запрос сохранён, поэтому поиск можно повторить без сохранения результатов внешней карты.",
            "ua": "Посилання на пошук місць було показано в попередньому повідомленні. Початковий запит збережено, тому пошук можна повторити без збереження результатів зовнішньої мапи.",
            "en": "The place-search link was shown in the previous message. The original query is retained so it can be repeated without storing external map results.",
        },
    }
    messages = table.get(key, {})
    template = messages.get(lang) or messages.get("en") or ""
    return template.format(**values)


def build_navigation_response(request: MachineRequest, *, plan: Optional[dict[str, Any]] = None, language: str = "ru") -> Optional[dict[str, Any]]:
    """Build a keyless OSM/Waze link response for the shared Free/Premium path."""
    if plan is None:
        current = _current_query(request)
        memory = getattr(request, "memory", {})
        selected = memory.get("selected_pairs") if isinstance(memory, dict) else []
        plan = resolve_navigation_plan(current, selected if isinstance(selected, list) else [])
    if not isinstance(plan, dict):
        return None

    answer = ""
    links: list[dict[str, str]] = []
    route_mode = ""

    if plan.get("kind") == "route":
        origin = _text(plan.get("origin"))
        destination = _text(plan.get("destination"))
        city = _text(plan.get("city"))
        mode = _text(plan.get("travel_mode") or "DRIVE").upper()
        route_mode = mode
        if not origin or not destination:
            answer = _localized(language, "route_missing")
        elif not city and not re.search(
            r"\b(?:ukraine|poland|germany|romania|moldova|united states|canada|united kingdom|france|italy|spain|turkey|czechia|austria|netherlands|japan|united arab emirates|portugal|greece|hungary|bulgaria|south korea|morocco|egypt|tunisia|algeria)\b",
            origin + " " + destination,
            re.I,
        ):
            answer = _localized(language, "route_no_city")
        else:
            osm_url = _osm_directions_url(origin, destination, mode)
            if mode == "TRANSIT":
                answer = _localized(language, "route_transit_link")
                transit_url = _google_transit_url(origin, destination)
                links.append({
                    "url": transit_url,
                    "title": "Маршрут общественным транспортом",
                    "description": f"{origin} → {destination}. Ссылка Google Maps без API-ключа.",
                })
                map_url = _osm_search_url(destination)
                links.append({
                    "url": map_url,
                    "title": "Показать пункт назначения в OpenStreetMap",
                    "description": f"{destination}. Карта и данные: © OpenStreetMap contributors.",
                })
            else:
                answer = _localized(language, "route_link_ready")
                mode_label = {"DRIVE": "автомобильный", "WALK": "пешеходный", "BICYCLE": "велосипедный"}.get(mode, "")
                links.append({
                    "url": osm_url,
                    "title": f"Открыть {mode_label} маршрут в OpenStreetMap",
                    "description": f"{origin} → {destination}. Проверка точек и расчёт пути откроются на карте.",
                })
                if mode == "DRIVE":
                    waze_url = _waze_directions_url(destination)
                    links.append({
                        "url": waze_url,
                        "title": "Найти пункт назначения в Waze",
                        "description": f"Пункт назначения: {destination}. В Waze можно проверить точку и запустить автомобильную навигацию от текущего местоположения.",
                    })
    elif plan.get("kind") == "places":
        raw_query = _text(plan.get("query"))
        city = _text(plan.get("city"))
        query = _clean_places_query(raw_query, city)
        if city and city.lower() not in query.lower():
            query = f"{query} {city}".strip()
        if not city:
            answer = _localized(language, "places_need_location")
        else:
            search_url = _osm_search_url(query)
            answer = _localized(language, "places_found")
            links.append({
                "url": search_url,
                "title": "Найти места на OpenStreetMap",
                "description": f"{query}. Карта и данные: © OpenStreetMap contributors.",
            })

    renderer_text = {"type": "text", "renderer": "MessageTextBlock", "viewer": "MessageTextBlock", "content": answer}
    render_blocks: list[dict[str, Any]] = [renderer_text]
    for item in links:
        render_blocks.append({
            "type": "link", "renderer": "LinkCard", "viewer": "LinkCard",
            "content": "", "payload": {
                "url": item["url"], "title": item["title"], "description": item["description"],
                "links": [{"url": item["url"], "title": item["title"], "description": item["description"]}],
            },
        })

    machine_response = {
        "answer": answer,
        "content": answer,
        "summary": answer[:180],
        "render_blocks": render_blocks,
        "artifacts": [],
        "metadata": {
            "identity": {},
            "provider_calls": 0,
            "world_room": True,
            "world_kind": _text(plan.get("kind")),
            "route_provider": "OpenStreetMap" if plan.get("kind") == "route" else "",
            "navigation_provider": "Waze" if route_mode == "DRIVE" else "",
            "route_verified": False,
            "places_verified": False,
            "map_image": False,
            "image_generation_used": False,
        },
        "internal_answer_en": answer,
    }
    return {
        "handled": True,
        "machine_response": machine_response,
        "plan": plan,
        "route_data": {},
        "map_image_url": "",
    }



def build_persistence_safe_turn(world_result: dict[str, Any], language: str = "ru") -> dict[str, Any]:
    """Persist only the user's own endpoints/query and rebuild external links."""
    plan = world_result.get("plan") if isinstance(world_result.get("plan"), dict) else {}
    links: list[dict[str, str]] = []
    if _text(plan.get("kind")) == "route":
        origin = _text(plan.get("origin"))
        destination = _text(plan.get("destination"))
        mode = _text(plan.get("travel_mode") or "DRIVE").upper()
        geographic_context = bool(plan.get("city")) or bool(re.search(
            r"\b(?:ukraine|poland|germany|romania|moldova|united states|canada|united kingdom|france|italy|spain|turkey|czechia|austria|netherlands|japan|united arab emirates|portugal|greece|hungary|bulgaria|south korea|morocco|egypt|tunisia|algeria)\b",
            origin + " " + destination,
            re.I,
        ))
        if not origin or not destination:
            safe_answer = _localized(language, "route_missing")
        elif not geographic_context:
            safe_answer = _localized(language, "route_no_city")
        else:
            safe_answer = _localized(language, "route_history_safe")
            if mode == "TRANSIT":
                transit_url = _google_transit_url(origin, destination)
                links.append({
                    "url": transit_url,
                    "title": "Маршрут общественным транспортом",
                    "description": f"{origin} → {destination}",
                })
                map_url = _osm_search_url(destination)
                links.append({"url": map_url, "title": "Пункт назначения в OpenStreetMap", "description": destination})
            else:
                url = _osm_directions_url(origin, destination, mode)
                links.append({
                    "url": url,
                    "title": "Повторить маршрут в OpenStreetMap",
                    "description": f"{origin} → {destination}",
                })
                if mode == "DRIVE":
                    links.append({
                        "url": _waze_directions_url(destination),
                        "title": "Найти пункт назначения в Waze",
                        "description": f"Пункт назначения: {destination}",
                    })
    else:
        raw_query = _text(plan.get("query"))
        city = _text(plan.get("city"))
        query = _clean_places_query(raw_query, city)
        if city and city.lower() not in query.lower():
            query = f"{query} {city}".strip()
        if not city:
            safe_answer = _localized(language, "places_need_location")
        else:
            safe_answer = _localized(language, "places_history_safe")
            if query:
                links.append({
                    "url": _osm_search_url(query),
                    "title": "Повторить поиск в OpenStreetMap",
                    "description": query,
                })

    blocks: list[dict[str, Any]] = [{
        "type": "text", "renderer": "MessageTextBlock", "viewer": "MessageTextBlock",
        "content": safe_answer,
    }]
    for item in links:
        blocks.append({
            "type": "link", "renderer": "LinkCard", "viewer": "LinkCard",
            "content": "", "payload": {
                "url": item["url"], "title": item["title"], "description": item["description"],
                "links": [{"url": item["url"], "title": item["title"], "description": item["description"]}],
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
                "Use OpenStreetMap search/directions links as the general map surface; these links cover the user's explicitly named location without requiring a Google Cloud key.",
                "Offer a Waze Deep Link for driving only; it opens a destination search, and the user starts navigation in Waze after confirming the result.",
                "For public-transport requests, provide a keyless external directions link and state that schedules/transfers are calculated by that provider after opening.",
                "Do not invent place names, addresses, ratings, road geometry, distance, duration, traffic or turn instructions. Provider results are not verified inside April in link-only mode.",
                "Persist only user-supplied endpoints/search terms and rebuild links; do not persist external map results.",
            ],
        },
        "prompt_fragments": [
            "C.World handles physical-world routes and place discovery.",
            "Use exact user-supplied endpoints and OpenStreetMap directions/search links; never draw invented geography.",
            "For driving, also offer the official Waze Deep Link; it opens the destination search so the user can confirm the place and start navigation in Waze.",
            "Do not generate map pictures or diagrams from natural language. Use only the existing LinkCard renderer for map/navigation links.",
            "Never store external map results; retain only the user's own request and rebuild external links for follow-up turns.",
            "No Google Cloud key or billing account is required for OpenStreetMap/Waze links. Public-transport link handoff is separate and keyless.",
        ],
        "artifact_hints": {"text": True, "link": True, "image": False, "diagram": False},
        "domain": "world_navigation",
        "knowledge_scope": ["maps", "directions", "routes", "restaurants", "bars", "places", "public_transport"],
        "artifact_outputs": ["text", "link"],
        "capabilities": ["osm_map_links", "osm_directions_links", "places_search_links", "waze_driving_navigation"],
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
            response.executor_hints["outputs"] = ["text", "link"]
        else:
            add_room_contribution(response, self.id, {"status": "no_match"})
        return response


ROOM = WorldRoom()
