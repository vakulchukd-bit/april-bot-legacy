"""April IT and product-navigation knowledge room.

The room is a read-only knowledge source. It describes only routes and controls
found in the companion April Web archive and never performs user actions.
"""
from __future__ import annotations

from typing import Any, Dict

from blocks.C_ARTIFACT_CONTRACT import (
    create_artifact,
    MachineRequest,
    MachineResponse,  # Backward-compatible room-contract export.
    UniversalArtifactContract,  # Backward-compatible room-contract export.
)

ROOM_ID = "it"

try:
    import pygments
    PYGMENTS_AVAILABLE = True
except ImportError:
    pygments = None
    PYGMENTS_AVAILABLE = False

try:
    import git
    GITPYTHON_AVAILABLE = True
except ImportError:
    git = None
    GITPYTHON_AVAILABLE = False

try:
    import lizard
    LIZARD_AVAILABLE = True
except ImportError:
    lizard = None
    LIZARD_AVAILABLE = False

try:
    import tree_sitter
    TREE_SITTER_AVAILABLE = True
except ImportError:
    tree_sitter = None
    TREE_SITTER_AVAILABLE = False

IT_LIBRARY_STATUS = {
    "pygments": PYGMENTS_AVAILABLE,
    "gitpython": GITPYTHON_AVAILABLE,
    "lizard": LIZARD_AVAILABLE,
    "tree_sitter": TREE_SITTER_AVAILABLE,
}

IT_COMPETENCY = {
    "domains": [
        "software_development", "programming", "algorithms", "system_architecture",
        "databases", "networking", "cybersecurity", "cloud_computing", "devops",
        "artificial_intelligence", "machine_learning", "testing", "version_control",
        "api_design", "april_site_navigation", "user_interface_help", "account_guidance",
    ]
}

IT_PROVIDERS = [
    {"id":"python","name":"Python","kind":"language","enabled":True},
    {"id":"git","name":"Git","kind":"version_control","enabled":True},
    {"id":"docker","name":"Docker","kind":"container","enabled":True},
    {"id":"postgresql","name":"PostgreSQL","kind":"database","enabled":True},
    {"id":"mongodb","name":"MongoDB","kind":"database","enabled":True},
    {"id":"rest_api","name":"REST API","kind":"integration","enabled":True},
]

