"""April IT and product-navigation knowledge room.

The room is a read-only knowledge source. It describes only routes and controls
found in the companion April Web archive and never performs user actions.
"""
from __future__ import annotations

from typing import Any, Dict, List
import re

from blocks.C_ARTIFACT_CONTRACT import (
    create_artifact,
    MachineRequest,
    MachineResponse,  # Backward-compatible room-contract export.
    UniversalArtifactContract,  # Backward-compatible room-contract export.
)

ROOM_ID = "it"


def _text(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value).strip()

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
    "source": "embedded April route map plus user-provided UI screenshots; some card-level URLs are unverified",
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
            "steps": ["Откройте [Saved dialogues / История диалогов](/history) через профиль или прямую ссылку.", "Прокручивайте список сохранённых записей; карточка содержит время, заголовок/фрагмент текста и номер записи.", "Нажмите «Continue this dialogue» у нужной карточки, чтобы продолжить именно тот диалог. Не путайте историю с кратковременной памятью активного чата.", "Если запись не видна, проверьте период и статус тарифа; если раздел показывает Connected в Memory Status, это само по себе не означает, что отдельная страница памяти содержит список всех диалогов."],
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
            "steps": ["Откройте [профиль и настройки](/settings). На профиле видны имя в чате и карточка CURRENT PLAN.", "В блоке USER измените имя в чате через Edit, если хотите поменять подпись рядом с сообщениями.", "В карточке CURRENT PLAN проверьте Free/Premium и строку Time remaining. На предоставленном скриншоте Premium — US$25 за 28 дней; Renew появляется за 24 часа до окончания, автоматических списаний нет.", "Используйте быстрые переходы в карточке тарифа: Chat with April — /, Dialog history — /history, Contact support — /insights?room=support, Community — /space.", "Для языка откройте блок выбора языка; настройка должна относиться к текущему April ID. Для ID откройте блок профиля и используйте кнопку копирования, если она отображается.", "Для выхода нажмите кнопку выхода. Удаление April-аккаунта доступно через /account-deletion и не удаляет аккаунт Google."],
            "related": ["chat", "support", "deletion", "guide"]
        },
        {
            "id": "space", "path": "/space", "label": "Сообщество и контакты",
            "purpose": "Общий чат для пользователей Free и Premium; публичные сообщения и вложения-файлы, поиск участников, приглашения, запросы в друзья, список контактов и настройка ника сообщества. Сообщения и файлы видны участникам; изображения/видео запрещены как вложения; файл — до 3 МБ, суммарный лимит активных вложений на пользователя — 30 МБ.",
            "steps": ["Откройте [April · Community / Сообщество](/space). Вверху находится блок Personal profile и переключатель профиля.", "Чтобы написать публичное сообщение, прокрутите к полю «Ask a question or share a solution…», введите текст и нажмите стрелку отправки.", "Для файла нажмите значок скрепки слева от поля ввода. В показанном интерфейсе указаны лимит 3 МБ на файл и 30 МБ активных вложений на пользователя; изображения/видео и исполняемые файлы ограничены правилами загрузки.", "Чтобы перейти в личную переписку, нажмите «Private chat» в карточке сообщения нужного участника или выберите контакт в разделе контактов.", "Свой пост можно удалить через «Delete your message». Не публикуйте пароли, API-ключи и личные данные: сообщения сообщества видны участникам."],
            "related": ["settings", "direct"]
        },
        {
            "id": "direct", "path": "/space/direct/[friendId]", "label": "Личный диалог",
            "purpose": "Маршрут личной переписки с выбранным контактом; friendId — идентификатор контакта в URL, не вводится вручную.",
            "steps": ["Откройте Сообщество (/space).", "Выберите нужный контакт и перейдите в личный диалог через интерфейс."],
            "related": ["space"]
        },
        {
            "id": "support", "path": "/insights?room=support", "label": "Contact Support / Поддержка",
            "purpose": "Просмотр истории обращений и ответов техподдержки. Карточка Contact Support находится на странице Help & Information; отправка обращения доступна Premium по правилам показанного интерфейса.",
            "steps": ["Откройте [Help & Information](/aprill) и нажмите Contact Support, либо откройте [раздел поддержки](/insights?room=support).", "В профиле можно также открыть [настройки](/settings) и секцию поддержки, если она отображается.", "Не открывайте административный профиль: он предназначен не для обычных пользователей."],
            "related": ["settings", "guide", "admin-support"]
        },
        {
            "id": "guide", "path": "/aprill", "label": "Help & Information / Справка о April",
            "purpose": "Общая страница Help & Information со справочными карточками Help Center, How to Use April, Privacy Policy, Terms of Service, Plans & Payments, Account & Data Deletion и Contact Support. Названия карточек подтверждены предоставленным скриншотом; отдельные URL-якоря карточек в приложенном Bot ZIP отсутствуют, поэтому ссылка ведёт на страницу справки, где нужно выбрать карточку.",
            "steps": ["Откройте [Help & Information](/aprill).", "На странице нажмите карточку нужной темы: Help Center, How to Use April, Plans & Payments или Contact Support.", "Для юридических документов можно сразу открыть /privacy-policy или /terms-of-service; удаление данных — /account-deletion."],
            "related": ["help-center", "how-to-use", "plans", "chat", "history", "memory", "settings", "deletion"]
        },
        {
            "id": "help-center", "path": "/aprill", "label": "Help Center",
            "purpose": "Карточка Help Center на странице Help & Information; содержит типичные вопросы и ответы об использовании April. Точный URL отдельной карточки не подтверждён, поэтому используется родительская страница.",
            "steps": ["Откройте [Help & Information](/aprill).", "Нажмите карточку Help Center.", "Если нужного ответа нет, откройте How to Use April или задайте вопрос в основном чате [April](/)."],
            "related": ["guide", "how-to-use", "chat"]
        },
        {
            "id": "how-to-use", "path": "/aprill", "label": "How to Use April",
            "purpose": "Карточка руководства по текстовым запросам, голосу, изображениям, истории диалогов и памяти. Отдельный URL карточки в предоставленных материалах не подтверждён.",
            "steps": ["Откройте [Help & Information](/aprill).", "Нажмите карточку How to Use April.", "Для возврата к работе откройте основной [чат April](/)."],
            "related": ["guide", "chat", "history", "memory"]
        },
        {
            "id": "plans", "path": "/aprill", "label": "Plans & Payments / Тарифы и платежи",
            "purpose": "Справочная карточка о Free/Premium, сроках доступа, цене, продлении и платежах. Фактический статус и оставшееся время текущего тарифа показаны в профиле/настройках (/settings). На предоставленном скриншоте Premium указан как US$25 за 28 дней, кнопка продления появляется за 24 часа до окончания; автоматических списаний нет. Эти значения описывают показанный экран и могут измениться в приложении.",
            "steps": ["Откройте [Help & Information](/aprill) и нажмите Plans & Payments.", "Чтобы увидеть собственный тариф и оставшееся время, откройте [профиль и настройки](/settings).", "На показанном экране Premium стоит US$25 за 28 дней; продление предлагается за 24 часа до окончания, автоматических списаний нет."],
            "related": ["guide", "settings"]
        },
        {
            "id": "deletion", "path": "/account-deletion", "label": "Account & Data Deletion / Удаление аккаунта April",
            "purpose": "Страница удаления данных April-аккаунта; не означает удаление Google-аккаунта. На странице Help & Information также есть карточка Account & Data Deletion.",
            "steps": ["Можно открыть [Удаление аккаунта](/account-deletion) напрямую.", "Либо откройте [Help & Information](/aprill) и нажмите Account & Data Deletion.", "Прочитайте пояснения и подтвердите действие только если действительно хотите удалить April-аккаунт."],
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
    "chat": ("главный чат", "основной чат", "чат с april", "chat", "написать april", "поле сообщения", "отправить вопрос", "вложен", "голос"),
    "history": ("истор", "history", "сохраненн", "прошл", "старый диалог", "предыдущ", "восстанов", "продолж", "saved dialogues", "saved dialogs"),
    "memory": ("памят", "memory", "запом", "срок хранения", "окно памяти"),
    "settings": ("кабинет", "личный кабинет", "профил", "аккаунт", "account", "settings", "настройк", "язык", "language", "april id", "premium id", "тариф", "подпис", "premium", "free", "выйти", "выход", "logout", "продлен"),
    "space": ("сообществ", "community", "space", "чат с пользовател", "чат с другими", "другие пользовател", "публичный чат", "участник", "контакт", "друз", "поиск участников"),
    "direct": ("личн", "direct message", "личный диалог", "приватный чат", "переписк"),
    "support": ("поддерж", "support", "обращен", "техподдерж", "contact support"),
    "guide": ("справк", "faq", "help", "помощ", "help center", "how to use april", "что где", "карта сайта", "куда зайти", "куда нажать", "как пройти", "как открыть раздел"),
    "help-center": ("help center", "центр помощи", "частые вопросы", "вопросы и ответы"),
    "how-to-use": ("how to use april", "как пользоваться april", "руководство april", "инструкция april"),
    "plans": ("plans & payments", "plans and payments", "тарифы и платежи", "оплата", "цена premium", "стоимость premium", "продлить premium", "renew premium"),
    "deletion": ("удал", "delete account", "account deletion", "удаление данных"),
    "privacy": ("конфиденц", "privacy", "персональн.*данн"),
    "terms": ("услови", "terms of service", "правил"),
    "tools": ("инструмент", "tools", "генератор", "генерац"),
}