# Source-derived from routes and page actions in aprill-web-main archive.
# Only describe existing functionality; do not promise a control absent from the UI.
APRIL_SITE_MAP = {
    "schema": "april.site_navigation.v1",
    "source": "aprill-web-main routes and visible links",
    "areas": [
        {
            "id": "chat", "path": "/", "label": "Основной чат April",
            "purpose": "Переписка с April; отправка текста и доступные элементы ввода, вложений и голоса; просмотр текстовых и мультимедийных блоков ответа.",
            "steps": ["Откройте основной экран через значок/ссылку April или путь /. ", "Введите вопрос в поле сообщения; для вложения используйте доступный элемент прикрепления. ", "После отправки читайте пояснение и открывайте отдельные блоки ответа."],
            "related": ["history", "settings", "guide"]
        },
        {
            "id": "history", "path": "/history", "label": "История диалогов",
            "purpose": "Просмотр сохранённых диалогов, индекса тем и возврат к выбранному сообщению/теме. Доступ к истории проверяется по Premium; если доступ закрыт или статус тарифа не подтверждён, обновите страницу и проверьте Premium в настройках.",
            "steps": ["Откройте раздел История (/history).", "Найдите нужную запись по заголовку и тексту сообщения; список показывает сохранённые диалоги в пределах доступного окна.", "Нажмите «Продолжить этот диалог» у нужной записи: April вернётся в чат с выбранным сообщением как контекстом."],
            "related": ["chat", "memory"]
        },
        {
            "id": "memory", "path": "/memory", "label": "Память",
            "purpose": "Отдельный маршрут памяти существует и указан ссылкой в справке, но в просмотренном архиве содержимое страницы не реализовано (страница возвращает null). Не обещать отдельные инструменты управления/очистки памяти на этой странице. Окно контекста диалога заявлено как до 12 часов Free и до 24 часов Premium; история диалогов находится отдельно.",
            "steps": ["Если нужно вернуться к прошлому разговору, откройте Историю (/history).", "Если нужен профиль или настройки аккаунта, откройте Настройки (/settings)."],
            "related": ["history", "settings"]
        },
        {
            "id": "settings", "path": "/settings", "label": "Настройки и профиль",
            "purpose": "Профиль и ник пользователя, язык интерфейса, April ID и (для активного тарифа) Premium ID, статус/тестовая активация Premium, поддержка Premium, выход и удаление April-аккаунта.",
            "steps": ["Откройте Настройки (/settings) из профиля/панели пользователя.", "Для языка откройте блок выбора языка; настройка связана с текущим April ID.", "Для идентификаторов откройте блок профиля; используйте кнопку копирования ID, если она отображается.", "В блоке тарифа проверьте статус и оставшееся время; кнопки покупки/продления не подтверждают реальную оплату Google Play — в загруженной справке указано, что Google Play Billing ещё не подключён.", "Для поддержки откройте раздел поддержки в профиле (отправка обращения доступна Premium, с ограничением частоты).", "Для выхода нажмите кнопку выхода; для удаления April-аккаунта используйте «Удалить аккаунт» и подтверждение. Удаление April не удаляет аккаунт Google."],
            "related": ["chat", "support", "deletion", "guide"]
        },
        {
            "id": "space", "path": "/space", "label": "Сообщество и контакты",
            "purpose": "Общий чат для пользователей Free и Premium; публичные сообщения и вложения-файлы, поиск участников, приглашения, запросы в друзья, список контактов и настройка ника сообщества. Сообщения и файлы видны участникам; изображения/видео запрещены как вложения; файл — до 3 МБ, суммарный лимит активных вложений на пользователя — 30 МБ.",
            "steps": ["Откройте Сообщество (/space).", "Чтобы писать, войдите через Google; в поле сообщения введите текст или код и нажмите «Отправить».", "Чтобы приложить файл, используйте «Прикрепить файл»; изображения/видео и исполняемые файлы блокируются, максимальный размер одного файла — 3 МБ.", "В блоке поиска участников отправьте запрос в друзья; входящий запрос можно принять. Используйте «Пригласить друга», чтобы скопировать приглашение.", "Для личной переписки выберите контакт и нажмите «Личный диалог». Своё сообщение можно удалить; чужое — пожаловаться или скрыть через блокировку, если кнопка доступна.", "Не публикуйте пароли, API-ключи и личные данные: сообщение видят другие участники."],
            "related": ["settings", "direct"]
        },
        {
            "id": "direct", "path": "/space/direct/[friendId]", "label": "Личный диалог",
            "purpose": "Маршрут личной переписки с выбранным контактом; friendId — идентификатор контакта в URL, не вводится вручную.",
            "steps": ["Откройте Сообщество (/space).", "Выберите нужный контакт и перейдите в личный диалог через интерфейс."],
            "related": ["space"]
        },
        {
            "id": "support", "path": "/insights?room=support", "label": "Поддержка",
            "purpose": "Просмотр истории обращений и ответов техподдержки. Отправка обращения ограничена Premium; параметр message_id может открыть конкретное сообщение.",
            "steps": ["Откройте Настройки (/settings) и перейдите в секцию поддержки.", "Откройте историю обращения или контакт с поддержкой, если соответствующая кнопка отображается.", "Маршрут поддержки — /insights?room=support; конкретная запись может передаваться как message_id."],
            "related": ["settings", "admin-support"]
        },
        {
            "id": "guide", "path": "/aprill", "label": "Справка о April",
            "purpose": "Информационный раздел и FAQ по использованию April, памяти Free/Premium, истории, тарифам и платежам, поддержке, конфиденциальности, условиям и удалению аккаунта. В загруженной справке указано, что реальные платежи Google Play Billing ещё не активированы; Lite — будущий формат, а не доступный тариф.",
            "steps": ["Откройте раздел April (/aprill).", "Выберите подходящую тему или FAQ.", "Используйте ссылку на нужный раздел, чтобы перейти туда напрямую."],
            "related": ["chat", "history", "memory", "settings", "deletion"]
        },
        {
            "id": "deletion", "path": "/account-deletion", "label": "Удаление аккаунта April",
            "purpose": "Страница удаления данных April-аккаунта; не означает удаление Google-аккаунта.",
            "steps": ["Откройте Настройки (/settings) или справку (/aprill).", "Перейдите в Удаление аккаунта (/account-deletion).", "Прочитайте пояснения и следуйте подтверждению удаления."],
            "related": ["settings", "guide", "privacy"]
        },
        {
            "id": "privacy", "path": "/privacy-policy", "label": "Политика конфиденциальности",
            "purpose": "Описание обработки данных и ссылки на связанные юридические страницы.",
            "steps": ["Откройте /privacy-policy напрямую либо по ссылке из справки/подвала страницы."],
            "related": ["terms", "deletion"]
        },
        {
            "id": "terms", "path": "/terms-of-service", "label": "Условия использования",
            "purpose": "Условия использования April и связанные юридические сведения.",
            "steps": ["Откройте /terms-of-service напрямую либо по ссылке из политики/справки."],
            "related": ["privacy", "deletion"]
        },
        {
            "id": "tools", "path": "/tools", "label": "Инструменты",
            "purpose": "Маршрут существует, но текущая страница из архива не отображает содержимое. Не выдумывать инструменты; предложить вернуться в чат или настройки." ,
            "steps": ["Если страница пустая, вернитесь в основной чат (/).", "Уточните, какой инструмент нужен, и опишите желаемое действие в чате."],
            "related": ["chat", "settings"]
        },
        {
            "id": "admin-support", "path": "/Admin-profile", "label": "Административный профиль",
            "purpose": "Административная панель со служебным состоянием и входящими обращениями. Это не обычный пользовательский раздел; не направлять туда рядовых пользователей.",
            "steps": ["Обычному пользователю не требуется открывать этот маршрут.", "Для пользовательской поддержки используйте раздел поддержки в Настройках."],
            "related": ["support"]
        },
    ],
    "navigation_policy": [
        "Сначала уточняй цель пользователя, если неясно, какой раздел ему нужен.",
        "Давай конкретный путь и пошаговые действия, но не утверждай, что сам нажал кнопку или изменил аккаунт.",
        "Если пользователь потерялся, предложи безопасную точку возврата: основной чат /, затем нужный маршрут.",
        "Не направляй обычных пользователей на административную страницу.",
        "Не обещай функции маршрута /memory или /tools: в текущем просмотренном архиве страницы пустые.",
        "Для действий с подпиской, выходом и удалением описывай только видимые кнопки, а если их расположение отличается — попроси скриншот текущего экрана.",
    ],
}