_SITE_NAVIGATION_ACTION_RE = re.compile(
    r"(?:куда\s+(?:мне\s+)?(?:зайти|нажать|перейти|открыть)|как\s+(?:зайти|попасть|перейти|открыть|найти|посмотреть|просмотреть)|"
    r"где\s+(?:(?:у\s+(?:меня|тебя|вас|april|април)\s+)?(?:находится|расположен|найти|открыть|посмотреть|вход|кнопк|ссылк)|.{0,55}(?:вход|кнопк|ссылк))|покажи\s+(?:мне\s+)?(?:куда|путь|раздел|ссылк)|"
    r"проведи\s+меня|как\s+пользоваться|по\s+сайту|по\s+интерфейсу|навигац|"
    r"where\s+(?:do\s+i|can\s+i)|how\s+do\s+i\s+(?:open|find|navigate)|where\s+is|show\s+me\s+where)",
    re.IGNORECASE,
)
def _site_navigation_picture_request(query: str, referenced_area_ids: Any = None) -> bool:
    """Route visual questions about April UI to its real SVG navigation map."""
    low = str(query or "").strip().lower().replace("ё", "е")
    referenced_ids = {str(value).strip().lower() for value in (referenced_area_ids or []) if str(value).strip()} if isinstance(referenced_area_ids, (list, tuple, set)) else set()
    ui_target = bool(referenced_ids.intersection({"space", "history", "settings", "support", "guide", "help-center", "how-to-use", "plans", "deletion", "privacy", "terms", "memory", "chat"})) or bool(re.search(
        r"(?:сообществ\w*|community|saved\s+dialogues?|истори\w*\s+диалог\w*|history|"
        r"кабинет|профил\w*|настройк\w*|settings|account|help\s+center|справк\w*|"
        r"support|поддержк\w*|тариф\w*|premium|памят\w*|удален\w*\s+аккаунт|"
        r"privacy\s+policy|terms\s+of\s+service|chat\s+with\s+april|основн\w*\s+чат)",
        low, re.IGNORECASE,
    ))
    if not ui_target or _SITE_NO_DIAGRAM_RE.search(low):
        return False
    if re.search(
        r"(?:только\s+(?:изображен\w*|картинк\w*|фото|портрет)|only\s+(?:an?\s+)?image)",
        low, re.IGNORECASE,
    ):
        return False
    # A real portrait/person/landscape request still goes to image generation.
    explicit_art = bool(re.search(
        r"(?:сгенерируй|создай|нарисуй|изобрази)\s+(?:мне\s+)?(?:фото|портрет|иллюстрац\w*|"
        r"картинк\w*\s+(?:человека|персонажа|пейзажа)|изображение\s+(?:человека|персонажа|пейзажа)|арт\b)|"
        r"(?:generate|create|draw)\s+(?:a\s+)?(?:portrait|person|character|landscape|artwork)",
        low, re.IGNORECASE,
    ))
    if explicit_art:
        return False
    asks_visual_path = bool(re.search(
        r"(?:на\s+(?:картинк\w*|изображени\w*|схем\w*)|визуальн\w*\s+путь|"
        r"покажи.{0,100}(?:путь|куда|интерфейс|меню|вход|картинк\w*|изображени\w*|схем\w*)|"
        r"(?:где|куда|как\s+(?:зайти|попасть|открыть|перейти)).{0,100}(?:картинк\w*|изображени\w*|схем\w*)|"
        r"show.{0,100}(?:path|where|interface|menu|picture|image|diagram)|"
        r"(?:where\s+(?:is|do\s+i|can\s+i)|how\s+do\s+i\s+(?:open|find|navigate)).{0,100}(?:picture|image|diagram))",
        low, re.IGNORECASE,
    ))
    return asks_visual_path


_SITE_ROUTE_WORDS = (
    "сообществ", "community", "личный кабинет", "кабинет april", "april id", "premium id",
    "история диалогов", "saved dialogues", "help center", "how to use april", "plans & payments",
    "account deletion", "удаление аккаунта", "privacy policy", "terms of service", "/settings",
    "/history", "/space", "/aprill", "/account-deletion", "/insights?room=support",
    "профиль пользователя", "тарифы и платежи", "контакт с поддержкой",
)


def is_site_help_query(query: str) -> bool:
    """Detect April self-help/navigation questions independently of LLM classification."""
    low = str(query or "").strip().lower().replace("ё", "е")
    if not low:
        return False
    # Direct route/section names are enough: a user can simply type "Сообщество".
    if any(term in low for term in _SITE_ROUTE_WORDS):
        return True
    # Broad questions about April's own capabilities should be grounded in the
    # real site map as well, so users receive both a description and entry points.
    april_self_help = bool(re.search(
        r"(?:\b(?:april|април)\b.{0,100}\b(?:функци\w*|возможност\w*|устроен\w*|работа\w*|создан\w*|умеешь|умеет|можешь|может)\b|"
        r"\b(?:функци\w*|возможност\w*)\b.{0,100}\b(?:april|април)\b|"
        r"(?:what can april do|how does april work|how is april built))",
        low,
        re.IGNORECASE,
    ))
    if april_self_help:
        return True
    ui_target = bool(re.search(
        r"(?:кабинет|профил|аккаунт|раздел|кнопк|меню|сайт|интерфейс|страниц|истор|диалог|сообществ|"
        r"тариф|подписк|памят|удален|поддержк|функци|возможност|как работает|как устроен|умеет|умеешь|"
        r"community|profile|account|settings|history|support|help center|features|capabilities|how does april work)",
        low,
    ))
    return bool(_SITE_NAVIGATION_ACTION_RE.search(low) and ui_target)


_SITE_NO_DIAGRAM_RE = re.compile(
    r"(?:только\s+текст|без\s+(?:схем|диаграмм|визуализац)|не\s+(?:нужна|нужно|надо)\s+(?:схема|диаграмма)|"
    r"не\s+(?:схему|диаграмму)|не\s+показывай\s+(?:схему|диаграмму)|text\s+only|no\s+diagram|not\s+(?:a\s+)?diagram)",
    re.IGNORECASE,
)
_SITE_EXPLICIT_DIAGRAM_RE = re.compile(r"(?:диаграмм\w*|схем\w*|diagram|flowchart)", re.IGNORECASE)
_SITE_OTHER_RENDERERS = {"image", "gallery", "code", "table", "graph", "formula", "link", "file", "3d_graph"}


def _site_should_render_diagram(query: str, requested_outputs: Any = None) -> bool:
    """Prefer a diagram by default, but respect an explicit alternative renderer or opt-out."""
    low = str(query or "").lower().replace("ё", "е")
    if _SITE_NO_DIAGRAM_RE.search(low):
        return False
    # A visual explanation of an interface path is a vector route map, not an image-generation task.
    if _site_navigation_picture_request(query):
        return True
    if re.search(r"(?:только\s+(?:ссылк\w*|код|таблиц\w*|изображен\w*|картинк\w*|график\w*|формул\w*|файл\w*)|only\s+(?:a\s+)?(?:link|code|table|image|graph|formula|file))", low) and not _SITE_EXPLICIT_DIAGRAM_RE.search(low):
        return False
    if _SITE_EXPLICIT_DIAGRAM_RE.search(low):
        return True
    outputs = {
        str(value or "").strip().lower().replace("-", "_")
        for value in (requested_outputs or [])
        if str(value or "").strip()
    } if isinstance(requested_outputs, (list, tuple, set)) else set()
    aliases = {"plot": "graph", "chart": "graph", "generated_image": "image", "image_gallery": "gallery", "latex": "formula", "math": "formula", "svg": "diagram"}
    outputs = {aliases.get(value, value) for value in outputs}
    return not bool(outputs.intersection(_SITE_OTHER_RENDERERS))


def _requested_outputs_from_machine_request(machine_request: Any) -> List[str]:
    """Read output preferences from the actual request/interpretation envelope."""
    root = machine_request if isinstance(machine_request, dict) else getattr(machine_request, "intent", {})
    if not isinstance(root, dict):
        return []
    sources = [root]
    nested = root.get("intent")
    if isinstance(nested, dict):
        sources.append(nested)
    interpretation = root.get("interpretation")
    if isinstance(interpretation, dict):
        sources.append(interpretation)
        nested_intent = interpretation.get("intent")
        if isinstance(nested_intent, dict):
            sources.append(nested_intent)
    for source in sources:
        values = source.get("requested_outputs")
        if isinstance(values, (list, tuple, set)) and values:
            return [str(value) for value in values]
    return []


_ELLIPTICAL_SITE_FOLLOWUP_RE = re.compile(
    r"(?:где\s+(?:это|там|он|она|они|мне|находится)|куда\s+(?:мне\s+)?(?:зайти|нажать|перейти|идти)|"
    r"покажи\s+(?:мне\s+)?(?:это|где|куда|путь)?|как\s+туда|какую\s+кнопку|"
    r"where\s+is\s+it|where\s+do\s+i\s+go|show\s+me\s+where|how\s+do\s+i\s+get\s+there)",
    re.IGNORECASE,
)


def _recent_context_texts(context: Any) -> List[str]:
    """Extract a small, current-turn continuation window, never a full history dump."""
    if not isinstance(context, dict):
        return []
    out: List[str] = []
    for key in ("active_topic", "topic", "anchor", "selected_section", "active_work_branch"):
        value = context.get(key)
        if isinstance(value, str) and value.strip():
            out.append(value.strip()[:900])
        elif isinstance(value, dict):
            for child_key in ("topic", "user", "april", "heading", "summary", "goal", "last_user_text", "last_assistant_answer"):
                child = value.get(child_key)
                if isinstance(child, str) and child.strip():
                    out.append(child.strip()[:900])
    for pair in (context.get("selected_pairs") or [])[:2] if isinstance(context.get("selected_pairs"), list) else []:
        if not isinstance(pair, dict):
            continue
        for key in ("topic", "user", "april", "source_user_text", "source_april_text"):
            child = pair.get(key)
            if isinstance(child, str) and child.strip():
                out.append(child.strip()[:900])
    # Avoid scanning topic indexes or older general history: only the active window
    # and the first two selected pairs may re-anchor an elliptical navigation follow-up.
    return out[:12]