_SITE_HELP_SIGNALS = (
    "site_navigation", "april_site_help", "user_guidance", "interface_help"
)

# Keyword groups are semantic hints for choosing a small request-scoped excerpt.
# The complete map above remains the canonical source; no user topic is hard-coded.
_SITE_AREA_HINTS = {
    "chat": ("чат", "chat", "сообщ", "ответ", "влож", "голос", "voice"),
    "history": ("истор", "history", "прошл", "старый диалог", "предыдущ", "восстанов", "продолж"),
    "memory": ("памят", "memory", "запом", "срок хранения"),
    "settings": ("настройк", "settings", "профил", "язык", "language", "апрель id", "april id", "premium", "тариф", "подпис", "выйти", "выход", "logout"),
    "space": ("сообществ", "space", "контакт", "друг", "друз", "community"),
    "direct": ("личн", "direct message", "переписк"),
    "support": ("поддерж", "support", "обращен", "техподдерж"),
    "guide": ("справк", "faq", "help", "помощ", "что где", "карта сайта"),
    "deletion": ("удал", "delete account", "account deletion"),
    "privacy": ("конфиденц", "privacy", "персональн.*данн"),
    "terms": ("услови", "terms of service", "правил"),
    "tools": ("инструмент", "tools", "генератор", "генерац"),
}


def _current_user_query(machine_request: Any) -> str:
    """Best-effort extract of this turn's request without touching conversation memory."""
    if isinstance(machine_request, dict):
        sources = [machine_request, machine_request.get("conversation") or {}]
    else:
        sources = [
            {"goal": getattr(machine_request, "goal", "")},
            getattr(machine_request, "conversation", {}) or {},
        ]
    for source in sources:
        if not isinstance(source, dict):
            continue
        for key in ("current_request", "current_text", "query", "user_message", "message", "goal"):
            value = source.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()[:1200]
    return ""


def _select_site_map_excerpt(machine_request: Any) -> Dict[str, Any]:
    """Return only the relevant routes for prompt efficiency; preserve the full map in this room."""
    query = _current_user_query(machine_request).lower().replace("ё", "е")
    selected_ids: list[str] = []
    for area_id, hints in _SITE_AREA_HINTS.items():
        if any(hint in query for hint in hints):
            selected_ids.append(area_id)
    if not selected_ids:
        selected_ids = ["guide", "chat", "settings", "history"]
    # Add directly related routes so users can recover to the next useful section.
    areas_by_id = {str(area.get("id")): area for area in APRIL_SITE_MAP["areas"]}
    pending = list(selected_ids)
    for area_id in list(selected_ids):
        area = areas_by_id.get(area_id, {})
        for related in area.get("related", []):
            if related in areas_by_id and related not in pending and len(pending) < 5:
                pending.append(related)
    chosen = [areas_by_id[area_id] for area_id in pending if area_id in areas_by_id]
    return {
        "schema": APRIL_SITE_MAP["schema"],
        "source": APRIL_SITE_MAP["source"],
        "matched_query": query[:240],
        "areas": chosen[:3],
        "navigation_policy": APRIL_SITE_MAP["navigation_policy"][:4],
        "map_area_count": len(APRIL_SITE_MAP["areas"]),
    }