def _referenced_site_area_ids(context: Any) -> List[str]:
    rows = _recent_context_texts(context)
    source = " ".join(rows).lower().replace("ё", "е")
    if not source:
        return []
    ids: List[str] = []
    # Specific current-route clues take precedence over generic words such as "chat".
    for area_id in ("space", "settings", "history", "support", "guide", "deletion", "privacy", "terms", "plans", "how-to-use", "help-center", "memory", "direct", "chat", "tools"):
        hints = _SITE_AREA_HINTS.get(area_id, ())
        if any(hint in source for hint in hints) or any(
            marker in source for marker in {
                "space": ("/space", "community", "сообществ", "private chat"),
                "settings": ("/settings", "личный кабинет", "профиль", "current plan"),
                "history": ("/history", "saved dialogues", "история диалогов", "continue this dialogue"),
                "support": ("/insights?room=support", "contact support", "поддержк"),
                "guide": ("/aprill", "help & information"),
                "deletion": ("/account-deletion", "account & data deletion"),
                "privacy": ("/privacy-policy", "privacy policy"),
                "terms": ("/terms-of-service", "terms of service"),
                "plans": ("plans & payments", "time remaining", "premium"),
                "how-to-use": ("how to use april",),
                "help-center": ("help center",),
                "memory": ("/memory", "memory status"),
                "direct": ("/space/direct/", "private chat"),
                "chat": ("главный чат", "основной чат", "chat with april"),
                "tools": ("/tools",),
            }.get(area_id, ())
        ):
            if area_id not in ids:
                ids.append(area_id)
    return ids[:4]


def prepare_site_help_interpretation(
    interpretation: Dict[str, Any], query: str, question_sequence: Any = None, recent_context: Any = None
) -> bool:
    """Bind site help to Interpretation and select a diagram unless another format is preferred."""
    direct_match = is_site_help_query(query)
    referent_ids: List[str] = []
    if not direct_match and _ELLIPTICAL_SITE_FOLLOWUP_RE.search(str(query or "")):
        relation = _text(recent_context.get("relation")).upper() if isinstance(recent_context, dict) else ""
        if relation in {"CONTINUE", "FOLLOWUP", "CONTINUATION"}:
            referent_ids = _referenced_site_area_ids(recent_context)
            direct_match = bool(referent_ids)
    if not direct_match:
        return False
    intent = interpretation.setdefault("intent", {})
    if not isinstance(intent, dict):
        intent = {}
        interpretation["intent"] = intent
    outputs = intent.get("requested_outputs")
    outputs = list(outputs) if isinstance(outputs, (list, tuple, set)) else ["text"]
    route_picture = _site_navigation_picture_request(query, referent_ids)
    if route_picture:
        # Keep the user's request for a visual explanation, but use the route-aware SVG renderer.
        outputs = [output for output in outputs if str(output).lower().replace("-", "_") not in {"image", "gallery", "generated_image", "image_gallery"}]
        intent["wants_image"] = False
        intent["explicit_generation_request"] = False
        intent["image_operation"] = "none"
        visual = interpretation.get("visual")
        if isinstance(visual, dict):
            visual["generation_required"] = False
            visual["wants_image"] = False
            visual["generator"] = ""
            visual["image_model"] = ""
    wants_diagram = _site_should_render_diagram(query, outputs)
    if "text" not in outputs:
        outputs.insert(0, "text")
    if wants_diagram and "diagram" not in outputs:
        outputs.append("diagram")
    if not wants_diagram:
        diagram_aliases = {"diagram", "svg", "schematic", "flowchart", "scene", "layout", "visual", "renderer_scene", "experimental_diagram"}
        outputs = [output for output in outputs if str(output).lower().replace("-", "_") not in diagram_aliases]
    intent["requested_outputs"] = outputs
    intent["wants_diagram"] = wants_diagram
    intent["site_navigation_help"] = True
    intent["adaptive_visual_policy"] = True
    caps = interpretation.get("routing_capabilities")
    caps = list(caps) if isinstance(caps, (list, tuple, set)) else []
    for capability in ("april_site_help", "site_navigation", "user_guidance"):
        if capability not in caps:
            caps.append(capability)
    if wants_diagram:
        for capability in ("diagram", "geometry"):
            if capability not in caps:
                caps.append(capability)
    else:
        caps = [capability for capability in caps if str(capability).lower() not in {"diagram", "geometry"}]
    interpretation["routing_capabilities"] = caps
    if referent_ids:
        interpretation["site_navigation_referent"] = referent_ids
    interpretation["site_navigation_diagram_policy"] = {
        "enabled": wants_diagram,
        "role": "complement the written navigation instructions",
        "required_payload": "readable responsive SVG plus concrete nodes and directed edges",
        "derive_nodes_from_query_relevant_map_routes": True,
        "never_emit_empty_diagram_shell": True,
        "use_only_map_routes": True,
    }
    if isinstance(question_sequence, list):
        for item in question_sequence:
            if not isinstance(item, dict):
                continue
            step_outputs = item.get("output_types")
            step_outputs = list(step_outputs) if isinstance(step_outputs, (list, tuple, set)) else ["text"]
            if "text" not in step_outputs:
                step_outputs.insert(0, "text")
            if wants_diagram and "diagram" not in step_outputs:
                step_outputs.append("diagram")
            if not wants_diagram:
                diagram_aliases = {"diagram", "svg", "schematic", "flowchart", "scene", "layout", "visual", "renderer_scene", "experimental_diagram"}
                step_outputs = [output for output in step_outputs if str(output).lower().replace("-", "_") not in diagram_aliases]
            if route_picture:
                step_outputs = [output for output in step_outputs if str(output).lower().replace("-", "_") not in {"image", "gallery", "generated_image", "image_gallery"}]
                if "diagram" not in step_outputs:
                    step_outputs.append("diagram")
                item["outputs"] = step_outputs
            item["output_types"] = step_outputs
            item["history_request"] = False if route_picture else item.get("history_request", False)
            if isinstance(item.get("dialogue_search"), dict) and route_picture:
                item["dialogue_search"]["history_request"] = False
                item["dialogue_search"]["search_scope"] = "CURRENT_DIALOGUE"
    structure = interpretation.get("request_structure")
    if isinstance(structure, dict):
        structure["site_navigation_help"] = True
        structure["site_navigation_diagram_required"] = wants_diagram
        if route_picture:
            structure["history_request"] = False
            structure["requested_outputs"] = ["text", "diagram"]
            for sequence_key in ("question_sequence", "presentation_sequence", "answer_sequence"):
                seq = structure.get(sequence_key)
                if isinstance(seq, list):
                    for item in seq:
                        if not isinstance(item, dict):
                            continue
                        key = "output_types" if "output_types" in item or sequence_key == "question_sequence" else "outputs"
                        child_outputs = item.get(key) if isinstance(item.get(key), list) else ["text"]
                        child_outputs = [value for value in child_outputs if str(value).lower().replace("-", "_") not in {"image", "gallery", "generated_image", "image_gallery"}]
                        if "text" not in child_outputs: child_outputs.insert(0, "text")
                        if "diagram" not in child_outputs: child_outputs.append("diagram")
                        item[key] = child_outputs
    if route_picture:
        intent["task"] = "answer_request" if intent.get("task") in {"generate_image", "create_image", "image_generation"} else intent.get("task", "answer_request")
        intent["wants_image"] = False
        intent["wants_diagram"] = True
        intent["requested_outputs"] = ["text", "diagram"]
    return True