def _site_help_requested(machine_request: Any) -> bool:
    if isinstance(machine_request, dict):
        intent = machine_request.get("intent") if isinstance(machine_request.get("intent"), dict) else machine_request
    else:
        intent = getattr(machine_request, "intent", {})
        intent = intent if isinstance(intent, dict) else {}
    nested = intent.get("interpretation") if isinstance(intent.get("interpretation"), dict) else {}
    for source in (intent, nested):
        capabilities = source.get("routing_capabilities") or []
        if isinstance(capabilities, (tuple, list, set)) and set(capabilities).intersection(_SITE_HELP_SIGNALS):
            return True
    routing = getattr(machine_request, "routing", {}) if not isinstance(machine_request, dict) else machine_request.get("routing", {})
    if isinstance(routing, dict) and routing.get("site_help_requested") is True:
        return True
    return False


def get_context(machine_request: MachineRequest | Dict[str, Any] | None = None) -> Dict[str, Any]:
    context: Dict[str, Any] = {
        "room": ROOM_ID,
        "competency": IT_COMPETENCY,
        "providers": IT_PROVIDERS,
        "libraries": IT_LIBRARY_STATUS,
        "site_help_requested": _site_help_requested(machine_request),
    }
    if context["site_help_requested"]:
        context["site_navigation_map"] = _select_site_map_excerpt(machine_request)
    return context


def build_machine_contribution(machine_request: MachineRequest) -> Dict[str, Any]:
    context = get_context(machine_request)
    help_active = bool(context.get("site_help_requested"))
    prompt_fragments = [
        "Use secure, maintainable software-engineering practices.",
        "Return machine-readable IT contribution, not a user-visible answer by itself.",
    ]
    if help_active:
        prompt_fragments.extend([
            "Answer April interface-navigation questions from site_navigation_map.",
            "Give the exact available route and ordered steps; do not claim to click or change settings for the user.",
            "If a page is marked empty/unimplemented, state that limitation and offer the verified fallback route.",
        ])
    return {
        "room": ROOM_ID,
        "knowledge_context": context,
        "prompt_fragments": prompt_fragments,
        "artifact_hints": {
            "text": True, "code": True, "table": True, "links": True, "graph": False,
        },
    }


def evaluate(machine_request: MachineRequest | Dict[str, Any]) -> Dict[str, Any]:
    help_active = _site_help_requested(machine_request)
    query = ""
    if isinstance(machine_request, dict):
        query = str(machine_request.get("query", "")).lower()
        if not query and isinstance(machine_request.get("conversation"), dict):
            query = str(machine_request["conversation"].get("current_request", "")).lower()
    score = 0.95 if help_active else 0.0
    for token in ("python", "api", "sql", "docker", "git", "algorithm", "алгоритм", "код", "программ", "database", "network"):
        if token in query:
            score = max(score, 0.95)
    return {
        "room": ROOM_ID,
        "score": score,
        "active": score > 0.0,
        "reason": "april_site_navigation_help" if help_active else ("it_match" if score > 0 else "no_match"),
    }


def execute(machine_request: MachineRequest):
    contribution = build_machine_contribution(machine_request)
    # Use the canonical contract's actual signature. Navigation knowledge is
    # machine-only so it does not render as a spurious user-facing IT block.
    return create_artifact(
        artifact_type="it",
        room_source=ROOM_ID,
        data={
            "domain": "april_site_navigation" if contribution["knowledge_context"].get("site_help_requested") else "software_engineering",
            "knowledge_scope": IT_COMPETENCY["domains"],
            "capabilities": ["software", "code", "analysis", "site_navigation", "user_guidance"],
            "payload": contribution,
            "machine_only": True,
            "human_visible": False,
        },
    )


class ITRoom:
    name = ROOM_ID
    id = ROOM_ID
    domains = IT_COMPETENCY["domains"]
    providers = IT_PROVIDERS

    @staticmethod
    def get_context(machine_request: MachineRequest) -> Dict[str, Any]:
        return get_context(machine_request)

    @staticmethod
    def build_machine_contribution(machine_request: MachineRequest) -> Dict[str, Any]:
        return build_machine_contribution(machine_request)

    @staticmethod
    def evaluate(machine_request: MachineRequest) -> Dict[str, Any]:
        return evaluate(machine_request)

    @staticmethod
    def execute(machine_request: MachineRequest):
        return execute(machine_request)


ROOM = ITRoom()