def _current_user_query(machine_request: Any) -> str:
    """Extract the current user text before generic orchestration goals or history."""
    if isinstance(machine_request, dict):
        root = machine_request
        conversation = root.get("conversation") if isinstance(root.get("conversation"), dict) else {}
        sources = [root, conversation]
        fallback_goal = root.get("goal")
    else:
        conversation = getattr(machine_request, "conversation", {})
        conversation = conversation if isinstance(conversation, dict) else {}
        sources = [conversation]
        fallback_goal = getattr(machine_request, "goal", "")

    current_keys = ("current_request", "current_text", "query", "user_message", "message", "resolved_request")
    # Never let `goal='answer_user_request'` mask the actual message. This was the
    # reason the room could be selected but still receive no request-scoped site map.
    for source in sources:
        if not isinstance(source, dict):
            continue
        for key in current_keys:
            value = source.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()[:1200]
    if isinstance(fallback_goal, str) and fallback_goal.strip() and fallback_goal.strip().lower() not in {
        "answer_user_request", "answer request", "new request", "user request"
    }:
        return fallback_goal.strip()[:1200]
    return ""


def _select_site_map_excerpt(machine_request: Any) -> Dict[str, Any]:
    """Return only the relevant routes for prompt efficiency; preserve the full map in this room."""
    query = _current_user_query(machine_request).lower().replace("ё", "е")
    selected_ids: list[str] = []
    for area_id, hints in _SITE_AREA_HINTS.items():
        if any(hint in query for hint in hints):
            selected_ids.append(area_id)
    intent = machine_request.get("intent") if isinstance(machine_request, dict) and isinstance(machine_request.get("intent"), dict) else getattr(machine_request, "intent", {})
    intent = intent if isinstance(intent, dict) else {}
    referent_ids = intent.get("site_navigation_referent") if isinstance(intent.get("site_navigation_referent"), list) else []
    referent_ids = [str(value) for value in referent_ids if str(value) in {str(area.get("id")) for area in APRIL_SITE_MAP["areas"]}]
    if referent_ids:
        selected_ids = referent_ids + [area_id for area_id in selected_ids if area_id not in referent_ids and area_id != "guide"]
    if not selected_ids:
        selected_ids = ["guide", "chat", "settings", "history"]
    # Target route order follows the user's wording. The screenshots confirm that
    # History, Support and Community are quick links inside the profile/CURRENT PLAN card.
    if not referent_ids and selected_ids:
        targets = [area_id for area_id in selected_ids if area_id not in {"settings", "chat", "guide", "memory"}]
        targets.sort(key=lambda area_id: min((query.find(hint) for hint in _SITE_AREA_HINTS.get(area_id, ()) if query.find(hint) >= 0), default=10**6))
        if targets and any(area_id in {"history", "space", "support"} for area_id in targets):
            selected_ids = ["settings"] + targets + [area_id for area_id in selected_ids if area_id not in {"settings", *targets, "guide", "memory"}]
    broad_self_help = bool(re.search(
        r"(?:\b(?:april|април)\b.{0,100}\b(?:функци\w*|возможност\w*|устроен\w*|работа\w*|создан\w*|умеешь|умеет|можешь|может)\b|"
        r"(?:what can april do|how does april work|how is april built))",
        query,
        re.IGNORECASE,
    ))
    if broad_self_help and not referent_ids:
        selected_ids = ["chat", "settings", "history", "space", "guide"]
    # Add directly related routes so users can recover to the next useful section.
    areas_by_id = {str(area.get("id")): area for area in APRIL_SITE_MAP["areas"]}
    pending = list(selected_ids)
    for area_id in list(selected_ids):
        area = areas_by_id.get(area_id, {})
        for related in area.get("related", []):
            if related in areas_by_id and related not in pending and len(pending) < 5:
                pending.append(related)
    # Specific route questions get only the profile gateway and requested destinations;
    # do not clutter their diagram with unrelated related routes such as Memory or Support.
    query_targets = [area_id for area_id in selected_ids if area_id in {"settings", "chat", "history", "space", "support", "guide", "plans", "deletion", "privacy", "terms"}]
    if any(area_id not in {"settings", "chat", "guide"} for area_id in query_targets):
        pending = query_targets
    else:
        pending = query_targets + [area_id for area_id in pending if area_id not in query_targets]
    chosen = [areas_by_id[area_id] for area_id in pending if area_id in areas_by_id]
    return {
        "schema": APRIL_SITE_MAP["schema"],
        "source": APRIL_SITE_MAP["source"],
        "matched_query": query[:240],
        "areas": chosen[:5],
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
        if source.get("site_navigation_help") is True:
            return True
    routing = getattr(machine_request, "routing", {}) if not isinstance(machine_request, dict) else machine_request.get("routing", {})
    if isinstance(routing, dict) and routing.get("site_help_requested") is True:
        return True
    return is_site_help_query(_current_user_query(machine_request))



def ensure_site_navigation_response(decoded: Dict[str, Any], machine_request: Any) -> Dict[str, Any]:
    """Deterministically add clickable route links and a real route diagram to UI-help answers.

    This runs after the provider response is decoded but before the canonical SceneContract
    normalizer. It guarantees that navigation help does not depend on the model choosing a
    diagram renderer correctly; the prose answer remains intact and primary.
    """
    if not isinstance(decoded, dict) or not _site_help_requested(machine_request):
        return decoded
    context: Dict[str, Any] = {}
    routing = getattr(machine_request, "routing", {}) if not isinstance(machine_request, dict) else machine_request.get("routing", {})
    if isinstance(routing, dict):
        rooms = routing.get("room_knowledge_context")
        if isinstance(rooms, dict) and isinstance(rooms.get("it"), dict):
            context = rooms["it"]
    if not context:
        context = get_context(machine_request)
    site_map = context.get("site_navigation_map") if isinstance(context, dict) else None
    if not isinstance(site_map, dict):
        return decoded
    areas = [area for area in (site_map.get("areas") or []) if isinstance(area, dict)]
    if not areas:
        return decoded

    # Build a unique list of safe, known relative routes. Never expose a dynamic
    # placeholder such as /space/direct/[friendId] as a literal clickable URL.
    route_rows: List[Dict[str, str]] = []
    seen_paths = set()
    for area in areas:
        area_id = _text(area.get("id"))
        path = _text(area.get("path"))
        label = _text(area.get("label"))
        # The map contains one admin-only reference for architecture/safety context;
        # it must never become a clickable destination for ordinary users.
        if area_id == "admin-support" or path.lower().rstrip("/") == "/admin-profile":
            continue
        if not path or not label or "[" in path or "]" in path:
            if path == "/space/direct/[friendId]":
                path = "/space"
                label = "Личный диалог через сообщество"
            else:
                continue
        if path in seen_paths:
            continue
        seen_paths.add(path)
        route_rows.append({
            "id": area_id or f"route_{len(route_rows)+1}", "path": path, "label": label,
            "purpose": _text(area.get("purpose")),
            "steps": [str(step).strip() for step in area.get("steps", []) if str(step).strip()] if isinstance(area.get("steps"), list) else [],
        })
        if len(route_rows) >= 5:
            break
    if not route_rows:
        return decoded

    answer_key = next((key for key in ("answer", "content", "text", "message") if isinstance(decoded.get(key), str) and decoded[key].strip()), "answer")
    answer = _text(decoded.get(answer_key))
    if not answer:
        for block in (decoded.get("render_blocks") if isinstance(decoded.get("render_blocks"), list) else []):
            if not isinstance(block, dict):
                continue
            block_type = _text(block.get("type") or block.get("artifact_type") or "text").lower()
            if block_type in {"text", "markdown", "message", "message_text"}:
                candidate = _text(block.get("content") or block.get("text") or block.get("markdown"))
                if candidate:
                    answer = candidate
                    answer_key = "answer"
                    break
    if not answer:
        return decoded
    language = _text(
        (getattr(machine_request, "constraints", {}) or {}).get("display_language", "")
        if not isinstance(machine_request, dict) else (machine_request.get("constraints") or {}).get("display_language", "")
    ).lower()
    heading = "Проверенные переходы" if language.startswith(("ru", "uk")) or not language else "Verified links"
    # Always expose a safe route back to the main chat. Add it as a text link even
    # when the selected excerpt only contains a deep-link destination.
    if not any(row["path"] == "/" for row in route_rows):
        route_rows.insert(0, {"id": "chat", "path": "/", "label": "Основной чат April"})
        route_rows = route_rows[:5]
    missing_links = [row for row in route_rows if f"]({row['path']})" not in answer]
    if missing_links:
        label_path_pairs = " · ".join(f"[{row['label']}]({row['path']})" for row in missing_links)
        addition = f"\n\n**{heading}:** {label_path_pairs}."
        answer = answer.rstrip() + addition
        decoded["answer"] = answer
        decoded["content"] = answer
        if answer_key not in {"answer", "content"}:
            decoded[answer_key] = answer

    # When a concrete area is named, state its verified route and next actions
    # explicitly. This corrects an LLM-generated "I cannot find this page" claim
    # when the canonical map does contain the destination.
    query_for_routes = _current_user_query(machine_request).lower().replace("ё", "е")
    targeted_ids = [
        area_id for area_id, hints in _SITE_AREA_HINTS.items()
        if any(hint in query_for_routes for hint in hints)
    ]
    if targeted_ids:
        full_areas = {str(area.get("id")): area for area in APRIL_SITE_MAP.get("areas", []) if isinstance(area, dict)}
        target_area = next((full_areas.get(area_id) for area_id in targeted_ids if full_areas.get(area_id) and area_id != "admin-support"), None)
        if target_area:
            target_path = _text(target_area.get("path"))
            if target_path and "[" not in target_path and "]" not in target_path and target_path.lower().rstrip("/") != "/admin-profile":
                target_label = _text(target_area.get("label")) or "Раздел April"
                target_steps = target_area.get("steps") if isinstance(target_area.get("steps"), list) else []
                safe_steps = [str(step).strip() for step in target_steps if str(step).strip()][:3]
                guide_heading = "Путь по карте April" if heading == "Проверенные переходы" else "Verified route in April"
                route_intro = f"**{guide_heading}:** [{target_label}]({target_path})."
                if safe_steps:
                    route_intro += "\n" + "\n".join(f"{index}. {step}" for index, step in enumerate(safe_steps, 1))
                # Add the deterministic guide when a model misses the path or
                # contradicts the verified map. If a route is already described
                # correctly, leave the model's step sequence unchanged.
                has_target_path = f"]({target_path})" in answer
                contradicts_map = bool(re.search(
                    r"(?:нет[^.\n]{0,140}(?:раздел|экрана|страниц|ссылк|приглашен)|"
                    r"(?:раздел|экран|страниц|ссылк)[^.\n]{0,100}\bнет\b|"
                    r"не\s+могу\s+(?:подтвердить|указать)[^.\n]{0,100}(?:существ|ссылк|путь)|"
                    r"(?:такого|такой)\s+(?:раздела|страницы|ссылки)\s+нет|"
                    r"cannot\s+(?:confirm|find)\s+(?:the\s+)?(?:page|section|link))",
                    answer.lower(),
                ))
                if target_area.get("id") == "space":
                    route_intro += "\nСтраница сообщества указана в проверенной карте сайта; отдельный URL-приглашение в доступной карте не указан."
                if contradicts_map:
                    # Remove only the sentence that denies the verified route; keep
                    # other useful context and let the map-derived route text replace it.
                    denial_sentence = re.compile(
                        r"[^.!?\n]*(?:нет[^.!?\n]{0,140}(?:раздел|экрана|страниц|ссылк|приглашен)|"
                        r"(?:раздел|экран|страниц|ссылк)[^.!?\n]{0,100}\bнет\b|"
                        r"не\s+могу\s+(?:подтвердить|указать)[^.!?\n]{0,100}(?:существ|ссылк|путь)|"
                        r"(?:такого|такой)\s+(?:раздела|страницы|ссылки)\s+нет|"
                        r"cannot\s+(?:confirm|find)\s+(?:the\s+)?(?:page|section|link))[^.!?\n]*[.!?]?",
                        re.IGNORECASE,
                    )
                    corrected = denial_sentence.sub("", answer)
                    corrected = re.sub(r"(?:\n\s*){3,}", "\n\n", corrected).strip()
                    if corrected:
                        answer = corrected
                if not has_target_path or contradicts_map:
                    answer = answer.rstrip() + "\n\n" + route_intro
                    decoded["answer"] = answer
                    decoded["content"] = answer
                    if answer_key not in {"answer", "content"}:
                        decoded[answer_key] = answer

    # For a visual navigation request that names several destinations, provide one ordered
    # how-to sequence in prose as well as the SVG. The route list comes from the actual map
    # and the screenshot-confirmed CURRENT PLAN shortcuts; it is never a generated mock photo.
    if _site_navigation_picture_request(query_for_routes):
        ordered_targets = []
        for area_id, hints in _SITE_AREA_HINTS.items():
            if area_id not in {"space", "history", "support", "chat", "settings", "guide", "plans", "deletion", "privacy", "terms"}:
                continue
            positions = [query_for_routes.find(hint) for hint in hints if query_for_routes.find(hint) >= 0]
            if positions:
                ordered_targets.append((min(positions), area_id))
        ordered_targets = [area_id for _, area_id in sorted(ordered_targets)][:3]
        area_by_id = {str(area.get("id")): area for area in APRIL_SITE_MAP.get("areas", []) if isinstance(area, dict)}
        steps = []
        if any(area_id in {"space", "history", "support"} for area_id in ordered_targets):
            steps.append("Откройте [Настройки и профиль](/settings) — на странице профиля найдите карточку CURRENT PLAN.")
        for area_id in ordered_targets:
            area = area_by_id.get(area_id)
            if not area:
                continue
            route = _text(area.get("path"))
            label = _text(area.get("label"))
            if area_id == "space":
                steps.append(f"Для сообщества нажмите **Community / Сообщество** в карточке CURRENT PLAN или откройте [{label}]({route}).")
            elif area_id == "history":
                steps.append(f"Для истории нажмите **Dialog history / История диалогов** или откройте [{label}]({route}); затем выберите нужную запись и нажмите **Continue this dialogue**.")
            elif area_id == "support":
                steps.append(f"Для поддержки нажмите **Contact support** или откройте [{label}]({route}).")
            elif area_id in {"chat", "guide", "plans", "deletion", "privacy", "terms"} and route:
                steps.append(f"Откройте [{label}]({route}).")
        if steps and not re.search(r"(?:как пройти по интерфейсу|порядок перехода|route steps)", answer, re.IGNORECASE):
            guide = "**Как пройти по интерфейсу:**\n" + "\n".join(f"{index}. {step}" for index, step in enumerate(steps, 1))
            answer = answer.rstrip() + "\n\n" + guide
            decoded["answer"] = answer
            decoded["content"] = answer
            if answer_key not in {"answer", "content"}:
                decoded[answer_key] = answer

    # Build a route graph without duplicating the homepage. From the profile page,
    # the screenshot/map confirms quick links to Chat, History, Support and Community;
    # other selected destinations remain reachable from the main screen.
    nodes: List[Dict[str, Any]] = [{"id": "april_home", "label": "Главный экран April\n/", "kind": "start", "href": "/"}]
    edges: List[Dict[str, Any]] = []
    node_by_area: Dict[str, str] = {"chat": "april_home"}
    for index, row in enumerate(route_rows, 1):
        if row["path"] == "/":
            node_by_area[row["id"]] = "april_home"
            continue
        node_id = re.sub(r"[^a-zA-Z0-9_-]+", "_", row["id"] or f"route_{index}").strip("_") or f"route_{index}"
        if node_id == "april_home":
            node_id = f"route_{index}"
        # Keep IDs unique if two map areas share the same parent-page URL.
        existing_ids = {item["id"] for item in nodes}
        if node_id in existing_ids:
            node_id = f"{node_id}_{index}"
        nodes.append({"id": node_id, "label": f"{row['label']}\n{row['path']}", "kind": "page", "href": row["path"]})
        node_by_area[row["id"]] = node_id
    settings_node = node_by_area.get("settings")
    if settings_node:
        edges.append({"from": "april_home", "to": settings_node, "label": "Открыть профиль/настройки"})
        for area_id, edge_label in (("chat", "Chat with April"), ("history", "Dialog history"), ("support", "Contact support"), ("space", "Community")):
            target = node_by_area.get(area_id)
            if target and target != settings_node:
                edges.append({"from": settings_node, "to": target, "label": edge_label})
    for area_id, target in node_by_area.items():
        if area_id == "settings" or target == "april_home":
            continue
        # Avoid duplicate edges where the profile's confirmed shortcuts already lead
        # to the destination; otherwise show a safe recovery path from the homepage.
        if not any(edge["to"] == target for edge in edges):
            edges.append({"from": "april_home", "to": target, "label": "Открыть раздел"})
    diagram_payload = {
        "title": "Карта переходов April",
        "description": "Главный экран и проверенные маршруты, отобранные по текущему вопросу пользователя.",
        "representation": "navigation_flow",
        # The portrait layout stays readable on phone screens. SVG is generated
        # from these same route nodes/edges; this is not a pre-baked topic diagram.
        "layout": {"direction": "TB", "rankdir": "TB", "spacing": "comfortable", "responsive": True},
        "nodes": nodes,
        "edges": edges,
        "navigation_map_schema": site_map.get("schema", "april.site_navigation.v1"),
        "renderer": "DiagramRenderer",
    }
    blocks = decoded.get("render_blocks")
    blocks = list(blocks) if isinstance(blocks, list) else []
    # A prompt/caption-only image block is not a rendered image. On route guidance it is almost always the LLM trying to send a fake raster substitute for a concrete UI map.
    query_for_visual_policy = _current_user_query(machine_request)
    if _site_help_requested(machine_request):
        def _has_site_image_source(value: Any, depth: int = 0) -> bool:
            if depth > 5:
                return False
            if isinstance(value, str):
                candidate = value.strip()
                return bool(candidate and (candidate.startswith(("data:image/", "https://", "http://", "/")) or len(candidate) > 256 and re.fullmatch(r"[A-Za-z0-9+/=\s]+", candidate)))
            if isinstance(value, (list, tuple)):
                return any(_has_site_image_source(item, depth + 1) for item in value)
            if isinstance(value, dict):
                allowed = {"src", "url", "image_url", "image_base64", "base64", "data_uri", "data", "images", "gallery", "items", "payload", "artifact", "artifacts", "source", "media"}
                return any(str(key).lower().replace("-", "_") in allowed and _has_site_image_source(child, depth + 1) for key, child in value.items())
            return False
        cleaned_blocks = []
        for block in blocks:
            if not isinstance(block, dict):
                continue
            block_kind = _text(block.get("type") or block.get("artifact_type")).lower()
            if block_kind in {"image", "gallery", "generated_image"} and not _has_site_image_source(block):
                continue
            cleaned_blocks.append(block)
        blocks = cleaned_blocks
    diagram_explanation = (
        "Диаграмма показывает, откуда начать и какие проверенные разделы доступны по текущему вопросу. Нажимайте ссылки в текстовом ответе: стрелки объясняют переход, а не выполняют его автоматически."
        if language.startswith(("ru", "uk")) or not language else
        "This diagram shows the starting screen and verified destinations relevant to your question. Use the links in the text; arrows explain navigation and do not click automatically."
    )
    current_query_for_render = _current_user_query(machine_request)
    requested_outputs_for_render = _requested_outputs_from_machine_request(machine_request)
    render_navigation_diagram = _site_should_render_diagram(current_query_for_render, requested_outputs_for_render)
    if render_navigation_diagram:
        try:
            from blocks.C_DIAGRAM_ROOM import ensure_readable_diagram_payload
            diagram_payload = ensure_readable_diagram_payload(diagram_payload, title=diagram_payload["title"])
        except Exception:
            # Preserve the source node/edge payload if optional SVG conversion fails.
            pass
        diagram_renderer = str(diagram_payload.get("renderer") or "DiagramRenderer")
        if (diagram_payload.get("svg") or diagram_payload.get("svg_payload")) and diagram_renderer in {"", "DiagramRenderer", "diagram"}:
            diagram_renderer = "SvgBlock"
        diagram_block = {
            "type": "diagram", "artifact_type": "diagram", "renderer": diagram_renderer, "viewer": diagram_renderer,
            "title": diagram_payload["title"], "payload": diagram_payload,
            "explanation": diagram_explanation, "source_room": "C_IT_ROOM", "integrity_repaired": True,
        }
        existing_index = next((i for i, block in enumerate(blocks) if isinstance(block, dict) and _text(block.get("type") or block.get("artifact_type")).lower() == "diagram"), None)
        if existing_index is None:
            blocks.append(diagram_block)
        else:
            existing = blocks[existing_index]
            merged = dict(existing)
            merged.update(diagram_block)
            # Keep per-step placement metadata if the model supplied it.
            for key in ("step_index", "step_title", "sequence_index", "topic_group", "block_id"):
                if key in existing:
                    merged[key] = existing[key]
            blocks[existing_index] = merged
    # Keep route links visible in the actual SceneContract text renderer, not
    # only in the top-level answer field. For a one-text-block answer, synchronize
    # that block; for multi-section answers, add a separate link block to avoid
    # flattening or duplicating the explanatory sections.
    text_indexes = [
        i for i, block in enumerate(blocks)
        if isinstance(block, dict) and _text(block.get("type") or block.get("artifact_type")).lower() in {"text", "markdown", "message", "message_text"}
    ]
    if len(text_indexes) == 1:
        text_block = blocks[text_indexes[0]]
        text_key = next((key for key in ("content", "text", "markdown") if key in text_block), "content")
        # The prose is the primary answer; synchronize the visible text component
        # even when the model already included some (but not all) route links.
        text_block[text_key] = answer
    elif not text_indexes:
        blocks.insert(0, {
            "type": "text", "artifact_type": "text", "renderer": "MessageTextBlock", "viewer": "MessageTextBlock",
            "title": "Инструкция", "content": answer, "source_room": "C_IT_ROOM",
        })
    elif missing_links:
        links_text = f"**{heading}:** " + " · ".join(
            f"[{row['label']}]({row['path']})" for row in missing_links
        ) + "."
        blocks.insert(max(text_indexes) + 1, {
            "type": "text", "artifact_type": "text", "renderer": "MessageTextBlock", "viewer": "MessageTextBlock",
            "title": heading, "content": links_text, "source_room": "C_IT_ROOM",
        })
    decoded["render_blocks"] = blocks
    return decoded


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
            "Answer April interface-navigation questions from site_navigation_map; use the current question as the retrieval key.",
            "Give a clickable Markdown link using the exact relative path, then ordered steps with visible card/button labels.",
            "Never invent a base domain or unverified anchor. If a card's exact URL is unknown, link its known parent page and name the card to click.",
            "If a page is marked empty/unimplemented, state that limitation and offer the verified fallback route.",
        ])
        query = _current_user_query(machine_request)
        requested_outputs = _requested_outputs_from_machine_request(machine_request)
        if _site_should_render_diagram(query, requested_outputs):
            prompt_fragments.extend([
                "Complement site-navigation help with one concrete DiagramRenderer diagram built from the query-relevant routes; the written instructions remain the main answer.",
                "The diagram must contain a responsive mobile SVG generated from its route nodes/edges, real directed connections and concise labels. Never emit an empty renderer shell, a tiny corner graph, or a fixed unrelated template.",
            ])
    diagram_hint = help_active and _site_should_render_diagram(
        _current_user_query(machine_request), _requested_outputs_from_machine_request(machine_request)
    )
    return {
        "room": ROOM_ID,
        "knowledge_context": context,
        "prompt_fragments": prompt_fragments,
        "artifact_hints": {
            "text": True, "code": True, "table": True, "links": True, "diagram": diagram_hint, "graph": False,
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
