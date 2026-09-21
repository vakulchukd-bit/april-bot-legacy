"""
APRIL INTERPRETATION LAYER — QUANTUM MATRIX ENGINE

Single semantic engine for:
input -> matrix interpretation -> evidence packet -> QUANTUM_PROCESSOR
      -> existing provider/rooms -> C_ARTIFACT_CONTRACT -> April Web

The interpretation layer never owns routing, providers, renderers, room execution,
or final response generation. Public compatibility helpers remain available so
downstream imports can continue using the same single route.
"""
from __future__ import annotations
from blocks.C_ARTIFACT_CONTRACT import WEB_RENDERER_REGISTRY, WEB_RENDERER_REGISTRY_VERSION
import os
import re
import threading
import time
from dataclasses import dataclass
from copy import deepcopy
from collections import Counter
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Dict, List, Sequence
try:
    import numpy as np
except Exception:
    np = None
try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
except Exception:
    TfidfVectorizer = None
    cosine_similarity = None
try:
    import spacy
except Exception:
    spacy = None
try:
    import stanza
    from stanza.pipeline.multilingual import MultilingualPipeline
    from spacy.language import Language
except Exception:
    stanza = None
    MultilingualPipeline = Any
    Language = Any
try:
    from sentence_transformers import SentenceTransformer
except Exception:
    SentenceTransformer = None
try:
    from transformers import pipeline as hf_pipeline
except Exception:
    hf_pipeline = None
try:
    from nltk.stem.snowball import SnowballStemmer
except Exception:
    SnowballStemmer = None
RESPONSE_COMPLEXITY_LOW = 'LOW'
RESPONSE_COMPLEXITY_MEDIUM = 'MEDIUM'
RESPONSE_COMPLEXITY_HIGH = 'HIGH'
DECISION_OWNER = 'QUANTUM_PROCESSOR'
VISUAL_PRODUCTION_HYPOTHESES = {'image_generation': 'Пользователь просит именно сгенерировать, создать или получить новое отдельное изображение, фотографию, иллюстрацию или визуальную сцену по описанию; результатом должны стать новые пиксели, а не показ существующего файла и не простая схема.', 'diagram': 'Пользователь просит нарисовать, изобразить или построить простой визуальный объект, эскиз, схему, примитивную иллюстрацию или базовую форму, которую можно выразить структурированными диаграммными примитивами без отдельной генеративной фотосцены.', 'image_present': 'Пользователь просит показать, вывести, отобразить или повторно использовать уже существующую картинку, фотографию или визуальный артефакт, а не создавать новый.', 'visual_analysis': 'Пользователь просит исследовать, понять, описать, сравнить или проанализировать существующее изображение или визуальный артефакт.'}
TRANSPORT_NAME = 'transport_state'
INTERPRETATION_ENGINE_VERSION = 'quantum_interpretation_engine_v18_scene_blueprint_single_signal_v1'
print('🧠 APRIL INTERPRETATION BUILD:', INTERPRETATION_ENGINE_VERSION)
SEMANTIC_MODEL_NAME = os.getenv('APRIL_SENTENCE_MODEL', 'sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2')
NLI_MODEL_NAME = os.getenv('APRIL_ZERO_SHOT_MODEL', 'MoritzLaurer/mDeBERTa-v3-base-mnli-xnli')
SPACY_MODEL_NAME = os.getenv('APRIL_SPACY_MODEL', 'xx_ent_wiki_sm')
APRIL_FAST_SEMANTIC_MODE = os.getenv('APRIL_FAST_SEMANTIC_MODE', '1').strip().lower() in {'1', 'true', 'yes', 'on'}
APRIL_ENABLE_HEAVY_HOTPATH = os.getenv('APRIL_ENABLE_HEAVY_HOTPATH', '0').strip().lower() in {'1', 'true', 'yes', 'on'}
DIALOGUE_LABELS = ('identity', 'greeting', 'question', 'request', 'reformulation', 'continuation', 'correction', 'reference', 'affirmation', 'rejection', 'new_topic', 'statement', 'independent', 'memory_query')
# Words that express the user's action on a subject. They are not the subject
# themselves and therefore cannot become the active dialogue referent. This
# vocabulary is semantic-state hygiene, not a continuation trigger table.
DIALOGUE_TASK_FUNCTION_WORDS = {
    'дай', 'дайте', 'дать', 'напиши', 'написать', 'покажи', 'показать',
    'создай', 'создать', 'сделай', 'сделать', 'нарисуй', 'нарисовать',
    'объясни', 'объяснить', 'опиши', 'описать', 'расскажи', 'рассказать',
    'найди', 'найти', 'сравни', 'сравнить', 'расчитай', 'расчитать',
    'вычисли', 'вычислить', 'построй', 'построить', 'получи', 'получить',
    'изобрази', 'изобразить', 'измени', 'изменить', 'исправь', 'исправить',
    'добавь', 'добавить', 'убери', 'убрать', 'перепиши', 'переписать',
    'сгенерируй', 'сгенерировать', 'проверь', 'проверить', 'составь',
    'составить', 'перечисли', 'перечислить', 'на', 'и', 'а', 'но', 'или',
}
REPRESENTATION_HYPOTHESES = {'text': 'the user wants a normal textual answer', 'table': 'the user wants the information represented as a table', 'graph': 'the user wants the information represented as a graph or chart', 'diagram': 'the user wants a schematic or diagram with connected elements', 'formula': 'the user wants a mathematical formula or mathematical notation', 'image': 'the user wants an image or generated picture', 'gallery': 'the user wants multiple images or a gallery', 'code': 'the user wants executable source code', 'link': 'the user wants a link or web resource'}
SEMANTIC_TURN_PROTOTYPES = {'identity': 'dialogue act: identity request directed at the assistant', 'greeting': 'dialogue act: opening social exchange with no task dependency', 'question': 'dialogue act: information seeking or unresolved inquiry', 'request': 'dialogue act: task specification requiring an action or result', 'continuation': 'dialogue act: current turn depends on the preceding task or result and develops it', 'reformulation': 'dialogue act: current turn restates or reshapes the preceding task without starting a separate task', 'correction': 'dialogue act: current turn changes or repairs a parameter or result of the preceding task', 'reference': 'dialogue act: current turn identifies an antecedent in the preceding exchange and operates on it', 'artifact_reference': 'dialogue act: current turn depends on a previously produced structured result or artifact', 'memory_query': 'dialogue act: current turn requests recovery of information from prior dialogue', 'affirmation': 'dialogue act: current turn accepts or confirms the preceding result', 'rejection': 'dialogue act: current turn rejects or replaces the preceding result', 'new_topic': 'dialogue act: current turn establishes a task independent of the preceding exchange', 'statement': 'dialogue act: declarative content without a required discourse dependency', 'independent': 'dialogue act: self-contained task whose required information is present in the current turn'}
REPRESENTATION_HYPOTHESES = {'text': 'обычный текстовый ответ объяснение рассказ описание; the user wants a normal textual answer', 'table': 'таблица таблицу табличный формат строки столбцы колонки; information represented as a table', 'graph': 'график графика chart plot graph кривая кривые функция; information represented as a graph or chart', 'diagram': 'схема чертёж технический чертёж рисунок построение геометрическая фигура треугольник квадрат круг окружность вершины стороны углы длина сантиметр см соединение элементов блоки связи последовательность процесса подключение проводов источник питания выключатель лампа электрическая цепь; a technical or geometric drawing, construction diagram, schematic, wiring diagram, connected structure, or process diagram', 'formula': 'формула уравнение математическое выражение математическая запись равенство обозначение величин степени корни E mc2; a mathematical formula, equation, notation, or quantitative relationship', 'image': 'изображение картинка рисунок иллюстрация создать изображение фотография; an image or generated picture', 'gallery': 'несколько изображений много картинок подборка галерея набор карточек сравнение изображений; multiple images, a gallery, or an image collection', 'code': 'код программный код функция программа реализация python; executable source code or software implementation', 'link': 'ссылка адрес сайта веб ресурс открыть ресурс интернет источник; a link or web resource'}
DOMAIN_HYPOTHESES = {'biology': 'биология живые организмы клетки генетика животные растения; biology living organisms genetics', 'chemistry': 'химия вещества реакции молекулы атомы химические процессы; chemistry substances reactions molecules', 'physics': 'физика энергия сила движение скорость масса поля; physics energy forces motion', 'engineering': 'инженерия конструкции проектирование система устройство архитектура; engineering design construction', 'it': 'программирование компьютер software код алгоритм приложение система; computing programming software', 'literature': 'литература писатель поэзия роман стихотворение произведение; literature writing poetry authors', 'politics': 'политика государство правительство выборы закон; politics government', 'news': 'новости текущие события последние события; current events news', 'social': 'общество социальные темы люди отношения; society social topics', 'web': 'интернет сайт веб поиск онлайн ресурс страница; web search online resource'}
CAPABILITY_HYPOTHESES = {'exploration': 'анализ сравнение исследование изучение разбор выводы; analysis comparison investigation', 'web': 'поиск в интернете онлайн ресурс сайт веб информация; web search online resource', 'code': 'код программирование программная реализация функция python; programming code implementation', 'information': 'объяснение информация фактический ответ что означает разъяснение; explanation factual answer', 'discussion': 'обсуждение мнение рассуждение позиция аргументы; discussion opinion reasoning', 'space': 'пространство сцена композиция визуальная структура расположение элементов; spatial scene composition'}
SCENE_MATRIX_LABELS = ('text', 'table', 'graph', 'diagram', 'formula', 'image', 'gallery', 'code', 'link')
SCENE_MATRIX_FEATURES = ('dialogue', 'representation', 'domain', 'capability', 'continuity', 'context', 'modality')
_SCENE_WEIGHTS = ((0.12, 0.55, 0.03, 0.2, 0.04, 0.03, 0.03), (0.08, 0.62, 0.03, 0.2, 0.02, 0.03, 0.02), (0.04, 0.68, 0.05, 0.16, 0.02, 0.03, 0.02), (0.04, 0.62, 0.06, 0.2, 0.02, 0.04, 0.02), (0.03, 0.7, 0.07, 0.16, 0.01, 0.02, 0.01), (0.03, 0.72, 0.03, 0.17, 0.01, 0.02, 0.02), (0.03, 0.74, 0.03, 0.16, 0.01, 0.02, 0.01), (0.02, 0.7, 0.03, 0.22, 0.01, 0.01, 0.01), (0.02, 0.66, 0.05, 0.22, 0.01, 0.03, 0.01))
SCENE_MATRIX_CAPABILITY = {'text': 'information', 'table': 'information', 'graph': 'exploration', 'diagram': 'space', 'formula': 'information', 'image': 'space', 'gallery': 'space', 'code': 'code', 'link': 'web'}
SCENE_MATRIX_DOMAIN_BIAS = {'biology': {'graph': 0.08, 'table': 0.06, 'diagram': 0.08}, 'chemistry': {'formula': 0.1, 'table': 0.05, 'diagram': 0.05}, 'physics': {'graph': 0.09, 'formula': 0.09, 'diagram': 0.05}, 'engineering': {'diagram': 0.1, 'graph': 0.06, 'table': 0.04}, 'it': {'code': 0.1, 'diagram': 0.06, 'table': 0.04}, 'literature': {'text': 0.08}, 'politics': {'table': 0.06, 'graph': 0.06}, 'news': {'link': 0.05, 'table': 0.05, 'graph': 0.05}, 'social': {'table': 0.04, 'graph': 0.04}, 'web': {'link': 0.1}}
REPRESENTATION_UNIVERSE = ('text', 'table', 'graph', 'diagram', 'formula', 'image', 'gallery', 'code', 'link', 'audio', 'video', 'file', 'action', 'scene', 'memory', 'visual_context')
STRUCTURED_REPRESENTATIONS = tuple((x for x in REPRESENTATION_UNIVERSE if x != 'text'))
OPERATION_HYPOTHESES = {'answer': 'ответить объяснить рассказать сообщить дать информацию', 'build': 'создать построить сформировать нарисовать начертить изобразить результат', 'present': 'показать отобразить продемонстрировать вывести представить результат', 'compare': 'сравнить сопоставить различия сходства', 'modify': 'изменить исправить обновить переделать дополнить', 'retrieve': 'найти получить ресурс источник ссылку документ', 'calculate': 'арифметическая операция над числовыми величинами: вычисление, сложение, вычитание, умножение, деление, отношение, процентное изменение, получение числового результата; arithmetic calculation over numeric quantities including addition, subtraction, multiplication, division, ratios and percentage change', 'analyze': 'проанализировать разобрать исследовать проверить', 'explain': 'объяснить объясни объяснение разъяснить разъясни пояснить поясни растолковать опиши описать описание как работает почему смысл принцип расскажи', 'summarize': 'суммировать сократить основные пункты', 'list': 'перечислить список варианты'}
OBJECT_HYPOTHESES = {'graph': 'график plot chart curve series числовая визуализация', 'diagram': 'схема чертёж технический чертёж построение геометрическая фигура треугольник квадрат круг окружность вершины стороны углы длина сантиметр см блоки связи соединения проводка электрическая цепь процесс', 'table': 'таблица строки столбцы колонки структурированные данные сравнение', 'formula': 'формула уравнение математическое выражение notation', 'link': 'ссылка URL адрес сайта веб ресурс источник', 'code': 'код программа функция скрипт', 'image': 'изображение картинка рисунок иллюстрация фотография портрет художественная картинка', 'gallery': 'галерея подборка несколько изображений', 'file': 'файл документ вложение', 'audio': 'аудио звук голос запись', 'video': 'видео ролик запись', 'text': 'текст обычный ответ объяснение описание', 'action': 'действие интерактивная операция'}
GOAL_HYPOTHESES = {'visualize': 'увидеть визуально показать наглядно кривые схему', 'organize': 'структурировать упорядочить данные строки столбцы', 'present': 'представить вывести отобразить результат', 'understand': 'понять разобраться объяснение смысл', 'obtain': 'получить ресурс ссылку файл', 'transform': 'изменить преобразовать результат', 'decide': 'выбрать сопоставить варианты'}
VISUAL_SCHEMA_HYPOTHESES = {'text_schema': 'текстовая схема ASCII схема текстовая блок-схема последовательность шагов стрелки пункты обозначения узлы связи в тексте; textual schematic or ASCII-style text schema using characters and arrows', 'function': 'mathematical function equation dependency f(x) y of x curve coordinate plot; mathematical function against an axis', 'series': 'ряд данных последовательность измерений значения изменение динамика тренд временной ряд развитие по оси; ordered measurements or changing values', 'timeline': 'временная шкала хронология история периоды эпохи эры события даты раньше позже начало конец продолжительность последовательность во времени развитие существование вымирание; temporal history chronology eras periods dates and events', 'scatter': 'paired observations numeric variables relationship correlation distribution individual points; relationship between two numeric variables', 'network': 'entities connected by relationships nodes edges topology dependencies connections; network of related entities', 'matrix': 'rows columns cells heatmap two dimensional array intensities crossing dimensions; matrix or heatmap', 'categorical': 'категории группы сравнение ранжирование дискретные значения подписи количество по категориям; categorical comparison'}
REPRESENTATION_ALIASES = {'chart': 'graph', 'plot': 'graph', 'schematic': 'diagram', 'flowchart': 'diagram', 'math': 'formula', 'equation': 'formula', 'url': 'link', 'link_card': 'link', 'media': 'gallery'}

def _clean_representation(value: Any) -> str:
    value = str(value or '').strip().lower()
    value = REPRESENTATION_ALIASES.get(value, value)
    return value if value in REPRESENTATION_UNIVERSE else ''


# ----------------------------------------------------------------
# Canonical Scene Blueprint
# ----------------------------------------------------------------
# Interpretation owns semantic meaning and the ordered set of semantic
# representations. It does NOT execute renderers. The blueprint is the
# hand-off puzzle that the Quantum Processor later composes into one scene.
SCENE_RENDERER_MAP = {
    'text': 'MessageTextBlock',
    'markdown': 'MessageTextBlock',
    'formula': 'MessageTextBlock',
    'table': 'TableBlock',
    'graph': 'GraphBlock',
    'diagram': 'GalleryBlock',
    'image': 'GalleryBlock',
    'gallery': 'GalleryBlock',
    'code': 'CodeBlock',
    'link': 'LinkCard',
    'file': 'LinkCard',
    'audio': 'MessageTextBlock',
    'video': 'MessageTextBlock',
    'action': 'MessageTextBlock',
    'scene': 'GalleryBlock',
    'memory': 'MessageTextBlock',
    'visual_context': 'GalleryBlock',
}

SCENE_ROLE_MAP = {
    'text': 'answer',
    'formula': 'quantitative_model',
    'table': 'source_data',
    'graph': 'data_visualization',
    'diagram': 'structural_visualization',
    'image': 'visualization',
    'gallery': 'visual_collection',
    'code': 'implementation',
    'link': 'resource',
    'file': 'resource',
    'audio': 'media',
    'video': 'media',
    'action': 'interaction',
    'scene': 'composite_visual',
    'memory': 'context_reference',
    'visual_context': 'visual_evidence',
}


def _scene_clean_outputs(values: Any) -> list[str]:
    """Normalize semantic outputs once, preserving first-seen order."""
    result: list[str] = []
    aliases = {'markdown': 'text', 'chart': 'graph', 'plot': 'graph', 'schematic': 'diagram', 'math': 'formula', 'url': 'link'}
    for raw in values or []:
        key = aliases.get(_clean_representation(raw), _clean_representation(raw))
        if not key or key not in REPRESENTATION_UNIVERSE:
            continue
        if key not in result:
            result.append(key)
    # A specialized visual/structured result remains one answer only when a
    # human-readable text node is part of the same scene. It is a companion,
    # never a second response.
    if result and any(item != 'text' for item in result) and 'text' not in result:
        result.insert(0, 'text')
    return result or ['text']


def build_scene_blueprint(
    *,
    text: str,
    requested_outputs: list[str] | None = None,
    scene_composition: list[dict[str, Any]] | None = None,
    production_representation: str = 'text',
    active_topic: str = '',
    active_goal: str = '',
    subject: str = '',
    semantic_summary: str = '',
    entities: list[Any] | None = None,
    relations: list[Any] | None = None,
    dimensions: dict[str, Any] | None = None,
    dialogue: dict[str, Any] | None = None,
    flow_id: str = '',
) -> dict[str, Any]:
    """Create the single semantic scene blueprint consumed by the Processor.

    This function only assembles semantic relationships and presentation
    expectations. No renderer is executed and no provider call is performed.
    """
    composition = scene_composition or []
    source_outputs: list[str] = []
    for item in composition:
        if isinstance(item, dict):
            source_outputs.append(_clean_representation(item.get('representation')))
    source_outputs.extend(requested_outputs or [])
    if production_representation:
        source_outputs.append(production_representation)
    outputs = _scene_clean_outputs(source_outputs)

    # Preserve explicit segment ordering when available, then append missing
    # outputs deterministically. This prevents graph/table/image from replacing
    # each other just because one representation has the highest score.
    ordered: list[str] = []
    segment_map: dict[str, dict[str, Any]] = {}
    for item in composition:
        if not isinstance(item, dict):
            continue
        rep = _clean_representation(item.get('representation'))
        if rep:
            segment_map.setdefault(rep, item)
            if rep not in ordered:
                ordered.append(rep)
    for rep in outputs:
        if rep not in ordered:
            ordered.append(rep)
    outputs = _scene_clean_outputs(ordered)

    nodes: list[dict[str, Any]] = []
    for index, rep in enumerate(outputs):
        source = segment_map.get(rep, {})
        role = SCENE_ROLE_MAP.get(rep, 'supporting')
        node = {
            'block_id': f'scene_node_{index + 1}',
            'render_id': f'scene_render_{index + 1}',
            'type': rep,
            'representation': rep,
            'role': role,
            'renderer': SCENE_RENDERER_MAP.get(rep, 'MessageTextBlock'),
            'sequence_index': index,
            'segment_index': int(source.get('segment_index', index + 1) or index + 1),
            'semantic_source': source.get('semantic_source') or 'canonical_scene_blueprint',
            'segment_text': str(source.get('segment_text') or '').strip(),
            'continuation': bool((dialogue or {}).get('continuation')),
            'topic_group': str(active_topic or '').strip(),
            'flow_id': str(flow_id or '').strip(),
        }
        node['content_role'] = 'human_answer' if rep == 'text' else 'specialized_result'
        node['presentation'] = {
            'renderer': node['renderer'],
            'engine': 'McDowell' if node['renderer'] == 'MessageTextBlock' else 'specialized_scene_renderer',
            'math_engine': 'KaTeX' if rep == 'formula' else None,
            'shared_scene': True,
            'payload_owned_by_processor': True,
        }
        nodes.append(node)

    node_by_type = {node['type']: node['block_id'] for node in nodes}
    scene_relations: list[dict[str, Any]] = []
    text_id = node_by_type.get('text')
    for node in nodes:
        rep = node['type']
        if rep == 'text' or not text_id:
            continue
        scene_relations.append({'from': text_id, 'relation': 'explains', 'to': node['block_id']})
    if 'table' in node_by_type and 'graph' in node_by_type:
        scene_relations.append({'from': node_by_type['table'], 'relation': 'feeds', 'to': node_by_type['graph']})
    if 'formula' in node_by_type and 'graph' in node_by_type:
        scene_relations.append({'from': node_by_type['formula'], 'relation': 'describes', 'to': node_by_type['graph']})
    if 'diagram' in node_by_type and 'text' in node_by_type:
        scene_relations.append({'from': node_by_type['diagram'], 'relation': 'illustrates', 'to': text_id})
    if 'image' in node_by_type and 'graph' in node_by_type:
        scene_relations.append({'from': node_by_type['image'], 'relation': 'complements', 'to': node_by_type['graph']})
    if 'gallery' in node_by_type and 'text' in node_by_type:
        scene_relations.append({'from': node_by_type['gallery'], 'relation': 'illustrates', 'to': text_id})

    semantic_entities = [x for x in (entities or []) if x not in (None, '', {})][:24]
    semantic_relations = [x for x in (relations or []) if x not in (None, '', {})][:32]
    return {
        'version': 'scene_blueprint_v1',
        'scene_kind': 'composite' if len(outputs) > 1 else outputs[0],
        'root': 'current_turn',
        'topic_group': str(active_topic or '').strip(),
        'flow_id': str(flow_id or '').strip(),
        'goal': str(active_goal or '').strip(),
        'subject': str(subject or '').strip(),
        'semantic_summary': str(semantic_summary or text or '').strip()[:4000],
        'representations': outputs,
        'preferred_representation': _clean_representation(production_representation) or outputs[0],
        'nodes': nodes,
        'relations': scene_relations,
        'semantic_entities': semantic_entities,
        'semantic_relations': semantic_relations,
        'dimensions': deepcopy(dimensions or {}),
        'dialogue': deepcopy(dialogue or {}),
        'layout': {
            'mode': 'flow',
            'density': 'adaptive',
            'shared_scene': True,
            'free_width': True,
            'allow_inline_text': True,
            'allow_wide_visuals': True,
            'frames_are_optional': True,
        },
        'ownership': {
            'semantic_owner': 'INTERPRETATION_LAYER',
            'composition_owner': 'QUANTUM_PROCESSOR',
            'renderer_owner': 'APRIL_WEB',
            'one_response': True,
            'one_scene': True,
            'one_signal': True,
        },
    }


class QuantumTurnMeaningEngine:
    """
    Persistent semantic understanding of one completed USER -> APRIL turn.

    The engine stores meaning, not routing commands:
      - what the user was trying to accomplish;
      - what April actually answered;
      - which objects/concepts were developed;
      - which representations were actually produced;
      - which semantic thread the turn leaves active.

    A later request is compared with this meaning before older history is considered.
    This makes dialogue development a continuation of meaning rather than a search
    for a matching phrase or a predeclared memory state.
    """
    VERSION = 'quantum_turn_meaning_engine_v1'

    @staticmethod
    def _clean(value: Any, limit: int=5000) -> str:
        return re.sub('\\s+', ' ', str(value or '').strip())[:limit]

    @staticmethod
    def _block_type(block: Any) -> str:
        if not isinstance(block, dict):
            return ''
        return _clean_representation(block.get('type') or block.get('artifact_type') or block.get('representation'))

    @classmethod
    def _semantic_terms(cls, profile: dict[str, Any], key: str, limit: int=8) -> list[dict[str, Any]]:
        values = profile.get(key)
        if not isinstance(values, dict):
            return []
        ranked = sorted(((str(name), float(score or 0.0)) for name, score in values.items()), key=lambda item: item[1], reverse=True)
        return [{'value': name, 'strength': round(score, 6)} for name, score in ranked[:limit] if name]

    @classmethod
    def build(cls, user_request: str, answer: str, *, render_blocks: list[dict[str, Any]] | None=None, summary: str='', turn_id: Any=None, scene_id: str='', semantic_engine: Any=None) -> dict[str, Any]:
        user_request = cls._clean(user_request, 2600)
        answer = cls._clean(answer, 7000)
        blocks = [x for x in render_blocks or [] if isinstance(x, dict)]
        engine = semantic_engine
        user_profile = {}
        answer_profile = {}
        try:
            if engine is not None:
                user_profile = engine.measure(user_request)
                answer_profile = engine.measure(answer, previous_user=user_request, active_topic=user_request)
        except Exception:
            user_profile = {}
            answer_profile = {}
        actual_representations = []
        for block in blocks:
            kind = cls._block_type(block)
            if kind and kind not in {'text', 'markdown'} and (kind not in actual_representations):
                actual_representations.append(kind)
        topic = ''
        # The user's request owns the task meaning. April's answer remains
        # result evidence, but cannot silently redefine the active topic.
        goal = cls._clean(user_profile.get('best_goal'), 300) or 'understand'
        operation = cls._clean(user_profile.get('best_operation'), 300) or 'answer'
        objects = []
        for profile in (user_profile, answer_profile):
            if not profile:
                continue
            for item in cls._semantic_terms(profile, 'object_scores', 8):
                if item['value'] not in {x['value'] for x in objects}:
                    objects.append(item)
        content_tokens = QuantumContextUnderstandingEngine._content_tokens(f'{user_request} {answer}')
        term_counts = Counter(content_tokens)
        salient_terms = [token for token, _ in sorted(term_counts.items(), key=lambda item: (item[1], len(item[0])), reverse=True) if token][:8]
        semantic_entity_terms = []
        try:
            entity_packets = QuantumContextUnderstandingEngine._entities(f'{user_request} {answer}')
            semantic_entity_terms = [cls._clean(item.get('value'), 240) for item in entity_packets if isinstance(item, dict) and item.get('value') and (item.get('type') in {'proper_name', 'formula_symbol', 'number_expression', 'code_identifier'})]
        except Exception:
            semantic_entity_terms = []
        answer_content = QuantumContextUnderstandingEngine._content_tokens(answer)
        user_content = QuantumContextUnderstandingEngine._content_tokens(user_request)
        answer_stems = QuantumDialogueStateEngine._tokens(answer) if 'QuantumDialogueStateEngine' in globals() else set(answer_content)
        answer_is_compact_object = bool(answer_content and len(answer_content) <= 6 and (len(set(answer_content)) <= 6) and (len(answer_content) <= 3 or semantic_entity_terms))
        user_entity_packets = []
        try:
            user_entity_packets = QuantumContextUnderstandingEngine._entities(user_request)
        except Exception:
            user_entity_packets = []
        user_semantic_entities = [
            cls._clean(item.get('value'), 240)
            for item in user_entity_packets
            if isinstance(item, dict)
            and item.get('value')
            and item.get('type') in {'proper_name', 'formula_symbol', 'number_expression', 'code_identifier'}
            and str(item.get('value')).casefold() not in DIALOGUE_TASK_FUNCTION_WORDS
        ]
        non_representation_objects = [str(item['value']) for item in objects if str(item['value']).casefold() not in {'graph', 'diagram', 'table', 'formula', 'image', 'gallery', 'file', 'audio', 'video', 'code', 'link', 'text', 'action'}]
        topic_candidates = [
            *user_semantic_entities,
            *non_representation_objects,
            *[x for x in user_content if x.casefold() not in DIALOGUE_TASK_FUNCTION_WORDS],
        ]
        unique = []
        for value in topic_candidates:
            value = cls._clean(value, 240)
            if value and value.casefold() not in {x.casefold() for x in unique}:
                unique.append(value)
        if unique:
            topic = ' '.join(unique[:4])
        if not topic:
            topic = cls._clean(user_request, 500)
        output_plan = list(actual_representations)
        if not output_plan:
            semantic_representation = cls._clean(user_profile.get('best_representation'), 80).lower()
            output_plan = [semantic_representation] if semantic_representation in {'code', 'graph', 'table', 'diagram', 'image', 'gallery', 'formula', 'link', 'file', 'audio', 'video'} else ['text']
        semantic_anchor = cls._clean(' '.join((x for x in (user_request, answer, topic, goal, operation, ' '.join((x['value'] for x in objects[:6])), ' '.join(output_plan)) if x)), 9000)
        numeric_literals = re.findall('(?<![\\w.])[-+]?\\d+(?:[.,]\\d+)?(?![\\w.])', user_request)
        numeric_range = bool(len(numeric_literals) >= 2 and re.search('[-+]?\\d+(?:[.,]\\d+)?\\s*(?:до|to|-)\\s*[-+]?\\d+(?:[.,]\\d+)?', user_request, flags=re.I))
        scalar_task = bool(numeric_range and (operation in {'answer', 'calculate', 'build', 'present'} or 'text' in output_plan))
        produced_scalar = bool(answer and len(re.findall('(?<![\\w.])[-+]?\\d+(?:[.,]\\d+)?(?![\\w.])', answer)) == 1)
        expected_response_type = 'number' if scalar_task or (produced_scalar and numeric_range) else 'text' if not actual_representations else output_plan[0]
        pending_input = bool(answer.rstrip().endswith('?'))
        pending_input_type = expected_response_type if expected_response_type in {'number', 'text'} else 'number' if numeric_range else 'unknown'
        return {'version': cls.VERSION, 'turn_id': turn_id, 'scene_id': cls._clean(scene_id, 300), 'user_request': user_request, 'answer': answer, 'summary': cls._clean(summary, 1500), 'meaning': {'topic': topic, 'goal': goal, 'operation': operation, 'objects': objects[:8], 'concepts': [{'value': term, 'strength': round(float(term_counts[term]), 6)} for term in salient_terms[:8]], 'representations': output_plan, 'semantic_anchor': semantic_anchor, 'user_profile': {'best_operation': cls._clean(user_profile.get('best_operation'), 120), 'best_object': cls._clean(user_profile.get('best_object'), 120), 'best_goal': cls._clean(user_profile.get('best_goal'), 120), 'representation': cls._clean(user_profile.get('best_representation'), 120)}, 'answer_profile': {'best_operation': cls._clean(answer_profile.get('best_operation'), 120), 'best_object': cls._clean(answer_profile.get('best_object'), 120), 'best_goal': cls._clean(answer_profile.get('best_goal'), 120), 'representation': cls._clean(answer_profile.get('best_representation'), 120)}}, 'dialogue_anchor': {'user': user_request, 'april': answer, 'topic': topic, 'goal': goal, 'active_meaning': semantic_anchor}, 'response_contract': {'expected_type': expected_response_type, 'numeric_range_request': numeric_range, 'scalar_task': scalar_task, 'produced_scalar': produced_scalar, 'produced_representations': list(output_plan), 'pending_input': pending_input, 'pending_input_type': pending_input_type if pending_input else ''}, 'scene': {'render_block_types': output_plan, 'render_blocks': deepcopy(blocks[:24]), 'complete': bool(answer)}, 'dialogue_state': QuantumDialogueStateEngine.commit_turn(user_request, answer, render_blocks=blocks, turn_id=turn_id, scene_id=scene_id, semantic_engine=engine), 'source': 'completed_turn_semantic_understanding'}

    @staticmethod
    def _morphological_content_overlap(current_tokens: set[str], prior_tokens: set[str]) -> float:
        """Measure content continuity across inflectional variants without a
        vocabulary of topic triggers. Character-shape similarity lets forms such
        as ``опыты``/``опытов`` or ``сахар``/``сахаром`` remain the same concept.
        """
        if not current_tokens or not prior_tokens:
            return 0.0
        scores: list[float] = []
        for token in current_tokens:
            best = 0.0
            for prior in prior_tokens:
                if not prior or abs(len(token) - len(prior)) > max(4, len(token) // 2):
                    continue
                best = max(best, SequenceMatcher(None, token, prior).ratio())
            if len(token) >= 4:
                scores.append(best if best >= 0.45 else 0.0)
        if not scores:
            return 0.0
        return sum(scores) / max(1, len(scores))

    @classmethod
    def compare(cls, current_request: str, meaning: dict[str, Any] | None, *, semantic_engine: Any=None, recent_meanings: list[dict[str, Any]] | None=None) -> dict[str, Any]:
        current_request = cls._clean(current_request, 2600)
        meaning = meaning if isinstance(meaning, dict) else {}
        meaning_block = meaning.get('meaning') if isinstance(meaning.get('meaning'), dict) else meaning
        anchor = cls._clean(meaning_block.get('semantic_anchor') or meaning_block.get('active_meaning') or meaning.get('answer') or meaning.get('user_request'), 8000)
        previous_user = cls._clean(meaning.get('user_request') or (meaning.get('dialogue_anchor') if isinstance(meaning.get('dialogue_anchor'), dict) else {}).get('user'), 2600)
        previous_answer = cls._clean(meaning.get('answer') or (meaning.get('dialogue_anchor') if isinstance(meaning.get('dialogue_anchor'), dict) else {}).get('april'), 7000)
        topic = cls._clean(meaning_block.get('topic'), 600)
        goal = cls._clean(meaning_block.get('goal'), 600)
        engine = semantic_engine
        similarities: dict[str, float] = {}
        source = 'none'
        if engine is not None and current_request:
            candidates = [x for x in (anchor, previous_answer, previous_user, topic, goal) if x]
            try:
                result = engine.similarity_many(current_request, candidates)
                if isinstance(result, dict):
                    similarities = {str(k): round(float(v or 0.0), 6) for k, v in result.items()}
                    source = 'quantum_semantic_similarity'
            except Exception:
                for candidate in [x for x in (anchor, previous_answer, previous_user, topic, goal) if x]:
                    try:
                        similarities[candidate] = round(float(engine.similarity(current_request, candidate).get('score', 0.0) or 0.0), 6)
                        source = 'quantum_semantic_similarity'
                    except Exception:
                        pass

        def sim_of(value: str) -> float:
            return float(similarities.get(value, 0.0) or 0.0)
        current_entities = QuantumContextUnderstandingEngine._entities(current_request)
        current_content_tokens = set(QuantumContextUnderstandingEngine._content_tokens(current_request))
        prior_content_tokens = set(QuantumContextUnderstandingEngine._content_tokens(' '.join((x for x in (previous_user, previous_answer, anchor) if x))))
        concept_items = meaning_block.get('concepts')
        if isinstance(concept_items, list):
            prior_content_tokens.update((str(item.get('value')).casefold() for item in concept_items if isinstance(item, dict) and item.get('value')))
        content_overlap = len(current_content_tokens & prior_content_tokens) / max(1, len(current_content_tokens))
        current_stems = QuantumContextUnderstandingEngine._semantic_stems(current_content_tokens)
        prior_stems = QuantumContextUnderstandingEngine._semantic_stems(prior_content_tokens)
        stem_overlap = len(current_stems & prior_stems) / max(1, len(current_stems))
        morphological_content_overlap = max(cls._morphological_content_overlap(current_content_tokens, prior_content_tokens), stem_overlap)
        content_semantic_similarity = 0.0
        if semantic_engine is not None and current_content_tokens and prior_content_tokens:
            try:
                current_content_text = ' '.join(sorted(current_content_tokens))
                prior_content_text = ' '.join(sorted(prior_content_tokens))
                content_semantic_similarity = float(semantic_engine.similarity(current_content_text, prior_content_text).get('score', 0.0) or 0.0)
            except Exception:
                content_semantic_similarity = 0.0
        current_entity_values = {str(x.get('value') or '').casefold() for x in current_entities if x.get('value')}
        prior_entities = QuantumContextUnderstandingEngine._entities(' '.join((x for x in (previous_user, previous_answer, anchor) if x)))
        prior_entity_values = {str(x.get('value') or '').casefold() for x in prior_entities if x.get('value')}
        entity_overlap = len(current_entity_values & prior_entity_values) / max(1, len(current_entity_values))
        answer_similarity = sim_of(previous_answer)
        user_similarity = sim_of(previous_user)
        anchor_similarity = sim_of(anchor)
        topic_similarity = sim_of(topic)
        goal_similarity = sim_of(goal)
        discourse_scores: dict[str, float] = {}
        if engine is not None:
            try:
                measured = engine.measure(current_request, previous_assistant=previous_answer, previous_user=previous_user, active_topic=topic, active_goal=goal)
                discourse_scores = dict(measured.get('dialogue_scores') or {})
            except Exception:
                discourse_scores = {}
        continuation = max(float(discourse_scores.get('continuation', 0.0) or 0.0), float(discourse_scores.get('reformulation', 0.0) or 0.0), float(discourse_scores.get('correction', 0.0) or 0.0))
        reference = max(float(discourse_scores.get('reference', 0.0) or 0.0), float(discourse_scores.get('artifact_reference', 0.0) or 0.0))
        followup_mass = max(continuation, reference)
        non_followup_mass = max(float(discourse_scores.get('new_topic', 0.0) or 0.0), float(discourse_scores.get('independent', 0.0) or 0.0), float(discourse_scores.get('question', 0.0) or 0.0))
        discourse_relative = followup_mass / max(0.001, followup_mass + non_followup_mass)
        current_output_profile = {}
        if engine is not None:
            try:
                current_output_profile = engine.measure(current_request)
            except Exception:
                current_output_profile = {}
        current_operation = str(current_output_profile.get('best_operation') or '').lower()
        current_representation = str(current_output_profile.get('best_representation') or '').lower()
        previous_representations = [str(x).lower() for x in (meaning_block.get('representations') if isinstance(meaning_block.get('representations'), list) else []) if str(x).strip()]
        representation_continuity = 0.0
        if current_representation and current_representation in previous_representations:
            representation_continuity = 1.0
        development_score = 0.22 * answer_similarity + 0.14 * anchor_similarity + 0.08 * user_similarity + 0.06 * topic_similarity + 0.05 * goal_similarity + 0.07 * min(1.0, entity_overlap) + 0.1 * continuation + 0.1 * discourse_relative + 0.18 * min(1.0, max(content_overlap, morphological_content_overlap, content_semantic_similarity))
        reference_score = 0.2 * answer_similarity + 0.12 * anchor_similarity + 0.08 * topic_similarity + 0.09 * min(1.0, entity_overlap) + 0.18 * reference + 0.06 * representation_continuity + 0.16 * discourse_relative + 0.11 * min(1.0, max(content_overlap, morphological_content_overlap, content_semantic_similarity))
        relation_score = max(development_score, reference_score)
        topic_evidence = max(min(1.0, content_overlap), min(1.0, morphological_content_overlap), min(1.0, content_semantic_similarity), min(1.0, entity_overlap))
        current_content_count = len(current_content_tokens)
        explicit_topic_novelty = bool(current_content_count >= 2 and entity_overlap == 0.0 and (content_overlap < 0.12) and (morphological_content_overlap < 0.22) and (content_semantic_similarity < 0.22) and (reference < 0.35))
        followup_total = max(0.001, followup_mass + non_followup_mass)
        continuation_ratio = continuation / followup_total
        reference_ratio = reference / followup_total
        followup_ratio = followup_mass / followup_total
        topic_fit = 1.0 - __import__('math').exp(-5.0 * max(0.0, topic_evidence))
        context_fit = max(topic_fit, 0.85 * followup_ratio)
        transition_scores = {'develop_current': development_score * (0.55 + 0.45 * context_fit) + 0.5 * continuation_ratio, 'refer_current': reference_score * (0.55 + 0.45 * context_fit) + 0.8 * reference_ratio, 'new_topic': max(0.0, 1.0 - 0.9 * max(topic_fit, followup_ratio))}
        if explicit_topic_novelty:
            transition_scores['new_topic'] = max(transition_scores['new_topic'], 0.92)
            transition_scores['develop_current'] *= 0.3
            transition_scores['refer_current'] *= 0.3
        relation_score = max(float(transition_scores['develop_current']), float(transition_scores['refer_current']))
        recent_candidates: list[dict[str, Any]] = []
        for age, candidate in enumerate(reversed(recent_meanings or []), start=2):
            if not isinstance(candidate, dict):
                continue
            candidate_result = cls.compare(current_request, candidate, semantic_engine=semantic_engine, recent_meanings=[])
            candidate_result['age'] = age
            candidate_result['_meaning'] = candidate
            recent_candidates.append(candidate_result)
        recent_best = None
        if recent_candidates:
            recent_best = max(recent_candidates, key=lambda item: max(float((item.get('relation_scores') if isinstance(item.get('relation_scores'), dict) else {}).get('develop_current', 0.0) or 0.0), float((item.get('relation_scores') if isinstance(item.get('relation_scores'), dict) else {}).get('refer_current', 0.0) or 0.0)))
        current_semantic_content = set(QuantumContextUnderstandingEngine._content_tokens(current_request))
        short_followup = bool(not explicit_topic_novelty and len(current_semantic_content) <= 2 and (continuation >= 0.03 or reference >= 0.03 or discourse_relative >= 0.12 or (morphological_content_overlap >= 0.25)))
        latest_development_lock = bool(not explicit_topic_novelty and (continuation >= 0.08 and continuation >= reference or (current_content_count <= 2 and (answer_similarity >= 0.05 or morphological_content_overlap >= 0.4 or content_semantic_similarity >= 0.05) and (topic_evidence >= 0.25 or discourse_relative >= 0.08 or short_followup))))
        immediate_relation = max({'REFER_CURRENT': float(transition_scores['refer_current']), 'DEVELOP_CURRENT': float(transition_scores['develop_current']), 'NEW_TOPIC': float(transition_scores['new_topic'])}.items(), key=lambda item: item[1])[0]
        new_topic_score = float(transition_scores['new_topic'] or 0.0)
        best_forward_score = max(float(transition_scores['develop_current'] or 0.0), float(transition_scores['refer_current'] or 0.0))
        new_topic_dominant = bool(new_topic_score > best_forward_score and new_topic_score >= 0.14 and (new_topic_score - best_forward_score >= 0.02))
        if latest_development_lock and (not new_topic_dominant):
            immediate_relation = 'DEVELOP_CURRENT'
        elif new_topic_dominant:
            immediate_relation = 'NEW_TOPIC'
        if recent_best is not None:
            recent_relation_scores = recent_best.get('relation_scores') if isinstance(recent_best.get('relation_scores'), dict) else {}
            recent_strength = max(float(recent_relation_scores.get('develop_current', 0.0) or 0.0), float(recent_relation_scores.get('refer_current', 0.0) or 0.0))
            immediate_strength = max(development_score, reference_score)
            if not short_followup and (not latest_development_lock) and (recent_strength >= 0.22) and (recent_strength > immediate_strength + 0.07):
                selected_relation = str(recent_best.get('relation') or 'DEVELOP_CURRENT')
                relation = 'REVISIT_RECENT'
                relation_scores = dict(recent_best.get('relation_scores') or {})
                relation_scores['immediate'] = round(immediate_strength, 6)
                relation_scores['selected_recent'] = round(recent_strength, 6)
                return {'version': cls.VERSION, 'current_request': current_request, 'relation_scores': relation_scores, 'evidence': {**dict(recent_best.get('evidence') or {}), 'immediate_strength': round(immediate_strength, 6), 'selected_recent_strength': round(recent_strength, 6)}, 'current_task': dict(recent_best.get('current_task') or {}), 'previous_task': dict(recent_best.get('previous_task') or {}), 'relation': selected_relation, 'anchor': 'recent_turn', 'selected_turn_meaning': deepcopy(recent_best.get('_meaning') or {}), 'source': 'semantic_meaning_transition_recent'}
        return {'version': cls.VERSION, 'current_request': current_request, 'relation_scores': {'develop_current': round(max(0.0, min(1.0, float(transition_scores['develop_current']))), 6), 'refer_current': round(max(0.0, min(1.0, float(transition_scores['refer_current']))), 6), 'revisit_recent': 0.0, 'new_topic': round(max(0.0, min(1.0, float(transition_scores['new_topic']))), 6)}, 'evidence': {'answer_similarity': round(answer_similarity, 6), 'user_similarity': round(user_similarity, 6), 'anchor_similarity': round(anchor_similarity, 6), 'topic_similarity': round(topic_similarity, 6), 'goal_similarity': round(goal_similarity, 6), 'entity_overlap': round(entity_overlap, 6), 'continuation_semantics': round(continuation, 6), 'reference_semantics': round(reference, 6), 'representation_continuity': round(representation_continuity, 6), 'discourse_relative': round(discourse_relative, 6), 'content_overlap': round(content_overlap, 6), 'morphological_content_overlap': round(morphological_content_overlap, 6), 'content_semantic_similarity': round(content_semantic_similarity, 6), 'contextual_support': round(topic_evidence, 6), 'explicit_topic_novelty': explicit_topic_novelty, 'current_content_count': current_content_count, 'context_fit': round(context_fit, 6), 'continuation_ratio': round(continuation_ratio, 6), 'reference_ratio': round(reference_ratio, 6), 'semantic_source': source, 'short_followup_lock': bool(short_followup), 'latest_development_lock': bool(latest_development_lock)}, 'current_task': {'operation': current_operation, 'representation': current_representation}, 'previous_task': {'operation': str(meaning_block.get('operation') or ''), 'topic': topic, 'goal': goal, 'representations': previous_representations}, 'relation': immediate_relation, 'anchor': 'last_turn' if immediate_relation in {'REFER_CURRENT', 'DEVELOP_CURRENT'} else 'none', 'source': 'semantic_meaning_transition'}

class QuantumDialogueStateEngine:
    """
    Persistent semantic state for the dialogue loop.

    The engine performs two complementary operations:
      A) analyze the completed April answer and commit what was established;
      B) prepare the next turn from that committed state.

    It never chooses a renderer or provider. It creates one semantic state object
    that later interpretation consumes. This prevents the conversation from
    splitting into independent "topic", "memory", "scene", and "answer" anchors.
    """
    VERSION = 'quantum_dialogue_state_engine_v1'
    _REPRESENTATION_LABELS = {'text', 'table', 'graph', 'diagram', 'formula', 'image', 'gallery', 'code', 'link', 'audio', 'video', 'file', 'action', 'scene', 'memory', 'visual_context'}

    @classmethod
    def _norm(cls, value: Any, limit: int=4000) -> str:
        return re.sub('\\s+', ' ', str(value or '').strip())[:limit]

    @classmethod
    def _tokens(cls, text: Any) -> set[str]:
        return {token for token in QuantumContextUnderstandingEngine._content_tokens(text) if len(token) >= 3}

    @classmethod
    def _extract_entities(cls, text: str) -> list[str]:
        try:
            packets = QuantumContextUnderstandingEngine._entities(text)
        except Exception:
            packets = []
        values = []
        for item in packets:
            if not isinstance(item, dict):
                continue
            value = cls._norm(item.get('value'), 240)
            if not value:
                continue
            if value.casefold() in cls._REPRESENTATION_LABELS:
                continue
            if value.casefold() not in {x.casefold() for x in values}:
                values.append(value)
        return values[:12]

    @classmethod
    def _extract_numeric_results(cls, answer: str) -> list[str]:
        result = []
        for match in re.finditer('(?:=|равно|equals)\\s*([-+]?\\d+(?:[.,]\\d+)?)\\b', answer, flags=re.I):
            result.append(match.group(1))
        if not result:
            nums = re.findall('(?<![\\w.])[-+]?\\d+(?:[.,]\\d+)?(?![\\w.])', answer)
            if len(nums) == 1:
                result.append(nums[0])
        return result[-8:]

    @classmethod
    def _pending_from_answer(cls, answer: str, expected_type: str) -> dict[str, Any]:
        stripped = cls._norm(answer, 7000)
        pending = bool(stripped.endswith('?'))
        return {'pending': pending, 'expected_input_type': expected_type if pending else '', 'source': 'answer_semantics'}

    @classmethod
    def commit_turn(cls, user_request: str, answer: str, *, render_blocks: list[dict[str, Any]] | None=None, turn_id: Any=None, scene_id: str='', semantic_engine: Any=None, inherited_state: dict[str, Any] | None=None) -> dict[str, Any]:
        user = cls._norm(user_request, 2600)
        assistant = cls._norm(answer, 9000)
        inherited = inherited_state if isinstance(inherited_state, dict) else {}
        user_profile = {}
        answer_profile = {}
        if semantic_engine is not None:
            try:
                user_profile = semantic_engine.measure(user, active_topic=inherited.get('active_topic', ''), active_goal=inherited.get('active_goal', ''))
            except Exception:
                user_profile = {}
            try:
                answer_profile = semantic_engine.measure(assistant, previous_user=user, active_topic=inherited.get('active_topic', ''), active_goal=inherited.get('active_goal', ''))
            except Exception:
                answer_profile = {}
        representation_scores = user_profile.get('representation_scores') if isinstance(user_profile, dict) else {}
        operation_scores = user_profile.get('operation_scores') if isinstance(user_profile, dict) else {}
        goal_scores = user_profile.get('goal_scores') if isinstance(user_profile, dict) else {}
        best_rep = str(user_profile.get('best_representation') or 'text').lower()
        best_op = str(user_profile.get('best_operation') or 'answer').lower()
        best_goal = str(user_profile.get('best_goal') or 'understand').lower()
        block_types = []
        artifacts = []
        for block in render_blocks or []:
            if not isinstance(block, dict):
                continue
            rep = _clean_representation(block.get('type') or block.get('artifact_type') or block.get('representation'))
            if rep and rep != 'text' and (rep not in block_types):
                block_types.append(rep)
            if rep and rep != 'text':
                artifacts.append({'type': rep, 'title': cls._norm(block.get('title') or block.get('label'), 300), 'block_id': cls._norm(block.get('block_id'), 200), 'payload': deepcopy(block.get('payload')) if isinstance(block.get('payload'), dict) else {}})
        if block_types:
            best_rep = str(block_types[0]).lower()
        assistant_entities = cls._extract_entities(assistant)
        user_entities = cls._extract_entities(user)
        answer_tokens = QuantumContextUnderstandingEngine._content_tokens(assistant)
        user_tokens = QuantumContextUnderstandingEngine._content_tokens(user)
        operation_stems = set()
        try:
            stemmer = SnowballStemmer('russian') if SnowballStemmer is not None else None
            if stemmer is not None:
                operation_words = re.findall('[А-Яа-яЁёЇїІіЄєҐґ]+', ' '.join(OPERATION_HYPOTHESES.values()).lower())
                operation_stems = {stemmer.stem(word) for word in operation_words if len(word) >= 4}
        except Exception:
            operation_stems = set()
        answer_entity_tokens = [token for token in answer_tokens if len(token) >= 4 and token.casefold() not in {'готово', 'сделано', 'ответ', 'слово', 'число', 'сейчас', 'здесь', 'также', 'может', 'можно'} and (not operation_stems or (SnowballStemmer is None or not re.search('[А-Яа-яЁёЇїІіЄєҐґ]', token) or SnowballStemmer('russian').stem(token.casefold()) not in operation_stems))]
        try:
            stemmer = SnowballStemmer('russian') if SnowballStemmer is not None else None
            user_stems = {stemmer.stem(tok) if stemmer is not None and re.search('[А-Яа-яЁёЇїІіЄєҐґ]', tok) else tok.casefold() for tok in user_tokens if len(tok) >= 4}
            answer_entity_tokens.sort(key=lambda tok: (1 if stemmer is not None and re.search('[А-Яа-яЁёЇїІіЄєҐґ]', tok) and (stemmer.stem(tok.casefold()) in user_stems) else 0, len(tok)), reverse=True)
        except Exception:
            pass
        filtered_assistant_entities = [value for value in assistant_entities if value.casefold() not in {'готово', 'сделано', 'ответ', 'слово', 'число', 'вот'}]
        if len(answer_tokens) <= 6 and answer_entity_tokens:
            entities = list(dict.fromkeys(answer_entity_tokens + filtered_assistant_entities))[:12]
        else:
            entities = list(dict.fromkeys(assistant_entities + [x for x in user_entities if x.casefold() not in {y.casefold() for y in assistant_entities}]))[:12]
        numeric_results = cls._extract_numeric_results(assistant)
        representation_only = {'graph', 'diagram', 'table', 'formula', 'image', 'gallery', 'file', 'audio', 'video', 'code', 'link'}
        answer_topic_tokens = [x for x in answer_tokens if x.casefold() not in representation_only]
        user_topic_tokens = [x for x in user_tokens if x.casefold() not in representation_only and x.casefold() not in DIALOGUE_TASK_FUNCTION_WORDS]
        # The active thread follows the user's task, not the assistant's prose.
        topic = ' '.join(user_topic_tokens[:6]) or (entities[0] if entities else ' '.join(answer_topic_tokens[:4]) or cls._norm(user, 500))
        expected_type = 'number' if numeric_results and len(numeric_results) == 1 else 'text' if not block_types else block_types[0]
        previous_open = inherited.get('open_task') if isinstance(inherited.get('open_task'), dict) else {}
        pending = cls._pending_from_answer(assistant, expected_type)
        open_task = {'pending_input': pending['pending'], 'expected_input_type': pending['expected_input_type'], 'operation': best_op, 'goal': best_goal}
        if previous_open.get('pending_input') and (not pending['pending']):
            open_task['completed_previous_input'] = True
        established_facts = []
        if numeric_results:
            for value in numeric_results:
                established_facts.append({'kind': 'numeric_result', 'value': value, 'source': 'assistant_answer'})
        return {'version': cls.VERSION, 'turn_id': turn_id, 'scene_id': cls._norm(scene_id, 300), 'active_thread': {'status': 'active', 'topic': topic, 'goal': best_goal, 'operation': best_op, 'domain': max((user_profile.get('domain_scores') or {}).items(), key=lambda item: float(item[1] or 0.0))[0] if isinstance(user_profile.get('domain_scores'), dict) and user_profile.get('domain_scores') else '', 'entities': [topic] + [x for x in entities if x.casefold() != topic.casefold()][:11]}, 'current_turn': {'user_request': user, 'answer': assistant, 'operation': best_op, 'goal': best_goal, 'representation': best_rep}, 'established': {'facts': established_facts[:16], 'numeric_results': numeric_results[:8], 'entities': ([topic] + [x for x in entities if x.casefold() != topic.casefold()][:11]) if topic else entities[:12], 'artifacts': artifacts[:12], 'representations': block_types[:12]}, 'open_task': open_task, 'references': {'active_entity': topic or (entities[0] if entities else ''), 'active_result': numeric_results[-1] if numeric_results else '', 'active_artifact_types': block_types[:12]}, 'answer_semantics': {'best_operation': best_op, 'best_goal': best_goal, 'best_representation': best_rep, 'representation_scores': {str(k): round(float(v), 6) for k, v in (representation_scores or {}).items()}, 'operation_scores': {str(k): round(float(v), 6) for k, v in (operation_scores or {}).items()}, 'goal_scores': {str(k): round(float(v), 6) for k, v in (goal_scores or {}).items()}}, 'continuity_anchor': {'user': user, 'april': assistant, 'semantic_subject': topic, 'entities': ([topic] + [x for x in entities if x.casefold() != topic.casefold()][:11]) if topic else entities[:12], 'results': numeric_results[:8], 'artifacts': artifacts[:12], 'open_task': deepcopy(open_task)}, 'source': cls.VERSION}

    @classmethod
    def build_next_turn_context(cls, state: dict[str, Any] | None, current_request: str, *, relation: str, resolved_reference: str='') -> dict[str, Any]:
        state = state if isinstance(state, dict) else {}
        relation = str(relation or 'NEW').upper()
        current = cls._norm(current_request, 2600)
        if relation not in {'CONTINUE', 'RECALL'}:
            return {'relation': 'NEW', 'active': {}, 'previous': {}, 'resolved_reference': '', 'source': cls.VERSION}
        previous = state.get('continuity_anchor')
        if not isinstance(previous, dict):
            previous = {'user': cls._norm(state.get('current_turn', {}).get('user_request')), 'april': cls._norm(state.get('current_turn', {}).get('answer'))}
        active_thread = state.get('active_thread') if isinstance(state.get('active_thread'), dict) else {}
        established = state.get('established') if isinstance(state.get('established'), dict) else {}
        open_task = state.get('open_task') if isinstance(state.get('open_task'), dict) else {}
        references = state.get('references') if isinstance(state.get('references'), dict) else {}
        return {'relation': relation, 'active': {'topic': cls._norm(active_thread.get('topic'), 700), 'goal': cls._norm(active_thread.get('goal'), 500), 'operation': cls._norm(active_thread.get('operation'), 500), 'entities': deepcopy(active_thread.get('entities') or [])}, 'previous': {'user': cls._norm(previous.get('user'), 2600), 'april': cls._norm(previous.get('april'), 9000), 'semantic_subject': cls._norm(previous.get('semantic_subject'), 700), 'entities': deepcopy(previous.get('entities') or established.get('entities') or []), 'results': deepcopy(previous.get('results') or established.get('numeric_results') or []), 'artifacts': deepcopy(previous.get('artifacts') or established.get('artifacts') or []), 'open_task': deepcopy(previous.get('open_task') or open_task)}, 'resolved_reference': cls._norm(resolved_reference or references.get('active_entity') or '', 500), 'current_request': current, 'source': cls.VERSION}

class QuantumSequentialDialogueEngine:
    """
    Single-owner sequential dialogue state machine.

    Invariants:
      1) Every new user turn is interpreted against exactly one active completed
         USER -> APRIL turn (the immediately preceding successful exchange).
      2) The semantic result of that turn is the next turn's anchor.
      3) Older turns are historical evidence only; they cannot silently become the
         active topic during ordinary interpretation.
      4) The engine chooses exactly one of CONTINUE / NEW. RECALL is reserved for
         an explicit semantic memory-query measurement.
      5) No lexical trigger tables participate. Continuation is derived from the
         measured task vector, semantic similarity, discourse scores, structural
         incompleteness and artifact continuity.
    """
    VERSION = 'quantum_sequential_dialogue_engine_v1'

    @staticmethod
    def _norm(value: Any) -> str:
        return re.sub('\\s+', ' ', str(value or '').strip())

    @classmethod
    def _content_tokens(cls, text: Any) -> set[str]:
        return {token for token in QuantumContextUnderstandingEngine._content_tokens(text) if len(token) >= 3}

    @classmethod
    def _latest_pair(cls, history: list[dict[str, Any]] | None) -> dict[str, str]:
        pending_user = ''
        pairs: list[dict[str, str]] = []
        for item in history if isinstance(history, list) else []:
            if not isinstance(item, dict):
                continue
            metadata = item.get('metadata') if isinstance(item.get('metadata'), dict) else {}
            if metadata.get('internal_context') or metadata.get('internal_turn'):
                continue
            role = str(item.get('role') or '').lower()
            if role in {'user', 'human'}:
                pending_user = cls._norm(item.get('content') or item.get('text') or item.get('answer'))
                continue
            if role in {'assistant', 'april', 'bot'} and pending_user:
                answer = cls._norm(item.get('content') or item.get('answer') or item.get('text') or item.get('summary'))
                if answer:
                    pairs.append({'user': pending_user, 'april': answer, 'assistant': answer})
                pending_user = ''
        return pairs[-1] if pairs else {}

    @staticmethod
    def _is_explicit_task(text: str) -> bool:
        """Detect a structurally complete task, not a continuation keyword.

        The result is evidence that the current turn can stand alone. It is not
        a list of follow-up triggers and never decides continuation by itself.
        """
        tokens = QuantumContextUnderstandingEngine._content_tokens(text)
        if not tokens:
            return False
        return bool(
            re.search(
                r'\b(напиши|написать|покажи|показать|создай|создать|сделай|сделать|нарисуй|нарисовать|объясни|объяснить|опиши|описать|дай|дайте|найди|найти|сравни|сравнить|расскажи|рассказать|расчитай|вычисли|вычислить)\b',
                text.casefold(),
            ) and len(tokens) >= 2
        )

    @staticmethod
    def _interrogative_ellipsis(text: str, active_refs: list[str], previous_representation: str) -> bool:
        """Detect a question whose semantic object is omitted from the turn."""
        if not active_refs and not previous_representation:
            return False
        if not re.search(r'\b(какой|какая|какое|какие|какую|каких|который|которая|которое|которые|чего|что)\b', text.casefold()):
            return False
        tokens = QuantumContextUnderstandingEngine._content_tokens(text)
        return len(tokens) <= 3 or not QuantumContextUnderstandingEngine._entities(text)

    @staticmethod
    def _orthographic_reference(current: str, previous_user: str, active_refs: list[str]) -> dict[str, Any]:
        """Resolve a short typo/orthographic variation against the active turn."""
        current_tokens = [x for x in QuantumContextUnderstandingEngine._tokens(current) if len(x) >= 4]
        if len(current_tokens) != 1:
            return {'matched': False, 'current': '', 'target': '', 'score': 0.0}
        token = current_tokens[0].casefold()
        candidates = []
        for source in (previous_user, *active_refs):
            for value in re.findall(r'[А-ЯЁA-Z][а-яёa-z]+', str(source or '')):
                if len(value) >= 4 and value.casefold() != token:
                    candidates.append(value)
        best_value, best_score = '', 0.0
        for value in candidates:
            score = SequenceMatcher(None, token, value.casefold()).ratio()
            if score > best_score:
                best_value, best_score = value, score
        matched = bool(best_value and 0.72 <= best_score < 0.99)
        return {
            'matched': matched,
            'current': current_tokens[0],
            'target': best_value if matched else '',
            'score': round(best_score, 6),
        }

    @classmethod
    def _trajectory_evidence(
        cls,
        current: str,
        meaning: dict[str, Any],
        previous_user: str,
        previous_answer: str,
        current_profile: dict[str, Any],
        previous_profile: dict[str, Any],
    ) -> dict[str, Any]:
        """Reconstruct active dialogue trajectory from the authenticated turn."""
        previous_state = meaning.get('dialogue_state') if isinstance(meaning.get('dialogue_state'), dict) else {}
        refs_block = previous_state.get('references') if isinstance(previous_state.get('references'), dict) else {}
        thread = previous_state.get('active_thread') if isinstance(previous_state.get('active_thread'), dict) else {}
        active_refs = [
            str(x).strip()
            for x in (thread.get('topic'), refs_block.get('active_entity'), refs_block.get('active_result'), *(thread.get('entities') or []))
            if str(x).strip()
        ]
        meaning_block = meaning.get('meaning') if isinstance(meaning.get('meaning'), dict) else meaning
        previous_reps = meaning_block.get('representations') if isinstance(meaning_block.get('representations'), list) else []
        previous_rep = str(previous_reps[0] if previous_reps else '').lower()
        current_features = current_profile.get('request_features') if isinstance(current_profile.get('request_features'), dict) else {}
        self_contained = bool(current_features.get('self_contained'))
        grammatical_anaphora = bool(re.search(
            r'(?<![А-Яа-яЁёЇїІіЄєҐґ])(он|она|оно|они|его|её|ее|ему|ей|им|ими|этот|эта|это|эти|того|той|тем|такой|него|неё|нее|ней|нему|ним|них|который|которая|которое|которые)(?![А-Яа-яЁёЇїІіЄєҐґ])',
            current.casefold(),
        ))
        short_anchored_fragment = bool(
            active_refs
            and len(QuantumContextUnderstandingEngine._content_tokens(current)) <= 2
            and not cls._is_explicit_task(current)
        )
        explicit_reference = grammatical_anaphora or short_anchored_fragment
        ellipsis = cls._interrogative_ellipsis(current, active_refs, previous_rep)
        orth = cls._orthographic_reference(current, previous_user, active_refs)
        previous_open = previous_state.get('open_task') if isinstance(previous_state.get('open_task'), dict) else {}
        response_contract = meaning.get('response_contract') if isinstance(meaning.get('response_contract'), dict) else {}
        pending = bool(previous_open.get('pending_input') or response_contract.get('pending_input'))
        current_rep = str(current_profile.get('best_representation') or '').lower()
        explicit_task = cls._is_explicit_task(current)
        incompatible_structured_task = bool(
            self_contained
            and explicit_task
            and current_rep in STRUCTURED_REPRESENTATIONS
            and previous_rep in STRUCTURED_REPRESENTATIONS
            and current_rep != previous_rep
            and not explicit_reference
            and not ellipsis
            and not orth.get('matched')
        )
        previous_turn = previous_state.get('current_turn') if isinstance(previous_state.get('current_turn'), dict) else {}
        previous_op = str(previous_turn.get('operation') or meaning_block.get('operation') or '').lower()
        semantic_family_development = bool(
            (current_rep and previous_rep and current_rep == previous_rep)
            or (current_profile.get('best_operation') and previous_op and str(current_profile.get('best_operation')).lower() == previous_op)
        )
        return {
            'active_refs': active_refs[:12],
            'active_referent': str(thread.get('topic') or refs_block.get('active_entity') or (active_refs[0] if active_refs else '')).strip(),
            'previous_representation': previous_rep,
            'self_contained': self_contained,
            'grammatical_anaphora': grammatical_anaphora,
            'explicit_reference': explicit_reference,
            'interrogative_ellipsis': ellipsis,
            'orthographic_reference': orth,
            'pending_input': pending,
            'explicit_task': explicit_task,
            'incompatible_structured_task': incompatible_structured_task,
            'semantic_family_development': semantic_family_development,
        }

    @classmethod
    def resolve(cls, current_request: str, previous_meaning: dict[str, Any] | None, *, previous_user: str='', previous_answer: str='', recent_history: list[dict[str, str]] | None=None, semantic_engine: Any=None, previous_scene: dict[str, Any] | None=None) -> dict[str, Any]:
        current = cls._norm(current_request)
        meaning = previous_meaning if isinstance(previous_meaning, dict) else {}
        meaning_block = meaning.get('meaning') if isinstance(meaning.get('meaning'), dict) else {}
        previous_user = cls._norm(previous_user or meaning.get('user_request'))
        previous_answer = cls._norm(previous_answer or meaning.get('answer'))
        recent_history = [x for x in recent_history or [] if isinstance(x, dict)]
        latest_pair = cls._latest_pair(recent_history) or {'user': previous_user, 'april': previous_answer}
        if not previous_user:
            previous_user = cls._norm(latest_pair.get('user'))
        if not previous_answer:
            previous_answer = cls._norm(latest_pair.get('april') or latest_pair.get('assistant'))
        if not current or (not previous_user and (not previous_answer)):
            return {'relation': 'NEW', 'confidence': 0.98, 'selected_pair': {}, 'selected_index': -1, 'scores': {}, 'reason': 'no_completed_previous_turn', 'source': cls.VERSION}
        current_profile = {}
        previous_profile = {}
        if semantic_engine is not None:
            try:
                current_profile = semantic_engine.measure(current)
            except Exception:
                current_profile = {}
            try:
                previous_profile = semantic_engine.measure(previous_user)
            except Exception:
                previous_profile = {}
        trajectory = cls._trajectory_evidence(current, meaning, previous_user, previous_answer, current_profile, previous_profile)
        current_sem = current_profile.get('dialogue_scores') if isinstance(current_profile.get('dialogue_scores'), dict) else {}
        current_op = str(current_profile.get('best_operation') or '').lower()
        current_rep = str(current_profile.get('best_representation') or '').lower()
        current_obj = str(current_profile.get('best_object') or '').lower()
        current_goal = str(current_profile.get('best_goal') or '').lower()
        previous_rep = str(previous_profile.get('best_representation') or '').lower()
        previous_op = str(previous_profile.get('best_operation') or '').lower()
        previous_obj = str(previous_profile.get('best_object') or '').lower()
        previous_goal = str(previous_profile.get('best_goal') or '').lower()
        previous_response_contract = meaning.get('response_contract') if isinstance(meaning.get('response_contract'), dict) else {}
        expected_previous_type = str(previous_response_contract.get('expected_type') or '').lower()
        previous_scalar_task = bool(previous_response_contract.get('scalar_task') or previous_response_contract.get('numeric_range_request'))
        previous_pending_input = bool(previous_response_contract.get('pending_input'))
        previous_pending_input_type = str(previous_response_contract.get('pending_input_type') or '').lower()

        def sim(left: str, right: str) -> float:
            if semantic_engine is None or not left or (not right):
                return 0.0
            try:
                return float(semantic_engine.similarity(left, right).get('score', 0.0) or 0.0)
            except Exception:
                return 0.0
        answer_similarity = sim(current, previous_answer)
        user_similarity = sim(current, previous_user)
        combined_similarity = sim(current, ' '.join((x for x in (previous_user, previous_answer) if x)))
        current_tokens = cls._content_tokens(current)
        previous_tokens = cls._content_tokens(' '.join((x for x in (previous_user, previous_answer) if x)))
        overlap = len(current_tokens & previous_tokens) / max(1, len(current_tokens))
        current_numeric_literals = re.findall('(?<![\\w.])[-+]?\\d+(?:[.,]\\d+)?(?![\\w.])', current)
        bare_scalar = bool(len(current_tokens) <= 2 and len(current_numeric_literals) == 1)
        scalar_response_dependency = bool(bare_scalar and (previous_scalar_task and expected_previous_type in {'number', 'text'} or (previous_pending_input and previous_pending_input_type in {'number', 'text', ''})))
        explicit_arithmetic_expression = bool(re.search('(?<![\\w.])[-+]?\\d+(?:[.,]\\d+)?\\s*[+*/×÷-]\\s*[-+]?\\d+(?:[.,]\\d+)?(?![\\w.])', current))
        previous_state = meaning.get('dialogue_state') if isinstance(meaning.get('dialogue_state'), dict) else {}
        active_refs = []
        if isinstance(previous_state, dict):
            refs = previous_state.get('references') if isinstance(previous_state.get('references'), dict) else {}
            active_refs.extend((x for x in (refs.get('active_entity'), refs.get('active_result')) if x))
            thread = previous_state.get('active_thread') if isinstance(previous_state.get('active_thread'), dict) else {}
            active_refs.extend(list(thread.get('entities') or []))
        prior_stems = QuantumContextUnderstandingEngine._semantic_stems(previous_tokens)
        current_stems = QuantumContextUnderstandingEngine._semantic_stems(current_tokens)
        state_relation_support = bool(active_refs and (len(current_stems & prior_stems) > 0 or (isinstance(meaning.get('response_contract'), dict) and bool(meaning.get('response_contract', {}).get('pending_input'))) or (isinstance(previous_state.get('open_task'), dict) and bool(previous_state.get('open_task', {}).get('pending_input')))))
        grammatical_reference = bool(len(current_tokens) <= 7 and previous_tokens and active_refs and state_relation_support)
        current_entity_packets = QuantumContextUnderstandingEngine._entities(current)
        current_entity_values = {str(item.get('value') or '').casefold() for item in current_entity_packets if item.get('value')}
        current_first = (re.findall('[A-Za-zА-Яа-яЁёЇїІіЄєҐґ]+', current) or [''])[0].casefold()
        if current_first:
            try:
                op_words = set(re.findall('[A-Za-zА-Яа-яЁёЇїІіЄєҐґ]+', ' '.join(OPERATION_HYPOTHESES.values()).lower()))
                current_first_stem = SnowballStemmer('russian').stem(current_first) if SnowballStemmer is not None and re.search('[А-Яа-яЁёЇїІіЄєҐґ]', current_first) else current_first
                op_stems = {SnowballStemmer('russian').stem(word) if SnowballStemmer is not None and re.search('[А-Яа-яЁёЇїІіЄєҐґ]', word) else word for word in op_words}
                if current_first in QuantumContextUnderstandingEngine._STOP or current_first_stem in op_stems:
                    current_entity_values.discard(current_first)
            except Exception:
                pass
        explicit_current_numeric = bool(re.search('(?<![\\w.])[-+]?\\d+(?:[.,]\\d+)?\\s*[+*/×÷-]\\s*[-+]?\\d+(?:[.,]\\d+)?(?![\\w.])', current))
        grammatical_anaphora = bool(re.search('(?<![А-Яа-яЁёЇїІіЄєҐґ])(он|она|оно|они|его|её|ее|ему|ей|им|ими|этот|эта|это|эти|того|той|тем|такой|него|неё|нее|ней|нему|ним|них|который|которая|которое|которые)(?![А-Яа-яЁёЇїІіЄєҐґ])', current.lower()))
        contextual_antecedent_dependency = bool(active_refs and len(current_tokens) <= 10 and (not current_entity_values) and (not explicit_current_numeric) and (grammatical_anaphora or state_relation_support))
        if contextual_antecedent_dependency:
            grammatical_reference = True
        grammatical_reference = bool(grammatical_reference or contextual_antecedent_dependency)
        signature_matches = sum((1 for a, b in ((current_rep, previous_rep), (current_op, previous_op), (current_obj, previous_obj), (current_goal, previous_goal)) if a and b and (a == b)))
        core_signature_matches = sum((1 for a, b in ((current_rep, previous_rep), (current_op, previous_op), (current_obj, previous_obj)) if a and b and (a == b)))
        continuation_semantics = max(float(current_sem.get('continuation', 0.0) or 0.0), float(current_sem.get('reformulation', 0.0) or 0.0), float(current_sem.get('correction', 0.0) or 0.0))
        reference_semantics = max(float(current_sem.get('reference', 0.0) or 0.0), float(current_sem.get('artifact_reference', 0.0) or 0.0))
        memory_semantics = float(current_sem.get('memory_query', 0.0) or 0.0)
        request_features = current_profile.get('request_features') if isinstance(current_profile.get('request_features'), dict) else {}
        self_contained = bool(request_features.get('self_contained'))
        trajectory_dependency = bool(
            trajectory.get('explicit_reference')
            or trajectory.get('interrogative_ellipsis')
            or trajectory.get('orthographic_reference', {}).get('matched')
            or trajectory.get('pending_input')
        )
        if trajectory_dependency:
            self_contained = False
        trajectory_development = bool(trajectory.get('semantic_family_development'))
        explicit_structured_break = bool(trajectory.get('incompatible_structured_task'))
        current_content_count = len(current_tokens)
        underspecified = bool(not self_contained and current_content_count <= 7 and (continuation_semantics >= 0.02 or reference_semantics >= 0.02 or answer_similarity >= 0.025 or (user_similarity >= 0.025)))
        prior_structured_types = []
        if isinstance(previous_scene, dict):
            prior_structured_types = [str(x).lower() for x in previous_scene.get('render_block_types') or [] if str(x).strip()]
            if not prior_structured_types:
                prior_structured_types = [str(block.get('type') or block.get('artifact_type') or block.get('representation') or '').lower() for block in previous_scene.get('render_blocks') or [] if isinstance(block, dict)]
        artifact_continuity = bool(prior_structured_types and (current_rep in prior_structured_types or continuation_semantics >= 0.02 or reference_semantics >= 0.02))
        continuation_score = (
            0.20 * answer_similarity
            + 0.12 * user_similarity
            + 0.10 * combined_similarity
            + 0.08 * min(1.0, overlap)
            + 0.08 * min(1.0, core_signature_matches / 3.0)
            + 0.06 * min(1.0, signature_matches / 4.0)
            + 0.06 * continuation_semantics
            + 0.04 * reference_semantics
            + 0.04 * (1.0 if underspecified else 0.0)
            + 0.05 * (1.0 if artifact_continuity else 0.0)
            + 0.16 * (1.0 if trajectory.get('explicit_reference') else 0.0)
            + 0.16 * (1.0 if trajectory.get('interrogative_ellipsis') else 0.0)
            + 0.12 * (1.0 if trajectory.get('orthographic_reference', {}).get('matched') else 0.0)
            + 0.18 * (1.0 if trajectory.get('pending_input') else 0.0)
            + 0.07 * (1.0 if trajectory_development else 0.0)
        )
        if explicit_structured_break:
            continuation_score *= 0.12
        continuation_score = max(0.0, min(1.0, continuation_score))
        if contextual_antecedent_dependency:
            self_contained = False
        topic_break = bool((not trajectory_dependency) and self_contained and (explicit_structured_break or (core_signature_matches == 0 and (overlap < 0.25) and (answer_similarity < 0.25) and (user_similarity < 0.3) and (continuation_semantics < 0.16) and (reference_semantics < 0.12) and (not grammatical_reference) and (not scalar_response_dependency))))
        if trajectory_dependency and not explicit_structured_break:
            relation = 'CONTINUE'
            selected_pair = {'user': previous_user, 'april': previous_answer, 'assistant': previous_answer, 'development_state': 'completed_turn'}
            confidence = max(continuation_score, 0.70 if trajectory.get('pending_input') or trajectory.get('interrogative_ellipsis') or trajectory.get('orthographic_reference', {}).get('matched') else 0.62)
            reason = 'trajectory_dependency'
        elif explicit_structured_break:
            relation = 'NEW'
            selected_pair = {}
            confidence = max(0.0, min(1.0, 1.0 - continuation_score))
            reason = 'new_structured_task'
        elif memory_semantics >= max(0.22, continuation_semantics + 0.04) and (not self_contained):
            relation = 'RECALL'
            selected_pair = {}
            confidence = min(1.0, memory_semantics)
            reason = 'semantic_memory_query'
        elif not topic_break and continuation_score >= 0.13 and (not explicit_arithmetic_expression or previous_pending_input or grammatical_reference) and (continuation_semantics >= 0.02 or reference_semantics >= 0.02 or underspecified or (core_signature_matches >= 1) or artifact_continuity or grammatical_reference or scalar_response_dependency or trajectory_development):
            relation = 'CONTINUE'
            selected_pair = {'user': previous_user, 'april': previous_answer, 'assistant': previous_answer, 'development_state': 'completed_turn'}
            confidence = continuation_score
            reason = 'sequential_semantic_dependency'
        else:
            relation = 'NEW'
            selected_pair = {}
            confidence = max(0.0, min(1.0, 1.0 - continuation_score))
            reason = 'semantic_topic_release' if topic_break else 'no_dependency_proof'
        return {'relation': relation, 'confidence': round(float(confidence), 6), 'selected_pair': selected_pair, 'selected_index': -1, 'scores': {'continuation': round(float(continuation_score), 6), 'answer_similarity': round(float(answer_similarity), 6), 'user_similarity': round(float(user_similarity), 6), 'combined_similarity': round(float(combined_similarity), 6), 'content_overlap': round(float(overlap), 6), 'signature_matches': signature_matches, 'core_signature_matches': core_signature_matches, 'continuation_semantics': round(float(continuation_semantics), 6), 'reference_semantics': round(float(reference_semantics), 6), 'memory_semantics': round(float(memory_semantics), 6), 'grammatical_reference': grammatical_reference, 'contextual_antecedent_dependency': contextual_antecedent_dependency, 'grammatical_anaphora': grammatical_anaphora, 'underspecified': underspecified, 'self_contained': self_contained, 'artifact_continuity': artifact_continuity, 'topic_break': topic_break, 'trajectory_dependency': trajectory_dependency, 'interrogative_ellipsis': bool(trajectory.get('interrogative_ellipsis')), 'orthographic_reference': deepcopy(trajectory.get('orthographic_reference') or {}), 'pending_input': bool(trajectory.get('pending_input')), 'explicit_structured_break': explicit_structured_break}, 'previous_turn': {'user': previous_user, 'april': previous_answer, 'meaning': deepcopy(meaning)}, 'current_task': {'operation': current_op, 'representation': current_rep, 'object': current_obj, 'goal': current_goal}, 'previous_task': {'operation': previous_op, 'representation': previous_rep, 'object': previous_obj, 'goal': previous_goal}, 'reason': reason, 'source': cls.VERSION, 'single_active_anchor': True, 'trajectory': deepcopy(trajectory), 'older_turns_are_historical_only': True}

class QuantumContextUnderstandingEngine:
    """
    Context-first semantic fusion layer.

    Purpose:
      1) reconstruct the active topic/thread from authentic USER↔APRIL history;
      2) resolve entities/coreference before downstream engines see the turn;
      3) distinguish current-turn structure ("first/second/third") from historical
         references ("the previous formula", "that image");
      4) describe the COMPLETE task as a multi-dimensional intent packet:
         operation + object + representation + input modality + output modality;
      5) use multilingual sentence embeddings as the primary semantic comparison
         when available, with the existing matrix engine as a deterministic fallback;
      6) optionally use local NLI only for genuinely ambiguous relations.

    This class never routes, calls a provider, executes tools, selects renderers,
    or mutates an answer. It produces an evidence/understanding packet consumed
    by the canonical interpretation engine.
    """
    VERSION = 'QUANTUM_CONTEXT_UNDERSTANDING_V4_FAST_HOTPATH'
    TOPIC_WINDOW = 12
    ENTITY_WINDOW = 8
    NLI_ENABLED = os.getenv('APRIL_ENABLE_CONTEXT_NLI', '0').strip().lower() in {'1', 'true', 'yes', 'on'}
    EMBEDDING_ENABLED = os.getenv('APRIL_ENABLE_CONTEXT_EMBEDDINGS', '0').strip().lower() in {'1', 'true', 'yes', 'on'}
    ACTION_UNIVERSE = ('answer', 'ask', 'explain', 'calculate', 'analyze', 'compare', 'summarize', 'list', 'retrieve', 'create', 'build', 'present', 'modify', 'correct', 'continue', 'recall', 'inspect', 'read', 'extract', 'classify', 'translate')
    OUTPUT_UNIVERSE = ('text', 'number', 'formula', 'code', 'link', 'table', 'graph', 'diagram', 'image', 'gallery', 'file', 'audio', 'video', 'memory', 'visual_context', 'action')
    INPUT_UNIVERSE = ('text', 'number', 'formula', 'code', 'link', 'image', 'screenshot', 'gallery', 'file', 'audio', 'video', 'visual_context')
    _ORDINAL_MAP = {'первый': 1, 'первая': 1, 'первое': 1, 'второй': 2, 'вторая': 2, 'второе': 2, 'третий': 3, 'третья': 3, 'третье': 3, 'четвертый': 4, 'четвёртый': 4, 'четвертая': 4, 'четвёртая': 4, 'пятый': 5, 'пятая': 5, 'пятое': 5, 'шестой': 6, 'шестая': 6, 'шестое': 6, 'седьмой': 7, 'седьмая': 7, 'седьмое': 7, 'восьмой': 8, 'восьмая': 8, 'восьмое': 8, 'девятый': 9, 'девятая': 9, 'девятое': 9, 'десятый': 10, 'десятая': 10, 'десятое': 10, 'first': 1, 'second': 2, 'third': 3, 'fourth': 4, 'fifth': 5, 'sixth': 6, 'seventh': 7, 'eighth': 8, 'ninth': 9, 'tenth': 10}
    _STOP = {'что', 'это', 'такое', 'как', 'кто', 'когда', 'где', 'куда', 'почему', 'зачем', 'какой', 'какая', 'какое', 'какие', 'сколько', 'скольких', 'который', 'которая', 'которое', 'которые', 'готово', 'готово', 'вот', 'сейчас', 'понимаю', 'мне', 'тебе', 'тебя', 'ты', 'вы', 'он', 'она', 'они', 'его', 'ее', 'её', 'их', 'ему', 'ей', 'им', 'меня', 'нас', 'вам', 'мы', 'я', 'можно', 'нужно', 'хочу', 'и', 'а', 'но', 'или', 'ещё', 'еще', 'да', 'нет', 'the', 'what', 'who', 'how', 'why', 'this', 'that', 'they', 'he', 'she', 'it', 'and', 'or', 'to', 'of', 'for', 'in', 'on', 'at', 'from', 'with'}

    def __init__(self, semantic_engine: 'QuantumInterpretationEngine') -> None:
        self.semantic_engine = semantic_engine
        self._nli = None
        self._nli_lock = threading.RLock()

    @staticmethod
    def _compact(value: Any, limit: int=800) -> str:
        return re.sub('\\s+', ' ', str(value or '').strip())[:limit]

    @staticmethod
    def _tokens(text: Any) -> list[str]:
        return re.findall('[A-Za-zА-Яа-яЁёЇїІіЄєҐґ0-9_]+', str(text or '').lower())

    @classmethod
    def _content_tokens(cls, text: Any) -> list[str]:
        return [token for token in cls._tokens(text) if len(token) >= 3 and token not in cls._STOP]

    @staticmethod
    def _semantic_stems(tokens: Sequence[str]) -> set[str]:
        values = {str(token).casefold() for token in tokens if str(token).strip()}
        if not values:
            return set()
        if SnowballStemmer is None:
            return values
        try:
            stemmer = SnowballStemmer('russian')
            return {stemmer.stem(token) if re.search('[А-Яа-яЁёЇїІіЄєҐґ]', token) else token for token in values}
        except Exception:
            return values

    @classmethod
    def _entities(cls, text: Any) -> list[dict[str, Any]]:
        source = str(text or '')
        found: list[dict[str, Any]] = []
        seen: set[str] = set()
        patterns = (('url', 'https?://[^\\s)\\]}>,]+'), ('email', '\\b[\\w.+-]+@[\\w.-]+\\.[A-Za-z]{2,}\\b'), ('proper_name', '\\b[А-ЯЁA-Z][а-яёa-z]+(?:\\s+[А-ЯЁA-Z][а-яёa-z]+){1,4}\\b'), ('proper_name', '\\b[А-ЯЁA-Z][а-яёa-z]{2,}\\b'), ('formula_symbol', '\\b(?:[A-Za-z](?:\\^[A-Za-z0-9+\\-]+)?|[A-Za-z]\\s*=\\s*[A-Za-z0-9^_()+*/.\\-]+)\\b'), ('number_expression', '(?<![\\w.])[-+]?\\d+(?:[.,]\\d+)?(?:\\s*[+\\-*/×÷]\\s*[-+]?\\d+(?:[.,]\\d+)?)+'), ('code_identifier', '\\b[A-Za-z_][A-Za-z0-9_]{2,}(?:\\.[A-Za-z_][A-Za-z0-9_]{1,})+\\b'))
        for kind, pattern in patterns:
            for match in re.finditer(pattern, source):
                value = match.group(0).strip('.,:;()[]{}<>"\'')
                if not value:
                    continue
                if kind == 'proper_name' and len(value.split()) == 1:
                    if value.casefold() in cls._STOP:
                        continue
                key = (kind, value.casefold())
                if key in seen:
                    continue
                seen.add(key)
                found.append({'type': kind, 'value': value, 'start': match.start(), 'end': match.end()})
        return found[:48]

    @classmethod
    def _ordinals(cls, text: Any) -> list[int]:
        source = str(text or '').lower()
        hits = []
        for word, number in cls._ORDINAL_MAP.items():
            pos = source.find(word)
            if pos >= 0:
                hits.append((pos, number))
        hits.sort(key=lambda item: item[0])
        result = []
        for _, value in hits:
            if value not in result:
                result.append(value)
        return result

    @classmethod
    def _request_segments(cls, text: Any) -> list[dict[str, Any]]:
        source = str(text or '').strip()
        if not source:
            return []
        numbered = list(re.finditer('(?:^|\\n|\\s)(\\d{1,3})[.)]\\s+(.+?)(?=(?:\\s+\\d{1,3}[.)]\\s+)|\\n+\\s*(?:\\d{1,3})[.)]\\s+|$)', source, flags=re.S))
        if len(numbered) >= 2:
            return [{'segment_index': int(match.group(1)), 'text': re.sub('\\s+', ' ', match.group(2)).strip(), 'source': 'numbered_current_turn'} for match in numbered[:32]]
        pieces = [piece.strip(' \t') for piece in re.split('(?:\\n{2,}|;(?=\\s+)|\\s+\\band\\b\\s+|\\s+\\bи\\b\\s+)', source, flags=re.I) if piece.strip()]
        if len(pieces) >= 2:
            return [{'segment_index': idx, 'text': re.sub('\\s+', ' ', piece), 'source': 'semantic_clause_segmentation'} for idx, piece in enumerate(pieces[:16], start=1)]
        return [{'segment_index': 1, 'text': re.sub('\\s+', ' ', source), 'source': 'single_current_turn'}]

    @classmethod
    def _modality_evidence(cls, text: str, *, semantic: dict[str, Any] | None=None, cognition: dict[str, Any] | None=None, state: dict[str, Any] | None=None) -> dict[str, Any]:
        """
        Measure modalities from the current utterance plus concrete multimodal
        payloads. Serialized semantic state is never treated as user language.
        This prevents remembered words such as "table", "file" or "audio" from
        becoming accidental output requests on a later turn.
        """
        text = str(text or '')
        sources = (semantic if isinstance(semantic, dict) else {}, cognition if isinstance(cognition, dict) else {}, state if isinstance(state, dict) else {})
        code = bool(re.search('```[\\s\\S]*?```|(?:\\bdef\\b|\\bclass\\b|\\bimport\\b|\\bfunction\\b)\\s+\\w+', text, re.I))
        link = bool(re.search('https?://|www\\.[\\w.-]+\\.', text, re.I))
        screenshot = bool(re.search('\\b(?:скриншот|скрин|screenshot|screen shot|снимок экрана|изображен(?:ие|ия) на экране)\\b', text, re.I))
        formula = bool(re.search('(?:[A-Za-z]\\s*=\\s*[A-Za-z0-9^_()+*/.\\-]+|\\b(?:mc\\^2|E\\s*=\\s*mc2)\\b|\\\\frac|\\\\sqrt)', text, re.I))
        numeric = bool(re.search('(?<![\\w.])[-+]?\\d+(?:[.,]\\d+)?(?:\\s*[+\\-*/×÷]\\s*[-+]?\\d+(?:[.,]\\d+)?)+', text))
        image_signal = screenshot or bool(re.search('\\b(?:изображение|картинка|фото|фотография|image|picture|photo)\\b', text, re.I))
        table_signal = bool(re.search('\\b(?:таблица|таблич(?:а|ный)|table|rows?|columns?)\\b', text, re.I))
        graph_signal = bool(re.search('\\b(?:график|графика|chart|plot|curve|диаграмма данных)\\b', text, re.I))
        diagram_signal = bool(re.search('\\b(?:схема|черт[её]ж|diagram|schematic|flowchart|блок-схема)\\b', text, re.I))
        audio_signal = bool(re.search('\\b(?:аудио|голос|audio|voice|sound)\\b', text, re.I))
        video_signal = bool(re.search('\\b(?:видео|ролик|video)\\b', text, re.I))
        file_signal = bool(re.search('\\b(?:файл|документ|attachment|file|pdf|docx?)\\b', text, re.I))

        def concrete(value: Any) -> bool:
            if value in (None, '', [], {}, False, 0, 0.0):
                return False
            if isinstance(value, (int, float, bool)):
                return False
            if isinstance(value, dict):
                score_keys = {'score', 'scores', 'weights', 'measurements', 'representation_scores', 'object_scores'}
                if set(map(str.lower, value.keys())) & score_keys and len(value) <= 8:
                    return False
                return bool(value)
            return bool(value)
        for src in sources:
            for key in ('images', 'image', 'vision_context', 'vision'):
                if key in src and concrete(src.get(key)):
                    image_signal = True
            for key in ('files', 'file_context', 'attachment', 'attachments'):
                if key in src and concrete(src.get(key)):
                    file_signal = True
            for key in ('audio', 'voice_context', 'voice'):
                if key in src and concrete(src.get(key)):
                    audio_signal = True
            for key in ('video', 'video_context'):
                if key in src and concrete(src.get(key)):
                    video_signal = True
            if (key := '_incoming_visual_evidence'):
                incoming = src.get(key)
                if concrete(incoming):
                    image_signal = True
                    screenshot = True
        inputs = ['text'] if text.strip() else []
        if numeric:
            inputs.append('number')
        if formula:
            inputs.append('formula')
        if code:
            inputs.append('code')
        if link:
            inputs.append('link')
        if image_signal:
            inputs.append('screenshot' if screenshot else 'image')
        if table_signal:
            inputs.append('table')
        if graph_signal:
            inputs.append('graph')
        if diagram_signal:
            inputs.append('diagram')
        if file_signal:
            inputs.append('file')
        if audio_signal:
            inputs.append('audio')
        if video_signal:
            inputs.append('video')
        return {'inputs': list(dict.fromkeys(inputs)), 'flags': {'text': bool(text.strip()), 'number': numeric, 'formula': formula, 'code': code, 'link': link, 'image': image_signal, 'screenshot': screenshot, 'table': table_signal, 'graph': graph_signal, 'diagram': diagram_signal, 'file': file_signal, 'audio': audio_signal, 'video': video_signal}, 'source': 'current_turn_multimodal_measurement', 'lexical_routing': False}

    @classmethod
    def _task_actions(cls, text: str, profile: dict[str, Any], modality: dict[str, Any]) -> dict[str, Any]:
        """Compile the COMPLETE current-turn action/output vector.

        The whole request is interpreted as an ordered set of semantic segments.
        Each segment is measured independently and the resulting output plan is
        merged without allowing one dominant representation to erase another.
        The primary representation is still useful downstream, but it is never
        treated as the complete task when the user asked for multiple results.
        """
        scores = {key: float(value or 0.0) for key, value in (profile.get('operation_scores') or {}).items()}
        objects = {key: float(value or 0.0) for key, value in (profile.get('object_scores') or {}).items()}
        reps = {key: float(value or 0.0) for key, value in (profile.get('representation_scores') or {}).items()}
        op_rank = sorted(scores.items(), key=lambda item: item[1], reverse=True)
        best = op_rank[0][0] if op_rank else 'answer'
        flags = modality.get('flags', {}) if isinstance(modality, dict) else {}
        if flags.get('number') and re.search('(?<![\\w.])[-+]?\\d+(?:[.,]\\d+)?\\s*[+\\-*/×÷]\\s*[-+]?\\d+(?:[.,]\\d+)?(?![\\w.])', text):
            best = 'calculate'
        compatible = {'formula': {'calculate', 'answer', 'explain', 'present', 'build', 'modify'}, 'code': {'build', 'modify', 'present', 'explain', 'analyze', 'list'}, 'link': {'retrieve', 'present', 'answer', 'list', 'explain'}, 'table': {'build', 'present', 'compare', 'list', 'explain', 'analyze'}, 'graph': {'build', 'present', 'calculate', 'analyze', 'compare', 'list', 'explain'}, 'diagram': {'build', 'present', 'modify', 'explain', 'analyze'}, 'image': {'build', 'present', 'modify', 'create'}, 'gallery': {'build', 'present', 'compare', 'list'}, 'file': {'retrieve', 'present', 'analyze', 'read'}, 'audio': {'build', 'present', 'retrieve', 'analyze', 'read'}, 'video': {'build', 'present', 'retrieve', 'analyze', 'read'}}
        candidates = [{'action': action, 'score': round(float(score), 6)} for action, score in sorted(scores.items(), key=lambda item: item[1], reverse=True) if score >= 0.05]
        segments = cls._request_segments(text)
        segment_plans: list[dict[str, Any]] = []
        ordered_outputs: list[str] = []

        def append_output(label: str, segment_index: int, source: str, score: float=0.0, segment_text: str='') -> None:
            label = _clean_representation(label)
            if not label or label == 'text':
                return
            if label not in ordered_outputs:
                ordered_outputs.append(label)
            segment_plans.append({'segment_index': segment_index, 'output': label, 'segment_text': cls._compact(segment_text, 1200), 'source': source, 'score': round(float(score or 0.0), 6)})
        for segment in segments:
            segment_text = cls._compact(segment.get('text'))
            if not segment_text:
                continue
            segment_modality = cls._modality_evidence(segment_text)
            sf = segment_modality.get('flags', {}) if isinstance(segment_modality, dict) else {}
            segment_scores = {'representation': QUANTUM_INTERPRETATION_ENGINE._family_scores(segment_text, 'representation', REPRESENTATION_HYPOTHESES), 'object': QUANTUM_INTERPRETATION_ENGINE._family_scores(segment_text, 'object', OBJECT_HYPOTHESES), 'operation': QUANTUM_INTERPRETATION_ENGINE._operation_family_scores(segment_text), 'goal': QUANTUM_INTERPRETATION_ENGINE._family_scores(segment_text, 'goal', GOAL_HYPOTHESES)}
            segment_ops = segment_scores['operation']
            segment_op = max(segment_ops.items(), key=lambda item: float(item[1] or 0.0))[0] if segment_ops else 'answer'
            structural_flags = {'code': bool(sf.get('code')), 'image': bool(sf.get('image')) and (not bool(sf.get('screenshot'))), 'gallery': False, 'table': bool(sf.get('table')), 'graph': bool(sf.get('graph')), 'diagram': bool(sf.get('diagram')), 'formula': bool(sf.get('formula')), 'link': bool(sf.get('link')), 'file': bool(sf.get('file')), 'audio': bool(sf.get('audio')), 'video': bool(sf.get('video'))}
            for label, active in structural_flags.items():
                if active:
                    append_output(label, int(segment.get('segment_index', 1)), 'segment_modality', 1.0, segment_text)
            rep_items = sorted(segment_scores['representation'].items(), key=lambda item: float(item[1] or 0.0), reverse=True)
            obj_items = sorted(segment_scores['object'].items(), key=lambda item: float(item[1] or 0.0), reverse=True)
            top_rep, top_rep_score = rep_items[0] if rep_items else ('', 0.0)
            top_obj, top_obj_score = obj_items[0] if obj_items else ('', 0.0)
            for rep_pos, (label, score) in enumerate(rep_items[:5]):
                label_score = float(score or 0.0)
                object_score = float(segment_scores['object'].get(label, 0.0) or 0.0)
                compatible_op = segment_op in compatible.get(label, set())
                semantic_agreement = label_score >= 0.1 and (object_score >= 0.08 or (rep_pos == 0 and label_score >= 0.16 and compatible_op))
                if semantic_agreement:
                    append_output(label, int(segment.get('segment_index', 1)), 'segment_representation_matrix', max(label_score, object_score), segment_text)
            if top_obj in STRUCTURED_REPRESENTATIONS:
                obj_score = float(top_obj_score or 0.0)
                if obj_score >= 0.05 and segment_op in compatible.get(top_obj, set()):
                    append_output(top_obj, int(segment.get('segment_index', 1)), 'segment_object_matrix', obj_score, segment_text)
        if flags.get('number') and best in {'calculate', 'answer'}:
            if 'number' not in ordered_outputs:
                ordered_outputs.append('number')
        compatible_object_candidates = []
        for label, obj_score in objects.items():
            if label not in cls.OUTPUT_UNIVERSE or label == 'text':
                continue
            if best in compatible.get(label, set()) and obj_score >= 0.08:
                compatible_object_candidates.append((label, obj_score))
        for label, obj_score in sorted(compatible_object_candidates, key=lambda item: item[1], reverse=True)[:4]:
            append_output(label, 1, 'whole_turn_object_matrix', obj_score)
        for label, rep_score in sorted(reps.items(), key=lambda item: item[1], reverse=True):
            if label == 'text' or label not in cls.OUTPUT_UNIVERSE:
                continue
            if float(rep_score or 0.0) < 0.1:
                continue
            if best in compatible.get(label, set()) or label in {'formula' if flags.get('formula') else '', 'code' if flags.get('code') else '', 'link' if flags.get('link') else '', 'table' if flags.get('table') else '', 'graph' if flags.get('graph') else '', 'diagram' if flags.get('diagram') else '', 'image' if flags.get('image') and (not flags.get('screenshot')) else ''}:
                append_output(label, 1, 'whole_turn_representation_matrix', rep_score)
        if 'image' in ordered_outputs and 'gallery' in ordered_outputs and (not any((item.get('output') == 'gallery' and item.get('source') == 'segment_modality' for item in segment_plans))):
            image_score = float(reps.get('image', 0.0) or 0.0)
            gallery_score = float(reps.get('gallery', 0.0) or 0.0)
            weaker = 'gallery' if image_score >= gallery_score else 'image'
            ordered_outputs = [x for x in ordered_outputs if x != weaker]
            segment_plans = [item for item in segment_plans if item.get('output') != weaker or item.get('source') == 'segment_modality']
        if flags.get('screenshot'):
            append_output('visual_context', 1, 'whole_turn_screenshot_input', 1.0)
        elif flags.get('image'):
            append_output('image', 1, 'whole_turn_image_input', 1.0)
        for label in ('table', 'graph', 'diagram', 'formula', 'link', 'file', 'audio', 'video', 'code'):
            if flags.get(label):
                append_output(label, 1, 'whole_turn_modality', 1.0)
        if best == 'calculate':
            strong_structured = [item for item in ordered_outputs if item in {'formula', 'graph', 'table', 'diagram', 'image', 'gallery', 'code', 'link', 'file', 'audio', 'video', 'action', 'scene', 'memory', 'visual_context'} and (bool(flags.get(item)) or float(reps.get(item, 0.0) or 0.0) >= 0.22)]
            if not strong_structured:
                ordered_outputs = ['text']
                segment_plans = []
        if ordered_outputs and 'text' not in ordered_outputs:
            ordered_outputs.append('text')
        return {'primary': best, 'primary_score': float(scores.get(best, 0.0) or 0.0), 'candidates': candidates[:24], 'requested_outputs': list(dict.fromkeys(ordered_outputs)), 'output_segments': segment_plans, 'output_evidence': {'object_scores': {k: round(float(v), 6) for k, v in sorted(objects.items(), key=lambda item: item[1], reverse=True)[:16]}, 'representation_scores': {k: round(float(v), 6) for k, v in sorted(reps.items(), key=lambda item: item[1], reverse=True)[:16]}, 'segment_count': len(segments), 'complete_request': True}, 'source': 'complete_current_turn_task_matrix'}

    @classmethod
    def _topic_label(cls, pair: dict[str, str], scene: dict[str, Any] | None=None) -> str:
        texts = [str(pair.get('user') or ''), str(pair.get('assistant') or '')]
        if isinstance(scene, dict):
            texts.extend([str(scene.get('topic') or ''), str(scene.get('summary') or '')])
        entities = cls._entities(' '.join(texts))
        names = [x['value'] for x in entities if x['type'] == 'proper_name']
        if names:
            return max(names, key=lambda x: (len(x.split()), len(x)))
        content = [token for token in cls._content_tokens(' '.join(texts)) if not token.isdigit()]
        if content:
            ranked = sorted(set(content), key=lambda x: (-len(x), x))
            return ' '.join(ranked[:4])
        return ''

    def _embedding_similarity(self, left: str, right: str) -> tuple[float, str]:
        if not left or not right:
            return (0.0, 'none')
        if self.EMBEDDING_ENABLED and os.getenv('APRIL_ALLOW_CONTEXT_MODEL_DOWNLOAD', '0').strip().lower() in {'1', 'true', 'yes', 'on'}:
            try:
                if self.semantic_engine._semantic_encoder is None:
                    try:
                        if SentenceTransformer is not None:
                            self.semantic_engine._semantic_encoder = SentenceTransformer(SEMANTIC_MODEL_NAME)
                    except Exception:
                        self.semantic_engine._semantic_encoder = None
                result = self.semantic_engine.similarity(left, right)
                if result.get('measured'):
                    return (float(result.get('score', 0.0)), str(result.get('source', 'embedding')))
            except Exception:
                pass
        try:
            result = self.semantic_engine.similarity(left, right)
            return (float(result.get('score', 0.0)), str(result.get('source', 'matrix')))
        except Exception:
            return (0.0, 'none')

    @staticmethod
    def _shared_entities(current_entities: list[dict[str, Any]], prior_entities: list[dict[str, Any]]) -> list[str]:
        current = {str(x.get('value')).casefold() for x in current_entities}
        return [str(x.get('value')) for x in prior_entities if str(x.get('value')).casefold() in current][:16]

    def _topic_profiles(self, current: str, recent_pairs: list[dict[str, str]], active_topic: str, previous_scene: dict[str, Any] | None) -> list[dict[str, Any]]:
        profiles = []
        current_entities = QuantumContextUnderstandingEngine._entities(current)
        candidates = list(reversed(recent_pairs[-self.TOPIC_WINDOW:]))
        if active_topic:
            candidates.insert(0, {'user': active_topic, 'assistant': active_topic, 'source': 'active_topic'})
        for idx, pair in enumerate(candidates, start=1):
            user = self._compact(pair.get('user'))
            assistant = self._compact(pair.get('assistant'), 1200)
            pair_text = f'{user} {assistant}'.strip()
            if not pair_text:
                continue
            sim, source = self._embedding_similarity(current, pair_text)
            prior_entities = self._entities(pair_text)
            shared = self._shared_entities(current_entities, prior_entities)
            current_terms = set(QuantumContextUnderstandingEngine._content_tokens(current))
            prior_terms = set(self._content_tokens(pair_text))
            lexical_overlap = len(current_terms & prior_terms) / max(1, len(current_terms | prior_terms))
            recency = 1.0 / (1.0 + 0.12 * (idx - 1))
            topic_label = self._topic_label(pair, previous_scene)
            topic_score = 0.58 * sim + 0.22 * (len(shared) / max(1, min(4, len(current_entities) or 1))) + 0.12 * lexical_overlap + 0.08 * recency
            profiles.append({'pair_index': idx, 'topic': topic_label, 'user': user, 'assistant': assistant, 'semantic_similarity': round(float(sim), 6), 'shared_entities': shared, 'lexical_overlap': round(float(lexical_overlap), 6), 'recency': round(float(recency), 6), 'score': round(float(min(1.0, topic_score)), 6), 'source': source})
        return sorted(profiles, key=lambda item: item['score'], reverse=True)

    @classmethod
    def _is_current_turn_reference(cls, text: str) -> bool:
        source = str(text or '').lower()
        ordinals = cls._ordinals(source)
        numbered_items = len(cls._request_segments(source)) >= 2
        return bool(ordinals) and numbered_items

    @classmethod
    def _coreference_candidates(cls, current: str, prior_text: str, topic_profiles: list[dict[str, Any]]) -> list[dict[str, Any]]:
        ordinals = cls._ordinals(current)
        local_reference = cls._is_current_turn_reference(current)
        if not prior_text.strip() or local_reference:
            if local_reference:
                return [{'type': 'current_turn_ordinal', 'ordinal_targets': ordinals, 'historical_reference_blocked': True, 'candidates': [], 'confidence': 0.98}]
            return []
        entities = cls._entities(prior_text)
        scored = []
        for entity in entities:
            kind = entity['type']
            value = entity['value']
            score = 0.0
            if kind == 'proper_name':
                score += 0.34
            elif kind in {'formula_symbol', 'number_expression', 'code_identifier'}:
                score += 0.22
            if topic_profiles:
                shared = any((value.casefold() in {str(x).casefold() for x in profile.get('shared_entities', [])} for profile in topic_profiles[:4]))
                topic_labels = {str(profile.get('topic') or '').casefold() for profile in topic_profiles[:4] if profile.get('topic')}
                if shared:
                    score += 0.34
                if value.casefold() in topic_labels:
                    score += 0.46
            scored.append({'entity': value, 'type': kind, 'score': round(min(1.0, score), 6)})
        scored.sort(key=lambda item: item['score'], reverse=True)
        if ordinals:
            numbered = []
            for match in re.finditer('(?:^|\\s)(\\d{1,3})[.)]\\s+(.+?)(?=(?:\\s+\\d{1,3}[.)]\\s+)|$)', prior_text, flags=re.S):
                numbered.append({'index': int(match.group(1)), 'content': re.sub('\\s+', ' ', match.group(2)).strip()[:1000]})
            ordinal_target = ordinals[0]
            selected = [item for item in numbered if item['index'] == ordinal_target]
            if selected:
                return [{'type': 'historical_ordinal', 'ordinal_targets': ordinals, 'historical_reference_blocked': False, 'candidates': [{'entity': f'item_{ordinal_target}', 'type': 'historical_list_item', 'content': selected[0]['content'], 'score': 0.94}], 'confidence': 0.94}]
        return [{'type': 'historical_entity', 'ordinal_targets': ordinals, 'historical_reference_blocked': False, 'candidates': scored[:8], 'confidence': round(float(scored[0]['score']) if scored else 0.0, 6)}]

    def _nli_verify(self, current: str, hypothesis_pairs: list[tuple[str, str]]) -> list[dict[str, Any]]:
        """Use local NLI as an ambiguity verifier, never as the primary router."""
        if not self.NLI_ENABLED or hf_pipeline is None or (not hypothesis_pairs):
            return []
        labels = [str(label) for label, _ in hypothesis_pairs[:4]]
        with self._nli_lock:
            try:
                if self._nli is None:
                    self._nli = hf_pipeline('zero-shot-classification', model=NLI_MODEL_NAME, tokenizer=NLI_MODEL_NAME)
            except Exception:
                return []
        try:
            result = self._nli(current, candidate_labels=labels, hypothesis_template='This user request is {} relative to the previous conversation.', multi_label=False)
            out = []
            for label, score in zip(result.get('labels', []) if isinstance(result, dict) else [], result.get('scores', []) if isinstance(result, dict) else []):
                out.append({'hypothesis': str(label), 'score': round(float(score), 6)})
            return out
        except Exception:
            return []

    def analyze(self, current: str, *, history: list[dict[str, Any]] | None=None, state: dict[str, Any] | None=None, semantic: dict[str, Any] | None=None, cognition: dict[str, Any] | None=None, active_topic: str='', active_goal: str='', previous_scene: dict[str, Any] | None=None, semantic_profile: dict[str, Any] | None=None, canonical_dialogue: dict[str, Any] | None=None) -> dict[str, Any]:
        current = self._compact(current, 2200)
        history = history if isinstance(history, list) else []
        state = state if isinstance(state, dict) else {}
        semantic = semantic if isinstance(semantic, dict) else {}
        cognition = cognition if isinstance(cognition, dict) else {}
        semantic_profile = semantic_profile if isinstance(semantic_profile, dict) else {}
        recent_pairs = []
        pending_user = ''
        for item in history:
            if not isinstance(item, dict):
                continue
            metadata = item.get('metadata') if isinstance(item.get('metadata'), dict) else {}
            if metadata.get('internal_context') or metadata.get('internal_turn'):
                continue
            role = str(item.get('role') or '').lower()
            content = self._compact(item.get('content') or item.get('text') or item.get('answer'), 1200)
            if role in {'user', 'human'}:
                pending_user = content
            elif role in {'assistant', 'april', 'bot'} and pending_user:
                recent_pairs.append({'user': pending_user, 'assistant': content, 'source': 'authentic_dialogue'})
                pending_user = ''
        recent_pairs = recent_pairs[-self.TOPIC_WINDOW:]
        if isinstance(canonical_dialogue, dict) and canonical_dialogue:
            dialogue_relation = dict(canonical_dialogue)
        else:
            dialogue_relation = {'relation': 'NEW', 'confidence': 0.0, 'selected_pair': {}, 'selected_index': -1, 'source': 'canonical_dialogue_not_provided'}
        canonical_three_way = str(dialogue_relation.get('three_way_relation') or dialogue_relation.get('relation') or 'NEW').upper()
        if canonical_three_way == 'CONTINUE':
            selected_pair = dialogue_relation.get('selected_memory_operand') if isinstance(dialogue_relation.get('selected_memory_operand'), dict) else {}
        else:
            selected_pair = {}
        topic_profiles = self._topic_profiles(current, recent_pairs, self._compact(active_topic, 500), previous_scene)
        top_topic = topic_profiles[0] if topic_profiles else {}
        current_topic_label = self._topic_label({'user': current, 'assistant': ''}, previous_scene)
        reconstructed_topic = current_topic_label if top_topic and float(top_topic.get('semantic_similarity', 0.0) or 0.0) < 0.24 else self._compact(top_topic.get('topic'), 500) or self._compact(active_topic, 500) or current_topic_label or self._compact(current, 500)
        modality = self._modality_evidence(current, semantic=semantic, cognition=cognition, state=state)
        request_segments = self._request_segments(current)
        ordinals = self._ordinals(current)
        prior_text = ' '.join([self._compact(pair.get('user'), 700) + ' ' + self._compact(pair.get('assistant'), 1000) for pair in recent_pairs[-self.ENTITY_WINDOW:]])
        coreference = self._coreference_candidates(current, prior_text, topic_profiles)
        semantic_operation_scores = semantic_profile.get('operation_scores')
        if not isinstance(semantic_operation_scores, dict):
            semantic_operation_scores = {}
        action_matrix = self._task_actions(current, {'operation_scores': semantic_operation_scores, 'object_scores': semantic_profile.get('object_scores', {}) if isinstance(semantic_profile.get('object_scores'), dict) else {}, 'representation_scores': semantic_profile.get('representation_scores', {}) if isinstance(semantic_profile.get('representation_scores'), dict) else {}}, modality)
        topic_similarity = float(top_topic.get('semantic_similarity', 0.0) or 0.0)
        shared_entities = list(top_topic.get('shared_entities') or [])
        current_entities = QuantumContextUnderstandingEngine._entities(current)
        topic_shift = bool(top_topic and topic_similarity < 0.24 and (not shared_entities) and (len(current_entities) > 0))
        if topic_shift and current_topic_label:
            reconstructed_topic = current_topic_label
        local_compound = len(request_segments) > 1
        self_contained = bool(not coreference or all((item.get('historical_reference_blocked') for item in coreference)))
        historical_reference = bool(coreference and any((not item.get('historical_reference_blocked') for item in coreference)) and (not local_compound) and (not self_contained))
        if topic_shift:
            relation = 'NEW_TOPIC'
        elif historical_reference:
            relation = 'CONTINUE_TOPIC'
        elif local_compound:
            relation = 'SAME_TOPIC' if top_topic and (not topic_shift) else 'NEW_TOPIC'
        elif topic_similarity >= 0.3 or shared_entities:
            relation = 'SAME_TOPIC'
        else:
            relation = 'INDEPENDENT'
        if historical_reference and coreference and (coreference[0].get('confidence', 0.0) < 0.34):
            historical_reference = False
            relation = 'SAME_TOPIC' if topic_similarity >= 0.22 else 'INDEPENDENT'
        if canonical_three_way == 'CONTINUE':
            relation = 'CONTINUE_TOPIC'
            historical_reference = False
        elif canonical_three_way == 'RECALL':
            relation = 'RECALL'
            historical_reference = True
        else:
            relation = 'NEW_TOPIC'
            historical_reference = False
        discourse_confidence = max(0.0, min(1.0, 0.62 * topic_similarity + 0.18 * min(1.0, len(shared_entities) / 2.0) + 0.12 * (1.0 if relation in {'CONTINUE_TOPIC', 'SAME_TOPIC'} else 0.0) + 0.08 * (1.0 if self_contained else 0.0)))
        if relation == 'NEW_TOPIC' and (not top_topic):
            discourse_confidence = max(discourse_confidence, 0.82)
        if historical_reference:
            discourse_confidence = max(discourse_confidence, 0.72)
        if local_compound:
            discourse_confidence = max(discourse_confidence, 0.8)
        if canonical_three_way == 'RECALL' and selected_pair:
            reconstructed_topic = self._compact(selected_pair.get('user') or selected_pair.get('topic') or current_topic_label, 500)
        elif canonical_three_way == 'CONTINUE' and selected_pair:
            reconstructed_topic = self._compact(selected_pair.get('user') or selected_pair.get('topic') or top_topic.get('topic') or current_topic_label, 500)
        elif topic_shift and current_topic_label:
            reconstructed_topic = current_topic_label
        elif relation == 'SAME_TOPIC' and top_topic and top_topic.get('topic'):
            reconstructed_topic = self._compact(top_topic.get('topic'), 500)
        elif relation == 'CONTINUE_TOPIC' and top_topic and top_topic.get('topic'):
            reconstructed_topic = self._compact(top_topic.get('topic'), 500)
        hypothesis_pairs = []
        if relation in {'SAME_TOPIC', 'CONTINUE_TOPIC'} and top_topic:
            hypothesis_pairs.append(('continuation', f"The current user request continues the same subject as: {top_topic.get('user', '')}"))
        if relation == 'NEW_TOPIC':
            hypothesis_pairs.append(('new_topic', f"The current user request starts a different subject from: {top_topic.get('user', '')}"))
        if historical_reference and coreference and coreference[0].get('candidates'):
            hypothesis_pairs.append(('reference', f"The current request refers to: {coreference[0]['candidates'][0]['entity']}"))
        nli = self._nli_verify(current, hypothesis_pairs)
        return {'version': self.VERSION, 'topic': {'active': reconstructed_topic, 'relation': relation, 'confidence': round(float(discourse_confidence), 6), 'similarity_to_best_pair': round(topic_similarity, 6), 'topic_shift': topic_shift, 'best_pair': top_topic, 'candidates': topic_profiles[:8], 'source': 'multilingual_embedding_topic_tracking'}, 'dialogue_selection': {**dialogue_relation, 'selected_memory_operand': selected_pair, 'memory_role': canonical_three_way}, 'entities': {'current': current_entities[:24], 'shared_with_active_topic': shared_entities[:16], 'coreference': coreference, 'source': 'semantic_entity_graph'}, 'turn_structure': {'segments': request_segments, 'segment_count': len(request_segments), 'ordinals': ordinals, 'local_ordinal_reference': bool(local_compound and ordinals), 'historical_ordinal_reference_blocked': bool(local_compound and ordinals), 'source': 'current_turn_structure'}, 'discourse': {'relation': relation, 'continuation': relation == 'CONTINUE_TOPIC', 'same_topic': relation in {'CONTINUE_TOPIC', 'RECALL'}, 'new_topic': relation == 'NEW_TOPIC', 'independent': relation == 'NEW_TOPIC', 'three_way_relation': canonical_three_way, 'selected_memory_operand': selected_pair, 'historical_reference': historical_reference, 'self_contained': self_contained, 'confidence': round(float(discourse_confidence), 6), 'source': 'topic_entity_discourse_fusion'}, 'task': {'actions': action_matrix, 'input_modalities': modality.get('inputs', []), 'input_evidence': modality, 'requested_outputs': action_matrix.get('requested_outputs', []), 'output_segments': action_matrix.get('output_segments', []), 'active_goal': self._compact(active_goal, 700), 'source': 'unified_multimodal_task_matrix'}, 'verification': {'nli': nli, 'performed': bool(nli), 'source': 'local_nli_verifier' if nli else 'not_run'}, 'context_contract': {'topic': reconstructed_topic, 'relation': relation, 'reference_entities': [item.get('entity') for item in (coreference[0].get('candidates', []) if coreference else []) if item.get('entity')][:8], 'local_current_turn_structure': bool(local_compound), 'historical_memory_allowed': bool(canonical_three_way in {'CONTINUE', 'RECALL'}), 'three_way_relation': canonical_three_way, 'selected_memory_operand': selected_pair, 'historical_reference_blocked_for_local_ordinals': bool(local_compound and ordinals), 'multimodal_inputs': modality.get('inputs', []), 'requested_outputs': action_matrix.get('requested_outputs', []), 'decision_owner': DECISION_OWNER}, 'decision_owner': DECISION_OWNER, 'evidence_only': True}

class QuantumInterpretationEngine:
    """
    One semantic engine. It measures evidence, resolves the user's task and
    freezes one production interpretation. Evidence never becomes a renderer
    command by itself. No lexical routing, no domain/capability gates and no
    silent renderer fallback.
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._cache = {}
        self._cache_limit = 256
        self._vectorizer = None
        self._prototype_matrix = None
        self._prototype_index = {}
        self._semantic_encoder = None
        self._compile_matrix()

    @staticmethod
    def normalize(text: Any) -> str:
        return re.sub('\\s+', ' ', str(text or '').strip())

    @staticmethod
    def _tokens(text: str) -> list[str]:
        return re.findall('[A-Za-zА-Яа-яЁёЇїІіЄєҐґ0-9_]+', str(text or '').lower())

    def _compile_matrix(self):
        families = (('dialogue', SEMANTIC_TURN_PROTOTYPES), ('representation', REPRESENTATION_HYPOTHESES), ('domain', DOMAIN_HYPOTHESES), ('capability', CAPABILITY_HYPOTHESES), ('operation', OPERATION_HYPOTHESES), ('object', OBJECT_HYPOTHESES), ('goal', GOAL_HYPOTHESES), ('visual_schema', VISUAL_SCHEMA_HYPOTHESES))
        docs = []
        for family, vocab in families:
            for label, description in vocab.items():
                self._prototype_index[f'{family}:{label}'] = len(docs)
                docs.append(description)
        if TfidfVectorizer is not None and docs:
            self._vectorizer = TfidfVectorizer(analyzer='char_wb', ngram_range=(3, 5), lowercase=True, sublinear_tf=True)
            self._prototype_matrix = self._vectorizer.fit_transform(docs)
        if APRIL_ENABLE_HEAVY_HOTPATH and os.getenv('APRIL_ALLOW_CONTEXT_MODEL_DOWNLOAD', '0').strip().lower() in {'1', 'true', 'yes', 'on'} and (SentenceTransformer is not None):
            try:
                self._semantic_encoder = SentenceTransformer(SEMANTIC_MODEL_NAME)
            except Exception:
                self._semantic_encoder = None

    @staticmethod
    def _semantic_focus_text(text: str) -> str:
        lines = []
        for line in str(text or '').splitlines():
            s = line.strip()
            if not s:
                continue
            nums = re.findall('[-+]?\\\\d+(?:[.,]\\\\d+)?', s)
            if len(nums) >= 2 and re.search('(?:—|–|-|:)', s):
                continue
            lines.append(s)
        return ' '.join(lines)

    def _negated_representation_labels(self, text: str) -> set[str]:
        source = self.normalize(text).lower()
        negated = set()
        matches = re.findall('(?:не|not)\\s+(?:как|as)\\s+([^.;!?]+)', source)
        if not matches:
            return negated
        negated_text = ' '.join(matches)
        negated_tokens = {token for token in self._tokens(negated_text) if len(token) >= 4}
        if not negated_tokens:
            return negated
        for label, hypothesis in REPRESENTATION_HYPOTHESES.items():
            hypothesis_tokens = {token for token in self._tokens(hypothesis) if len(token) >= 4 and (not token.isascii())}
            if hypothesis_tokens & negated_tokens:
                negated.add(label)
        return negated

    def _family_scores(self, text, family, vocab):
        text = self.normalize(text)
        if not text:
            return {k: 0.0 for k in vocab}
        if self._semantic_encoder is not None:
            try:
                q = self._semantic_encoder.encode([text], normalize_embeddings=True)[0]
                d = self._semantic_encoder.encode(list(vocab.values()), normalize_embeddings=True)
                vals = (d @ q + 1.0) / 2.0
                return {k: max(0.0, min(1.0, float(v))) for k, v in zip(vocab, vals)}
            except Exception:
                pass
        if self._vectorizer is not None and self._prototype_matrix is not None and (cosine_similarity is not None):
            q = self._vectorizer.transform([text])
            result = {}
            for label in vocab:
                idx = self._prototype_index[f'{family}:{label}']
                similarity_value = cosine_similarity(q, self._prototype_matrix[idx])
                score = float(similarity_value[0, 0])
                result[label] = max(0.0, min(1.0, score))
            return result
        tokens = set(self._tokens(text))
        result = {}
        for label, description in vocab.items():
            words = set(self._tokens(description))
            result[label] = min(1.0, len(tokens & words) / max(2.0, len(words) * 0.2))
        return result

    def _operation_family_scores(self, text: str) -> dict[str, float]:
        """Measure operation hypotheses from semantic and morphological evidence.

        No command/phrase trigger table is used. Exact token overlap is only one
        measurement; inflectional similarity is derived mechanically from token
        shapes so forms such as an imperative and its nominal operation converge.
        """
        scores = self._family_scores(text, 'operation', OPERATION_HYPOTHESES)
        query_tokens = set(self._tokens(text))
        if not query_tokens:
            return scores
        for label, description in OPERATION_HYPOTHESES.items():
            desc_tokens = set(self._tokens(description))
            exact_overlap = len(query_tokens & desc_tokens) / max(1, len(query_tokens))
            morph_values = []
            for token in query_tokens:
                if len(token) < 4:
                    continue
                best = 0.0
                for desc_token in desc_tokens:
                    if len(desc_token) < 4 or abs(len(token) - len(desc_token)) > max(4, len(token) // 2):
                        continue
                    best = max(best, SequenceMatcher(None, token, desc_token).ratio())
                if best >= 0.55:
                    morph_values.append(best)
            morph_overlap = max(morph_values, default=0.0)
            scores[label] = max(float(scores.get(label, 0.0) or 0.0), min(1.0, 0.8 * exact_overlap), min(1.0, 0.72 * morph_overlap))
        return scores

    def _visual_production_profile(self, text: str, scores: dict[str, dict[str, float]], *, current_visual_input: bool=False) -> dict[str, Any]:
        """Fuse visual task meaning into one production mode.

        The result is derived from competing semantic prototypes and the already
        measured operation/representation/object/goal families. It is not a
        keyword trigger and it does not inspect conversation memory.
        """
        rep = scores.get('representation', {}) if isinstance(scores.get('representation'), dict) else {}
        obj = scores.get('object', {}) if isinstance(scores.get('object'), dict) else {}
        op = scores.get('operation', {}) if isinstance(scores.get('operation'), dict) else {}
        goal = scores.get('goal', {}) if isinstance(scores.get('goal'), dict) else {}
        semantic_scores = {name: float(self.similarity(text, hypothesis).get('score', 0.0) or 0.0) for name, hypothesis in VISUAL_PRODUCTION_HYPOTHESES.items()}
        best_op = max(op.items(), key=lambda item: float(item[1] or 0.0))[0] if op else 'answer'
        visual_rep = max(float(rep.get('image', 0.0) or 0.0), float(rep.get('gallery', 0.0) or 0.0), float(rep.get('diagram', 0.0) or 0.0), float(rep.get('graph', 0.0) or 0.0))
        visual_obj = max(float(obj.get('image', 0.0) or 0.0), float(obj.get('gallery', 0.0) or 0.0), float(obj.get('diagram', 0.0) or 0.0), float(obj.get('graph', 0.0) or 0.0))
        build = max(float(op.get('build', 0.0) or 0.0), float(op.get('create', 0.0) or 0.0), float(op.get('modify', 0.0) or 0.0))
        present = float(op.get('present', 0.0) or 0.0)
        analyze = float(op.get('analyze', 0.0) or 0.0)
        visualize = max(float(goal.get('visualize', 0.0) or 0.0), float(goal.get('transform', 0.0) or 0.0), float(goal.get('present', 0.0) or 0.0))
        composite = dict(semantic_scores)
        composite['image_generation'] += 0.4 * visual_rep + 0.24 * visual_obj + 0.36 * build + 0.1 * visualize
        composite['diagram'] += 0.54 * float(rep.get('diagram', 0.0) or 0.0) + 0.34 * float(obj.get('diagram', 0.0) or 0.0) + 0.34 * build + 0.1 * visualize
        composite['image_present'] += 0.62 * present + 0.28 * visual_obj + 0.2 * float(goal.get('present', 0.0) or 0.0)
        composite['visual_analysis'] += 0.62 * analyze + 0.28 * visual_obj
        if current_visual_input:
            composite['image_generation'] *= 0.1
            composite['diagram'] *= 0.45
            composite['image_present'] += 0.08 * visual_obj
            composite['visual_analysis'] += 0.4
        ordered = sorted(composite.items(), key=lambda item: float(item[1]), reverse=True)
        top_name = ordered[0][0] if ordered else 'none'
        mode = top_name
        top = float(ordered[0][1]) if ordered else 0.0
        second = float(ordered[1][1]) if len(ordered) > 1 else 0.0
        margin = top - second
        gen_sem = float(semantic_scores.get('image_generation', 0.0) or 0.0)
        diag_sem = float(semantic_scores.get('diagram', 0.0) or 0.0)
        build_like = best_op in {'build', 'create', 'modify'}
        if present < 0.14 and best_op not in {'present'}:
            composite['image_present'] *= 0.25
        generation_semantically_clear = gen_sem >= 0.1 and gen_sem >= diag_sem + 0.04
        if current_visual_input:
            if analyze >= max(present, build) and analyze >= 0.16:
                mode = 'visual_analysis'
            elif present >= max(analyze, build) and present >= 0.14:
                mode = 'image_present'
            else:
                mode = 'visual_analysis'
        elif analyze >= max(present, build) and analyze >= 0.18:
            mode = 'visual_analysis'
        elif present >= max(analyze, build) and present >= 0.14:
            mode = 'image_present'
        elif build_like:
            if generation_semantically_clear and composite.get('image_generation', 0.0) >= composite.get('diagram', 0.0) + 0.1:
                mode = 'image_generation'
            else:
                mode = 'diagram'
        elif generation_semantically_clear and visual_rep >= 0.05 and (composite.get('image_generation', 0.0) >= composite.get('image_present', 0.0) + 0.03):
            mode = 'image_generation'
        elif present >= max(analyze, build) and present >= 0.12:
            mode = 'image_present'
        elif analyze >= max(present, build) and analyze >= 0.18:
            mode = 'visual_analysis'
        elif visual_rep >= 0.05:
            mode = 'diagram'
        normalized_operation = best_op
        if mode in {'image_generation', 'diagram'} and best_op not in {'present', 'analyze'}:
            normalized_operation = 'build'
        return {'mode': mode, 'scores': {k: round(float(v), 6) for k, v in composite.items()}, 'semantic_scores': {k: round(float(v), 6) for k, v in semantic_scores.items()}, 'margin': round(float(margin), 6), 'normalized_operation': normalized_operation, 'current_visual_input': bool(current_visual_input), 'source': 'semantic_visual_production_fusion_v2', 'triggering': False}

    @staticmethod
    def _semantic_request_features(text: str, scores: dict[str, dict[str, float]] | None=None) -> dict[str, float | bool]:
        """Collapse semantic families into a task-vector feature set.

        No word/phrase trigger table is used.  The feature set is derived only
        from the already-measured semantic families, so equivalent phrasings
        converge on the same task representation.
        """
        measured = scores if isinstance(scores, dict) else {}
        rep_scores = measured.get('representation', {}) if isinstance(measured.get('representation'), dict) else {}
        op_scores = measured.get('operation', {}) if isinstance(measured.get('operation'), dict) else {}
        obj_scores = measured.get('object', {}) if isinstance(measured.get('object'), dict) else {}
        goal_scores = measured.get('goal', {}) if isinstance(measured.get('goal'), dict) else {}
        dial_scores = measured.get('dialogue', {}) if isinstance(measured.get('dialogue'), dict) else {}

        def best(mapping: dict[str, float], default: str) -> tuple[str, float]:
            if not mapping:
                return (default, 0.0)
            key, value = max(mapping.items(), key=lambda item: float(item[1] or 0.0))
            return (str(key), float(value or 0.0))
        best_rep, best_rep_score = best(rep_scores, 'text')
        best_op, best_op_score = best(op_scores, 'answer')
        best_obj, best_obj_score = best(obj_scores, 'text')
        best_goal, best_goal_score = best(goal_scores, 'understand')
        best_dialogue, best_dialogue_score = best(dial_scores, 'statement')
        structured_rep = best_rep in {'diagram', 'graph', 'formula', 'image', 'gallery', 'table', 'code', 'link', 'audio', 'video', 'file', 'action', 'scene', 'memory', 'visual_context'}
        visual_rep = best_rep in {'diagram', 'image', 'gallery', 'graph'}
        visual_object = best_obj in {'diagram', 'image', 'gallery', 'graph'}
        visual_operation = best_op in {'build', 'modify', 'present'}
        visual_goal = best_goal in {'visualize', 'transform', 'present'}
        memory_query = best_dialogue == 'memory_query'
        visual_schema_scores = measured.get('visual_schema', {}) if isinstance(measured.get('visual_schema'), dict) else {}
        text_schema_score = float(visual_schema_scores.get('text_schema', 0.0) or 0.0)
        ascii_schema_advisory = bool(best_rep == 'text' and text_schema_score >= 0.1 and (best_op in {'answer', 'build', 'present', 'explain', 'list'}))
        followup_dialogue = best_dialogue in {'continuation', 'reformulation', 'correction', 'reference', 'artifact_reference', 'affirmation', 'rejection'}
        self_contained = bool(not followup_dialogue and (not memory_query) and (best_op in {'build', 'modify', 'present', 'compare', 'calculate', 'analyze', 'retrieve', 'list', 'explain'}) and (best_obj != 'text' or structured_rep))
        return {'visual_action': bool(visual_operation and (visual_rep or visual_object)), 'explain_action': bool(best_op == 'explain'), 'geometry_object': bool(best_obj == 'diagram' and best_obj_score >= 0.08), 'construction_context': bool(best_rep == 'diagram' and best_rep_score >= 0.08), 'visual_construction': bool(visual_rep and visual_operation and (visual_object or best_rep_score >= 0.16) and (visual_goal or best_goal_score >= 0.08)), 'ascii_schema_advisory': ascii_schema_advisory, 'ascii_schema_score': text_schema_score, 'self_contained': self_contained, 'memory_query': memory_query, 'semantic_best_representation': best_rep, 'semantic_best_operation': best_op, 'semantic_best_object': best_obj, 'semantic_best_goal': best_goal, 'semantic_best_dialogue': best_dialogue, 'semantic_best_dialogue_score': best_dialogue_score}

    @staticmethod
    def _scene_semantic_text(scene: dict | None) -> str:
        """Build a compact semantic view of the active rendered scene.

        This is local evidence only. It serializes existing scene metadata and
        structured render-block payloads; it does not choose a renderer or call
        a provider.
        """
        if not isinstance(scene, dict):
            return ''
        parts = [scene.get('topic'), scene.get('summary'), scene.get('user_request'), scene.get('current_request'), scene.get('april_answer'), scene.get('answer')]
        for block in scene.get('render_blocks') or []:
            if not isinstance(block, dict):
                continue
            parts.extend([block.get('type'), block.get('artifact_type'), block.get('representation'), block.get('renderer'), block.get('title'), block.get('label'), block.get('content'), block.get('text')])
            payload = block.get('payload')
            if isinstance(payload, dict):
                parts.append(re.sub('\\\\s+', ' ', str(payload))[:1800])
        return re.sub('\\\\s+', ' ', ' '.join((str(x) for x in parts if x not in (None, '', [], {})))).strip()[:5000]

    def _context_scores(self, text, previous_assistant, previous_user, active_topic, active_goal):
        vals = {'previous_assistant': previous_assistant, 'previous_user': previous_user, 'active_topic': active_topic, 'active_goal': active_goal}
        return {k: self.similarity(text, v)['score'] if self.normalize(v) else 0.0 for k, v in vals.items()}

    @classmethod
    def _recent_dialogue_pairs(cls, history: list, limit: int=10) -> list[dict[str, str]]:
        """Build a compact authentic USER→APRIL memory window for follow-ups."""
        pairs: list[dict[str, str]] = []
        pending_user = ''
        for item in history if isinstance(history, list) else []:
            if not isinstance(item, dict):
                continue
            metadata = item.get('metadata') if isinstance(item.get('metadata'), dict) else {}
            if metadata.get('internal_context') or metadata.get('internal_turn'):
                continue
            role = str(item.get('role') or '').lower()
            if role in {'user', 'human'}:
                pending_user = cls.normalize(item.get('content') or item.get('text') or item.get('answer'))
                continue
            if role in {'assistant', 'april', 'bot'}:
                answer = cls.normalize(item.get('content') or item.get('answer') or item.get('text') or item.get('summary'))
                if pending_user and answer:
                    pairs.append({'user': pending_user[:700], 'april': answer[:900], 'result': answer[:1200], 'development_state': 'completed_turn'})
                pending_user = ''
                continue
            user_obj = item.get('user') if isinstance(item.get('user'), dict) else None
            april_obj = item.get('april') if isinstance(item.get('april'), dict) else None
            if user_obj and april_obj:
                user = cls.normalize(user_obj.get('text') or user_obj.get('content') or user_obj.get('answer'))
                answer = cls.normalize(april_obj.get('answer') or april_obj.get('content') or april_obj.get('text'))
                if user and answer:
                    pairs.append({'user': user[:700], 'april': answer[:900]})
        return pairs[-max(1, int(limit)):]

    @classmethod
    def _extract_numeric_results(cls, recent_dialogue_pairs: list[dict[str, str]] | None) -> list[dict[str, Any]]:
        """Extract concrete numeric results from recent authentic assistant answers.

        This is structural evidence, not a topic/phrase trigger. Equality RHS values
        are preferred; when an answer contains exactly one numeric value, that value
        is accepted as the result. The original user/assistant pair is preserved so
        downstream reasoning can cite the source without guessing.
        """
        results: list[dict[str, Any]] = []
        for idx, pair in enumerate(recent_dialogue_pairs or [], start=1):
            if not isinstance(pair, dict):
                continue
            answer = cls.normalize(pair.get('april') or pair.get('assistant'))
            user = cls.normalize(pair.get('user'))
            if not answer:
                continue
            values: list[str] = []
            for match in re.finditer('(?:=|равно|equals)\\s*([-+]?\\d+(?:[.,]\\d+)?)\\b', answer, flags=re.I):
                values.append(match.group(1))
            if not values:
                numbers = re.findall('(?<![\\w.])[-+]?\\d+(?:[.,]\\d+)?(?![\\w.])', answer)
                if len(numbers) == 1:
                    values.append(numbers[0])
            if not values:
                continue
            results.append({'history_index': idx, 'user': user, 'assistant': answer, 'result': values[-1], 'source': 'authentic_dialogue_result'})
        return results[-10:]

    @classmethod
    def _history_task_resolution(cls, current: str, recent_dialogue_pairs: list[dict[str, str]] | None, features: dict[str, Any]) -> dict[str, Any]:
        """Determine whether the current task is incomplete without recent results.

        The decision is based on the semantic operation plus structural operand
        availability. It is intentionally independent from any exact wording such
        as "два последних" so paraphrases behave consistently.
        """
        operation = cls.normalize(features.get('semantic_best_operation')).lower()
        latest_pair = None
        for pair in reversed(recent_dialogue_pairs or []):
            if isinstance(pair, dict) and cls.normalize(pair.get('user')) and cls.normalize(pair.get('april') or pair.get('assistant')):
                latest_pair = pair
                break
        latest_pairs = [latest_pair] if latest_pair else []
        candidate_pairs = list(reversed(recent_dialogue_pairs or []))
        numeric_source_pair = None
        for pair in candidate_pairs:
            if not isinstance(pair, dict):
                continue
            answer_text = cls.normalize(pair.get('april') or pair.get('assistant'))
            if re.search('(?:=|равно|equals)\\s*[-+]?\\d+(?:[.,]\\d+)?\\b', answer_text, flags=re.I) or len(re.findall('(?<![\\w.])[-+]?\\d+(?:[.,]\\d+)?(?![\\w.])', answer_text)) == 1:
                numeric_source_pair = pair
                break
        numeric_results = cls._extract_numeric_results([numeric_source_pair] if numeric_source_pair else latest_pairs)
        prior_numeric_evidence = bool(latest_pair and re.search('(?<![\\w.])[-+]?\\d+(?:[.,]\\d+)?(?![\\w.])', cls.normalize(latest_pair.get('april') or latest_pair.get('assistant'))))
        current_numbers = re.findall('(?<![\\w.])[-+]?\\d+(?:[.,]\\d+)?(?![\\w.])', cls.normalize(current))
        explicit_expression = bool(re.search('[-+]?\\d+(?:[.,]\\d+)?\\s*[+*/-]\\s*[-+]?\\d+(?:[.,]\\d+)?', cls.normalize(current)))
        self_contained_numeric = bool(explicit_expression or len(current_numbers) >= 2)
        required_history_results = 0
        if operation == 'calculate' and (not self_contained_numeric):
            if len(current_numbers) >= 1:
                required_history_results = 1
            elif len(current_numbers) == 0:
                required_history_results = 1
        requires_history = bool(required_history_results > 0 and (len(numeric_results) >= required_history_results or prior_numeric_evidence))
        selected = numeric_results[-required_history_results:] if numeric_results and requires_history else []
        operands = [x['result'] for x in selected]
        confidence = 0.99 if requires_history else 0.0
        return {'required': requires_history, 'operation': operation, 'self_contained_numeric': self_contained_numeric, 'explicit_numeric_count': len(current_numbers), 'available_numeric_results': len(numeric_results), 'selected_results': selected, 'resolved_operands': operands, 'source': 'semantic_operation_plus_structural_history', 'confidence': confidence}

    def _select_three_way_dialogue_relation(self, current: str, recent_pairs: list[dict[str, str]], *, active_topic: str='', previous_assistant: str='', previous_user: str='') -> dict:
        """Select exactly one CONTINUE / RECALL / NEW relation.

        Selection is object/topic anchored, not merely similarity anchored:
          - CONTINUE may only bind to the latest authenticated result.
          - RECALL may bind to an older result when the older result matches the
            current object/topic materially better than the latest result.
          - NEW is used when no prior result clears the relevance floor.

        A selected pair is returned as a concrete memory operand.
        """
        current = self.normalize(current)
        pairs = [x for x in recent_pairs or [] if isinstance(x, dict)]
        if not current or not pairs:
            return {'relation': 'NEW', 'confidence': 0.95 if not pairs else 0.0, 'selected_index': -1, 'selected_pair': {}, 'latest_score': 0.0, 'best_score': 0.0, 'source': 'three_way_dialogue_selector'}
        current_tokens = {token for token in QuantumContextUnderstandingEngine._content_tokens(current) if len(token) >= 4}
        current_content_count = len(current_tokens)
        current_entities = QuantumContextUnderstandingEngine._entities(current)
        current_entity_values = {str(item.get('value') or '').casefold() for item in current_entities if item.get('value')}
        anaphoric_reference = False
        scored: list[dict[str, Any]] = []
        for index, pair in enumerate(pairs):
            user = self.normalize(pair.get('user'))
            answer = self.normalize(pair.get('april') or pair.get('result'))
            combined = ' '.join((x for x in (user, answer) if x))
            if not combined:
                continue
            user_score = float(self.similarity(current, user).get('score', 0.0) or 0.0) if user else 0.0
            answer_score = float(self.similarity(current, answer).get('score', 0.0) or 0.0) if answer else 0.0
            combined_score = float(self.similarity(current, combined).get('score', 0.0) or 0.0)
            pair_tokens = set(QuantumContextUnderstandingEngine._content_tokens(combined))
            shared_tokens = current_tokens & pair_tokens
            pair_entities = QuantumContextUnderstandingEngine._entities(combined)
            pair_entity_values = {str(item.get('value') or '').casefold() for item in pair_entities if item.get('value')}
            shared_entities = current_entity_values & pair_entity_values
            token_overlap = len(shared_tokens) / max(1, len(current_tokens))
            entity_overlap = len(shared_entities) / max(1, len(current_entity_values))
            distinctive = set(current_tokens)
            distinctive_overlap = len(distinctive & pair_tokens) / max(1, len(distinctive))
            recency = 1.0 / (1.0 + 0.08 * (len(pairs) - 1 - index))
            score = 0.44 * user_score + 0.16 * answer_score + 0.12 * combined_score + 0.14 * token_overlap + 0.08 * distinctive_overlap + 0.04 * entity_overlap + 0.02 * recency
            scored.append({'index': index, 'score': float(min(1.0, score)), 'user_score': user_score, 'answer_score': answer_score, 'combined_score': combined_score, 'token_overlap': token_overlap, 'distinctive_overlap': distinctive_overlap, 'entity_overlap': entity_overlap, 'shared_tokens': sorted(shared_tokens)[:20], 'shared_entities': sorted(shared_entities)[:12], 'pair': pair})
        scored.sort(key=lambda item: (item['score'], item['index']), reverse=True)
        if not scored:
            return {'relation': 'NEW', 'confidence': 0.95, 'selected_index': -1, 'selected_pair': {}, 'latest_score': 0.0, 'best_score': 0.0, 'source': 'three_way_dialogue_selector'}
        latest_index = len(pairs) - 1
        latest = next((item for item in scored if item['index'] == latest_index), None)
        best = scored[0]
        latest_score = float(latest['score'] if latest else 0.0)
        CONTINUE_FLOOR = 0.055
        RECALL_FLOOR = 0.085
        RECALL_MARGIN = 0.045
        if latest is not None:
            latest_task_anchor = 0.7 * latest['user_score'] + 0.2 * latest['distinctive_overlap'] + 0.1 * latest['token_overlap']
        else:
            latest_task_anchor = 0.0
        best_task_anchor = 0.7 * best['user_score'] + 0.2 * best['distinctive_overlap'] + 0.1 * best['token_overlap']
        relation_affinity = max(float(latest.get('combined_score', 0.0) if latest else 0.0), float(latest.get('answer_score', 0.0) if latest else 0.0), float(latest.get('user_score', 0.0) if latest else 0.0))
        semantic_followup = max(relation_affinity, float(latest['token_overlap'] if latest else 0.0), float(latest['distinctive_overlap'] if latest else 0.0))
        reference_strength = max(float(best.get('combined_score', 0.0) or 0.0) if best else 0.0, float(best.get('entity_overlap', 0.0) or 0.0) if best else 0.0)
        continuation_strength = semantic_followup
        older_better = bool(best['index'] < latest_index and best['score'] >= RECALL_FLOOR and (best['score'] >= latest_score + RECALL_MARGIN) and (best_task_anchor >= max(latest_task_anchor + 0.04, 0.1)) and (reference_strength >= 0.06 or best['distinctive_overlap'] >= 0.25))
        latest_semantic_underspecification = bool(latest is not None and current_content_count <= 2 and (not current_entities) and (float(latest.get('answer_score', 0.0) or 0.0) >= 0.05 or float(latest.get('combined_score', 0.0) or 0.0) >= 0.05 or float(latest.get('token_overlap', 0.0) or 0.0) > 0.0))
        prior_numeric_evidence = any((bool(re.search('(?<![\\w.])[-+]?\\d+(?:[.,]\\d+)?(?![\\w.])', str(pair.get('assistant') or pair.get('april') or ''))) for pair in pairs[-3:] if isinstance(pair, dict)))
        current_numeric_dependency = bool(latest is not None and prior_numeric_evidence and (current_content_count <= 5) and (len(re.findall('(?<![\\w.])[-+]?\\d+(?:[.,]\\d+)?(?![\\w.])', current)) <= 1) and (not current_entities) and (float(latest.get('answer_score', 0.0) or 0.0) >= 0.04))
        latest_is_material = bool(latest is not None and latest_score >= CONTINUE_FLOOR and (not explicit_arithmetic_expression or previous_pending_input or grammatical_reference) and (latest['distinctive_overlap'] >= 0.12 or latest['token_overlap'] >= 0.2 or latest['user_score'] >= 0.18 or (continuation_strength >= 0.1) or latest_semantic_underspecification or current_numeric_dependency))
        if older_better:
            relation = 'RECALL'
            selected = best
        elif latest_is_material and (continuation_strength >= 0.1 or reference_strength < 0.12):
            relation = 'CONTINUE'
            selected = latest
        elif best['score'] >= RECALL_FLOOR and reference_strength >= 0.18 and (best['index'] < latest_index):
            relation = 'RECALL'
            selected = best
        else:
            relation = 'NEW'
            selected = {}
        confidence = best['score'] if relation != 'NEW' else max(0.0, min(1.0, 1.0 - best['score']))
        selected_pair = dict(selected.get('pair') or {}) if selected else {}
        return {'relation': relation, 'confidence': round(float(confidence), 6), 'selected_index': int(selected.get('index', -1)) if selected else -1, 'selected_pair': selected_pair, 'latest_score': round(latest_score, 6), 'best_score': round(float(best['score']), 6), 'dialogue_followup_evidence': round(float(max(continuation_strength, reference_strength)), 6), 'latest_task_anchor': round(float(latest_task_anchor), 6), 'best_task_anchor': round(float(best_task_anchor), 6), 'anaphoric_reference': False, 'reference_strength': round(float(reference_strength), 6), 'continuation_strength': round(float(continuation_strength), 6), 'older_pair_selected': bool(older_better), 'candidates': [{'index': int(item['index']), 'score': round(float(item['score']), 6), 'user_score': round(float(item['user_score']), 6), 'answer_score': round(float(item['answer_score']), 6), 'distinctive_overlap': round(float(item['distinctive_overlap']), 6), 'token_overlap': round(float(item['token_overlap']), 6)} for item in scored[:10]], 'source': 'semantic_dialogue_relation_engine_v3_no_triggers'}

    def _dialogue_relation_engine(self, text: str, *, previous_assistant: str='', previous_user: str='', active_topic: str='', active_goal: str='', previous_scene: dict | None=None, recent_dialogue_pairs: list[dict[str, str]] | None=None) -> dict:
        """Resolve topic continuity and request dependency from semantic evidence.

        Topic similarity and request dependency are separate dimensions.  The
        dialogue classifier decides the discourse act; current-task semantic
        completeness prevents topical similarity from becoming a false
        continuation.  No lexical trigger map is used.
        """
        current = self.normalize(text)
        prev_a = self.normalize(previous_assistant)
        prev_u = self.normalize(previous_user)
        topic = self.normalize(active_topic)
        goal = self.normalize(active_goal)
        scene = previous_scene if isinstance(previous_scene, dict) else {}
        scene_topic = self.normalize(scene.get('topic'))
        sims = {'previous_assistant': self.similarity(current, prev_a)['score'] if prev_a else 0.0, 'previous_user': self.similarity(current, prev_u)['score'] if prev_u else 0.0, 'active_topic': self.similarity(current, topic)['score'] if topic else 0.0, 'active_goal': self.similarity(current, goal)['score'] if goal else 0.0, 'previous_scene_topic': self.similarity(current, scene_topic)['score'] if scene_topic else 0.0}
        dialogue_scores = self._family_scores(current, 'dialogue', SEMANTIC_TURN_PROTOTYPES)
        dialogue_rank = sorted(dialogue_scores.items(), key=lambda item: float(item[1] or 0.0), reverse=True)
        dialogue_best = dialogue_rank[0][0] if dialogue_rank else 'statement'
        dialogue_best_score = float(dialogue_rank[0][1]) if dialogue_rank else 0.0
        semantic_measurements = {'representation': self._family_scores(current, 'representation', REPRESENTATION_HYPOTHESES), 'operation': self._operation_family_scores(current), 'object': self._family_scores(current, 'object', OBJECT_HYPOTHESES), 'goal': self._family_scores(current, 'goal', GOAL_HYPOTHESES), 'dialogue': dialogue_scores}
        features = self._semantic_request_features(current, semantic_measurements)
        operation_scores = semantic_measurements['operation']
        best_operation = str(features.get('semantic_best_operation') or '').lower()
        calculate_score = float(operation_scores.get('calculate', 0.0) or 0.0)
        best_operation_score = float(operation_scores.get(best_operation, 0.0) or 0.0)
        current_number_count = len(re.findall('(?<![\\w.])[-+]?\\d+(?:[.,]\\d+)?(?![\\w.])', current))
        if current_number_count >= 1 and current_number_count <= 1 and (calculate_score >= 0.55) and (calculate_score + 0.1 >= best_operation_score):
            features['semantic_best_operation'] = 'calculate'
            features['semantic_best_operation_score'] = calculate_score
        recent_pairs = recent_dialogue_pairs if isinstance(recent_dialogue_pairs, list) else []
        three_way = self._select_three_way_dialogue_relation(current, recent_pairs, active_topic=topic, previous_assistant=prev_a, previous_user=prev_u)
        history_task = self._history_task_resolution(current, recent_pairs, features)
        if history_task.get('required') and recent_pairs:
            three_way = {**dict(three_way), 'relation': 'CONTINUE', 'selected_index': len(recent_pairs) - 1, 'selected_pair': dict(recent_pairs[-1]), 'source': 'semantic_structural_task_dependency'}
        dialogue_followup = max((float(value or 0.0) for label, value in dialogue_scores.items() if label in {'continuation', 'reformulation', 'correction', 'reference', 'artifact_reference', 'affirmation', 'rejection'}), default=0.0)
        reference_evidence = max(float(dialogue_scores.get('reference', 0.0) or 0.0), float(dialogue_scores.get('artifact_reference', 0.0) or 0.0))
        artifact_reference_evidence = float(dialogue_scores.get('artifact_reference', 0.0) or 0.0)
        memory_evidence = float(dialogue_scores.get('memory_query', 0.0) or 0.0)
        continuation_evidence = max(float(dialogue_scores.get('continuation', 0.0) or 0.0), float(dialogue_scores.get('reformulation', 0.0) or 0.0), float(dialogue_scores.get('correction', 0.0) or 0.0))
        history_available = bool(recent_pairs or prev_a or prev_u)
        topic_affinity = max(sims['active_topic'], sims['previous_scene_topic'], sims['previous_user'] * 0.92)
        answer_affinity = sims['previous_assistant']
        request_affinity = sims['previous_user']
        goal_affinity = sims['active_goal']
        relation_strength = max(topic_affinity, answer_affinity, request_affinity, goal_affinity)
        has_context = bool(prev_a or prev_u or topic or scene_topic)
        current_self_contained = bool(features.get('self_contained'))
        explicit_numeric_expression = bool(re.search('(?<!\\w)[+-]?\\d+(?:[.,]\\d+)?\\s*[+*\\-/]\\s*[+-]?\\d+(?:[.,]\\d+)?(?!\\w)', current))
        contextual_operation = str(features.get('semantic_best_operation') or '').lower() in {'calculate', 'analyze', 'explain', 'list', 'compare', 'modify', 'present'}
        semantic_followup_evidence = max(dialogue_followup, reference_evidence, memory_evidence, continuation_evidence)
        history_dependent_task = bool(history_task.get('required') or (history_available and (not current_self_contained) and (semantic_followup_evidence >= 0.08) and (not explicit_numeric_expression)))
        semantic_reference = bool(dialogue_best == 'reference' and has_context and (not current_self_contained))
        semantic_memory_query = bool(dialogue_best == 'memory_query' and has_context)
        if not has_context:
            relation = 'NEW_TOPIC'
            topic_relation = 'NEW_TOPIC'
        elif semantic_memory_query:
            relation = 'MEMORY_QUERY'
            topic_relation = 'SAME_TOPIC'
        elif semantic_reference:
            relation = 'CONTINUE_TOPIC'
            topic_relation = 'SAME_TOPIC'
        elif dialogue_best in {'continuation', 'reformulation', 'correction'} and (not current_self_contained):
            relation = 'CONTINUE_TOPIC'
            topic_relation = 'SAME_TOPIC'
        elif history_task.get('required'):
            relation = 'CONTINUE_TOPIC'
            topic_relation = 'SAME_TOPIC'
        elif history_dependent_task and semantic_followup_evidence >= 0.08:
            relation = 'CONTINUE_TOPIC'
            topic_relation = 'SAME_TOPIC'
        elif current_self_contained:
            relation = 'SAME_TOPIC' if topic_affinity >= 0.18 or request_affinity >= 0.42 else 'INDEPENDENT'
            topic_relation = relation
        elif dialogue_best in {'affirmation', 'rejection'} and has_context:
            relation = 'SAME_TOPIC'
            topic_relation = 'SAME_TOPIC'
        elif relation_strength >= 0.48:
            relation = 'SAME_TOPIC'
            topic_relation = 'SAME_TOPIC'
        else:
            relation = 'NEW_TOPIC'
            topic_relation = 'NEW_TOPIC'
        canonical_three_way = str(three_way.get('relation') or 'NEW').upper()
        selected_pair = three_way.get('selected_pair') if isinstance(three_way.get('selected_pair'), dict) else {}
        latest_pair_for_boundary = recent_pairs[-1] if recent_pairs else {}
        latest_pair_text = ' '.join((str(latest_pair_for_boundary.get(key) or '') for key in ('user', 'assistant', 'april'))) if isinstance(latest_pair_for_boundary, dict) else ''
        current_content = set(QuantumContextUnderstandingEngine._content_tokens(current))
        latest_content = set(QuantumContextUnderstandingEngine._content_tokens(latest_pair_text))
        content_relation = len(current_content & latest_content) / max(1, len(current_content)) if current_content else 0.0
        previous_signature = {}
        latest_user_for_signature = str(latest_pair_for_boundary.get('user') or '') if isinstance(latest_pair_for_boundary, dict) else ''
        if latest_user_for_signature:
            try:
                previous_signature = self.measure(latest_user_for_signature) or {}
            except Exception:
                previous_signature = {}
        current_signature = {'representation': str(features.get('semantic_best_representation') or '').lower(), 'operation': str(features.get('semantic_best_operation') or '').lower(), 'object': str(features.get('semantic_best_object') or '').lower(), 'goal': str(features.get('semantic_best_goal') or '').lower()}
        previous_signature = {'representation': str(previous_signature.get('best_representation') or '').lower(), 'operation': str(previous_signature.get('best_operation') or '').lower(), 'object': str(previous_signature.get('best_object') or '').lower(), 'goal': str(previous_signature.get('best_goal') or '').lower()}
        signature_matches = sum((1 for key in ('representation', 'operation', 'object', 'goal') if current_signature.get(key) and current_signature.get(key) == previous_signature.get(key)))
        core_signature_matches = sum((1 for key in ('representation', 'operation', 'object') if current_signature.get(key) and current_signature.get(key) == previous_signature.get(key)))
        signature_continuity = signature_matches / 4.0
        semantic_new_topic_score = float(dialogue_scores.get('new_topic', 0.0) or 0.0)
        semantic_topic_boundary = bool(recent_pairs and current_self_contained and (not history_task.get('required')) and (semantic_new_topic_score >= 0.35 or core_signature_matches == 0) and (content_relation <= 0.25) and (core_signature_matches == 0) and (not semantic_reference) and (not semantic_memory_query))
        if semantic_topic_boundary:
            canonical_three_way = 'NEW'
            selected_pair = {}
        if history_task.get('required') and recent_pairs:
            canonical_three_way = 'CONTINUE'
            selected_pair = dict(recent_pairs[-1])
        if canonical_three_way == 'CONTINUE':
            relation = 'CONTINUE_TOPIC'
            topic_relation = 'SAME_TOPIC'
            subtype = 'DEVELOPMENT'
        elif canonical_three_way == 'RECALL':
            relation = 'RECALL'
            topic_relation = 'RECALL'
            subtype = 'RECALL'
        else:
            relation = 'NEW_TOPIC'
            topic_relation = 'NEW_TOPIC'
            subtype = 'NEW'
        scene_reference_similarity = 0.0
        visual_reference_candidate = False
        scene_has_rendered_artifact = bool(scene and any((isinstance(block, dict) and _clean_representation(block.get('type') or block.get('artifact_type') or block.get('representation')) in {'diagram', 'graph', 'image', 'gallery', 'table', 'formula', 'code', 'link', 'audio', 'video', 'file'} for block in scene.get('render_blocks') or [])))
        if scene_has_rendered_artifact and (not current_self_contained or artifact_reference_evidence >= 0.06):
            scene_text = self._scene_semantic_text(scene)
            if scene_text:
                scene_similarity_result = self.similarity(current, scene_text)
                scene_reference_similarity = float(scene_similarity_result.get('score', 0.0) or 0.0)
            semantic_best_rep = str(features.get('semantic_best_representation') or '').lower()
            semantic_best_obj = str(features.get('semantic_best_object') or '').lower()
            semantic_best_op = str(features.get('semantic_best_operation') or '').lower()
            visual_task = semantic_best_rep in {'diagram', 'graph', 'image', 'gallery', 'table', 'formula'} or semantic_best_obj in {'diagram', 'graph', 'image', 'gallery', 'table', 'formula'} or features.get('visual_action') or features.get('geometry_object')
            artifact_question = artifact_reference_evidence >= 0.06
            answer_about_artifact = semantic_best_op in {'answer', 'list', 'analyze', 'explain', 'compare', 'present', 'build'}
            visual_reference_candidate = bool(answer_about_artifact and visual_task and artifact_question and (scene_reference_similarity >= 0.16))
        if visual_reference_candidate and canonical_three_way == 'CONTINUE':
            relation = 'ARTIFACT_REFERENCE'
            topic_relation = 'SAME_TOPIC'
            subtype = 'REFERENCE_OR_DEVELOPMENT'
            semantic_reference = True
        elif relation == 'MEMORY_QUERY':
            subtype = 'MEMORY_QUERY'
        elif relation == 'CONTINUE_TOPIC':
            subtype = 'REFERENCE_OR_DEVELOPMENT' if semantic_reference else 'DEVELOPMENT'
        elif relation == 'SAME_TOPIC':
            subtype = 'NEW_TASK_SAME_TOPIC'
        else:
            subtype = relation
        previous_text = ' '.join((x for x in (prev_a, prev_u, topic) if x))
        previous_tokens = {t for t in self._tokens(previous_text) if len(t) >= 3}
        current_tokens = [t for t in self._tokens(current) if len(t) >= 3]
        shared_tokens, new_tokens = ([], [])
        for token in current_tokens:
            target = shared_tokens if token in previous_tokens else new_tokens
            if token not in target:
                target.append(token)
        previous_render_types = list(scene.get('render_block_types') or [])
        previous_block_ids = [str(x.get('block_id')) for x in scene.get('render_blocks') or [] if isinstance(x, dict) and x.get('block_id')]
        dependency_score = max(0.98 if history_task.get('required') else 0.0, 0.92 if semantic_reference else 0.0, 0.88 if semantic_memory_query and (not current_self_contained) else 0.0, continuation_evidence if not current_self_contained else 0.0, 0.3 * answer_affinity + 0.24 * topic_affinity + 0.2 * dialogue_followup)
        if current_self_contained and relation not in {'MEMORY_QUERY', 'CONTINUE_TOPIC'}:
            dependency_score = 0.0
        continuation_score = dependency_score if relation in {'CONTINUE_TOPIC', 'MEMORY_QUERY'} else 0.0
        independent_score = 1.0 - dependency_score
        request_dependency = 'continuation' if canonical_three_way == 'CONTINUE' else 'recall' if canonical_three_way == 'RECALL' else 'independent'
        if canonical_three_way == 'RECALL':
            continuation_score = 0.0
            independent_score = 0.0
        elif canonical_three_way == 'CONTINUE':
            continuation_score = dependency_score
            independent_score = 1.0 - dependency_score
        else:
            continuation_score = 0.0
            independent_score = 1.0
        return {'relation': relation, 'topic_relation': topic_relation, 'request_relation': 'ARTIFACT_REFERENCE' if semantic_reference else 'MEMORY_QUERY' if semantic_memory_query else relation, 'request_dependency': request_dependency, 'request_dependency_score': float(max(0.0, min(1.0, dependency_score))), 'current_request_complete': current_self_contained, 'history_dependent_task': history_dependent_task, 'history_window_size': len(recent_pairs), 'history_task_context': history_task, 'continuation_score': float(max(0.0, min(1.0, continuation_score))), 'independent_score': float(max(0.0, min(1.0, independent_score))), 'relation_strength': float(max(0.0, min(1.0, relation_strength))), 'three_way_relation': canonical_three_way, 'three_way_confidence': float(three_way.get('confidence', 0.0) or 0.0), 'selected_memory_index': int(three_way.get('selected_index', -1) or -1), 'selected_memory_operand': selected_pair, 'subtype': subtype, 'scores': {**sims, 'dialogue_followup': dialogue_followup, 'reference_evidence': reference_evidence, 'memory_query_evidence': memory_evidence, 'structural_followup': dependency_score, 'semantic_signature_continuity': signature_continuity, 'semantic_core_signature_matches': core_signature_matches, 'semantic_topic_boundary': semantic_topic_boundary}, 'active_topic': topic, 'active_goal': goal, 'previous_user_turn': prev_u, 'previous_april_turn': prev_a, 'shared_tokens': shared_tokens[:40], 'new_tokens': new_tokens[:40], 'delta_mode': 'extend' if relation in {'CONTINUE_TOPIC', 'MEMORY_QUERY'} else 'start', 'avoid_repeat': True, 'reuse_existing_scene': relation in {'CONTINUE_TOPIC', 'MEMORY_QUERY'} and bool(scene.get('scene_id')), 'previous_scene_id': scene.get('scene_id') if relation in {'CONTINUE_TOPIC', 'MEMORY_QUERY'} else '', 'previous_render_types': previous_render_types, 'previous_block_ids': previous_block_ids, 'explicit_reference': semantic_reference, 'anaphoric': semantic_reference, 'source': 'quantum_dialogue_vector_v6_semantic', 'decision_owner': DECISION_OWNER, 'trigger_independent': False, 'semantic_dialogue_label': dialogue_best, 'semantic_dialogue_confidence': dialogue_best_score, 'visual_reference_candidate': bool(visual_reference_candidate), 'visual_scene_similarity': float(max(0.0, min(1.0, scene_reference_similarity))), 'artifact_reference_evidence': bool(visual_reference_candidate), 'artifact_reference_semantic_score': float(max(0.0, min(1.0, artifact_reference_evidence)))}

    def _linguistic(self, text):
        tokens = self._tokens(text)
        return {'language': None, 'tokens': tokens, 'lemmas': tokens, 'pos': [], 'dependencies': [], 'entities': [], 'sentences': [text] if text else [], 'source': 'quantum_matrix', 'engine': 'quantum_interpretation_engine_v3'}

    def similarity(self, text_a, text_b):
        left, right = (self.normalize(text_a), self.normalize(text_b))
        if not left or not right:
            return {'score': 0.0, 'source': 'unresolved_semantic_similarity', 'measured': False, 'cached': False}
        if self._semantic_encoder is not None:
            try:
                v = self._semantic_encoder.encode([left, right], normalize_embeddings=True)
                return {'score': max(0.0, min(1.0, float(v[0] @ v[1]))), 'source': 'sentence_transformer', 'measured': True, 'cached': False}
            except Exception:
                pass
        if self._vectorizer is not None and cosine_similarity is not None:
            try:
                v = self._vectorizer.transform([left, right])
                return {'score': max(0.0, min(1.0, float(cosine_similarity(v[0], v[1])[0][0]))), 'source': 'quantum_matrix_tfidf', 'measured': True, 'cached': False}
            except Exception:
                pass
        return {'score': 0.0, 'source': 'unresolved_semantic_similarity', 'measured': False, 'cached': False}

    def similarities(self, text, candidates):
        return {self.normalize(c): self.similarity(text, c)['score'] for c in candidates if self.normalize(c)}

    def prewarm_static(self, candidates):
        return len({self.normalize(x) for x in candidates if self.normalize(x)})

    def _history(self, history):
        last_a = last_u = ''
        reply_to = None
        for item in reversed(history if isinstance(history, list) else []):
            if not isinstance(item, dict):
                continue
            metadata = item.get('metadata') if isinstance(item.get('metadata'), dict) else {}
            content = self.normalize(item.get('content') or item.get('text') or item.get('answer') or '')
            if metadata.get('internal_context') or metadata.get('internal_turn') or metadata.get('source') in {'internal_visual', 'internal_visual_analysis', 'passive_visual_helper'} or content.startswith('VISUAL_ANALYSIS:'):
                continue
            role = str(item.get('role') or '').lower()
            if not last_a:
                obj = item.get('april') if isinstance(item.get('april'), dict) else item
                if role in {'assistant', 'april', 'bot'} or isinstance(item.get('april'), dict):
                    last_a = self.normalize(obj.get('answer') or obj.get('content') or obj.get('summary'))
                    reply_to = item.get('turn_id')
            if not last_u:
                obj = item.get('user') if isinstance(item.get('user'), dict) else item
                if role in {'user', 'human'} or isinstance(item.get('user'), dict):
                    last_u = self.normalize(obj.get('text') or obj.get('content') or obj.get('answer'))
            if last_a and last_u:
                break
        return (last_a, last_u, reply_to)

    def measure(self, text, *, previous_assistant='', previous_user='', active_topic='', active_goal='', modalities=None):
        text = self.normalize(text)
        key = (text, self.normalize(previous_assistant), self.normalize(previous_user), self.normalize(active_topic), self.normalize(active_goal), tuple(sorted((modalities or {}).keys())))
        with self._lock:
            if key in self._cache:
                return self._cache[key]
        focus_text = self._semantic_focus_text(text)
        scores = {'dialogue': self._family_scores(text, 'dialogue', SEMANTIC_TURN_PROTOTYPES), 'representation': self._family_scores(focus_text or text, 'representation', REPRESENTATION_HYPOTHESES), 'domain': self._family_scores(text, 'domain', DOMAIN_HYPOTHESES), 'capability': self._family_scores(text, 'capability', CAPABILITY_HYPOTHESES), 'operation': self._operation_family_scores(text), 'object': self._family_scores(focus_text or text, 'object', OBJECT_HYPOTHESES), 'goal': self._family_scores(text, 'goal', GOAL_HYPOTHESES), 'visual_schema': self._family_scores(text, 'visual_schema', VISUAL_SCHEMA_HYPOTHESES)}
        visual_production = self._visual_production_profile(text, scores, current_visual_input=bool((modalities or {}).get('current_visual_input')))
        interrogative = bool('?' in text or re.match('^\\s*(что|кто|как|какой|какая|какое|какие|сколько|почему|зачем|где|когда|куда|откуда|на\\s+что)\\b', text.lower()))
        if interrogative:
            question_words = re.findall('[А-Яа-яЁёЇїІіЄєҐґ]+', text.lower())[:3]
            explanatory_form = bool(question_words and question_words[0] in {'почему', 'зачем', 'как'})
            if explanatory_form:
                scores['operation']['explain'] = max(float(scores['operation'].get('explain', 0.0) or 0.0), 0.52)
                scores['operation']['analyze'] = max(float(scores['operation'].get('analyze', 0.0) or 0.0), 0.34)
            else:
                scores['operation']['answer'] = max(float(scores['operation'].get('answer', 0.0) or 0.0), 0.52)
                scores['operation']['analyze'] = max(float(scores['operation'].get('analyze', 0.0) or 0.0), 0.3)
        for label in self._negated_representation_labels(text):
            if label in scores['representation']:
                scores['representation'][label] *= 0.05
            if label in scores['object']:
                scores['object'][label] *= 0.05
        request_features = self._semantic_request_features(text, scores)
        if request_features['visual_construction'] and (not self._negated_representation_labels(text)):
            scores['representation']['diagram'] = max(scores['representation'].get('diagram', 0.0), float(scores['representation'].get('diagram', 0.0) or 0.0))
            scores['operation']['build'] = max(scores['operation'].get('build', 0.0), float(scores['operation'].get('present', 0.0) or 0.0))
            scores['goal']['visualize'] = max(scores['goal'].get('visualize', 0.0), float(scores['goal'].get('transform', 0.0) or 0.0))
            request_features = self._semantic_request_features(text, scores)
        ctx = self._context_scores(text, previous_assistant, previous_user, active_topic, active_goal)

        def rank(d):
            return sorted(d.items(), key=lambda x: x[1], reverse=True)
        rep = rank(scores['representation'])
        ops = rank(scores['operation'])
        objs = rank(scores['object'])
        goals = rank(scores['goal'])
        dial = rank(scores['dialogue'])
        profile = {'dialogue_scores': scores['dialogue'], 'dialogue_best': dial[0][0] if dial else 'independent', 'dialogue_confidence': float(dial[0][1]) if dial else 0.0, 'dialogue_margin': float(dial[0][1] - dial[1][1]) if len(dial) > 1 else 0.0, 'representation_scores': scores['representation'], 'domain_scores': scores['domain'], 'capability_scores': scores['capability'], 'operation_scores': scores['operation'], 'object_scores': scores['object'], 'goal_scores': scores['goal'], 'visual_schema_scores': scores['visual_schema'], 'request_features': request_features, 'visual_production': visual_production, 'visual_production_mode': visual_production.get('mode', 'none'), 'image_generation_request': visual_production.get('mode') == 'image_generation', 'lightweight_visual_request': visual_production.get('mode') == 'diagram', 'complex_image_generation': visual_production.get('mode') == 'image_generation', 'context_scores': ctx, 'best_representation': rep[0][0] if rep else 'text', 'best_representation_score': float(rep[0][1]) if rep else 0.0, 'representation_margin': float(rep[0][1] - rep[1][1]) if len(rep) > 1 else float(rep[0][1]) if rep else 0.0, 'best_operation': ops[0][0] if ops else 'answer', 'best_object': objs[0][0] if objs else 'text', 'best_goal': goals[0][0] if goals else 'understand', 'source': 'quantum_matrix_semantic_measurement_v3', 'identity_request': bool(dial and dial[0][0] == 'identity' and (dial[0][1] >= 0.12)), 'fast_social': bool(dial and dial[0][0] in {'identity', 'greeting'} and (dial[0][1] >= 0.18))}
        with self._lock:
            self._cache[key] = profile
            if len(self._cache) > self._cache_limit:
                self._cache.pop(next(iter(self._cache)))
        return profile

    def _resolve_production(self, text, profile, explicit):
        explicit_values = [_clean_representation(x) for x in explicit or []]
        explicit_values = [x for x in explicit_values if x]
        if len(explicit_values) == 1:
            return (explicit_values[0], 'explicit_current_request', True)
        rep = dict(profile.get('representation_scores') or {})
        obj = dict(profile.get('object_scores') or {})
        op = dict(profile.get('operation_scores') or {})
        goal = dict(profile.get('goal_scores') or {})
        features = dict(profile.get('request_features') or {})
        visual_mode = str(profile.get('visual_production_mode') or 'none').lower()

        def rank(items):
            return sorted(items.items(), key=lambda x: float(x[1]), reverse=True)
        rep_rank = rank(rep)
        obj_rank = rank(obj)
        op_rank = rank(op)
        goal_rank = rank(goal)
        best_rep = rep_rank[0][0] if rep_rank else 'text'
        best_rep_score = float(rep.get(best_rep, 0.0))
        second_rep_score = float(rep_rank[1][1]) if len(rep_rank) > 1 else 0.0
        best_obj = obj_rank[0][0] if obj_rank else 'text'
        best_obj_score = float(obj.get(best_obj, 0.0))
        best_op = op_rank[0][0] if op_rank else 'answer'
        best_op_score = float(op.get(best_op, 0.0))
        best_goal = goal_rank[0][0] if goal_rank else 'understand'
        best_goal_score = float(goal.get(best_goal, 0.0))
        if visual_mode == 'image_generation':
            return ('image', 'semantic_visual_image_generation', True)
        if visual_mode == 'diagram' and best_op in {'build', 'create', 'modify', 'present'}:
            return ('diagram', 'semantic_light_visual_construction', True)
        if visual_mode == 'image_present' and best_op in {'present', 'build', 'modify', 'retrieve', 'list'}:
            return ('image', 'semantic_existing_image_presentation', True)
        visual_schema_scores = dict(profile.get('visual_schema_scores') or {})
        text_schema_score = float(visual_schema_scores.get('text_schema', 0.0) or 0.0)
        diagram_score = float(visual_schema_scores.get('diagram', 0.0) or 0.0)
        text_schema_format_intent = bool(text_schema_score >= 0.15 and text_schema_score >= diagram_score + 0.04 and (best_op in {'build', 'present', 'answer', 'explain', 'list', 'modify'}))
        if text_schema_format_intent and best_rep in {'text', 'diagram'} and (best_obj in {'text', 'diagram'}):
            return ('text', 'semantic_text_schema_format_advisory', True)
        if best_op == 'calculate':
            structured_calc = []
            for label in ('formula', 'graph', 'table', 'diagram', 'image', 'gallery'):
                rep_score = float(rep.get(label, 0.0) or 0.0)
                object_score = float(obj.get(label, 0.0) or 0.0)
                if rep_score >= 0.22 and (object_score >= 0.08 or rep_score >= 0.3):
                    structured_calc.append(label)
            if not structured_calc:
                return ('text', 'semantic_calculation_answer', True)
        compatible_ops = {'graph': {'build', 'modify', 'present', 'calculate', 'analyze', 'list', 'explain'}, 'diagram': {'build', 'modify', 'present', 'explain'}, 'table': {'build', 'modify', 'present', 'compare', 'list', 'explain'}, 'formula': {'build', 'modify', 'present', 'calculate', 'explain', 'answer'}, 'link': {'retrieve', 'present', 'answer', 'explain', 'list'}, 'code': {'build', 'modify', 'present', 'explain', 'list'}, 'image': {'build', 'modify', 'present'}, 'gallery': {'build', 'present'}, 'file': {'retrieve', 'present'}, 'audio': {'build', 'present'}, 'video': {'build', 'present'}, 'action': {'build', 'modify', 'present'}, 'scene': {'build', 'modify', 'present'}, 'memory': {'retrieve', 'answer', 'present'}, 'visual_context': {'answer', 'analyze', 'explain'}}
        aligned = best_op in compatible_ops.get(best_rep, set())
        if features.get('visual_construction') and (not self._negated_representation_labels(text)):
            return ('diagram', 'semantic_visual_construction', True)
        if best_rep != 'text' and aligned:
            rep_margin = best_rep_score - second_rep_score
            object_agreement = best_obj == best_rep and best_obj_score >= 0.05
            representation_clear = best_rep_score >= 0.1 and (rep_margin >= 0.015 or best_rep_score >= 0.22)
            if representation_clear and (object_agreement or best_rep_score >= 0.16):
                return (best_rep, 'task_object_goal_resolution', True)
            production_ops = {'build', 'modify', 'present'}
            production_signal = max((float(op.get(name, 0.0) or 0.0) for name in production_ops))
            production_goal = max((float(goal.get(name, 0.0) or 0.0) for name in {'visualize', 'transform', 'present', 'organize'}))
            object_alignment = best_obj == best_rep and best_obj_score >= 0.1
            representation_dominance = best_rep_score >= max(0.09, float(rep.get('text', 0.0) or 0.0) + 0.025)
            structured_task = best_rep != 'text' and object_alignment and representation_dominance and (production_signal >= 0.055 or (aligned and best_op_score >= 0.08)) and (production_goal >= 0.035 or best_rep_score >= 0.14)
            if structured_task:
                return (best_rep, 'semantic_task_vector_resolution', True)
            if aligned and best_rep_score >= 0.1 and (best_op_score >= 0.08):
                return (best_rep, 'operation_representation_resolution', True)
        return ('text', 'unresolved', False)

    def dialogue(self, text, previous_assistant='', previous_user='', active_goal='', active_topic='', previous_scene=None, recent_dialogue_pairs=None):
        p = self.measure(text, previous_assistant=previous_assistant, previous_user=previous_user, active_goal=active_goal, active_topic=active_topic)
        vector = self._dialogue_relation_engine(text, previous_assistant=previous_assistant, previous_user=previous_user, active_goal=active_goal, active_topic=active_topic, previous_scene=previous_scene, recent_dialogue_pairs=recent_dialogue_pairs)
        d = p['dialogue_scores']
        return {'dialogue': {'label': p['dialogue_best'], 'confidence': p['dialogue_confidence'], 'continuation_score': vector['continuation_score'], 'reference_score': max(vector['scores'].get('previous_assistant', 0.0), vector['scores'].get('previous_scene_topic', 0.0)), 'topic_score': max(vector['scores'].get('active_topic', 0.0), vector['scores'].get('previous_scene_topic', 0.0)), 'goal_score': vector['scores'].get('active_goal', 0.0)}, 'linguistic': self._linguistic(text), 'continuation': vector['relation'] == 'CONTINUE_TOPIC', 'reference_to_previous': bool(vector.get('request_relation') == 'ARTIFACT_REFERENCE'), 'dialogue_relation': vector, 'identity_request': p['identity_request'], 'nli': {'labels': list(d), 'scores': list(d.values()), 'source': 'quantum_matrix'}, 'decision_owner': DECISION_OWNER, 'evidence_only': True, 'engine': 'quantum_dialogue_vector_engine_v4'}

    def representations(self, text, context=''):
        p = self.measure(text, active_topic=context)
        return {'nli': {'labels': list(p['representation_scores']), 'scores': list(p['representation_scores'].values()), 'source': 'quantum_matrix'}, 'measurements': [{'type': k, 'score': float(v), 'source': 'quantum_matrix'} for k, v in sorted(p['representation_scores'].items(), key=lambda x: x[1], reverse=True)], 'context_similarity': {'score': p['context_scores'].get('active_topic', 0.0), 'source': 'quantum_matrix'}, 'decision_owner': DECISION_OWNER, 'evidence_only': True, 'engine': 'quantum_representation_matrix_view_v3'}

    def domains(self, text):
        p = self.measure(text)
        return {'measurements': [{'domain': k, 'score': float(v)} for k, v in sorted(p['domain_scores'].items(), key=lambda x: x[1], reverse=True)], 'decision_owner': DECISION_OWNER, 'evidence_only': True, 'engine': 'quantum_domain_matrix_view_v3'}

    def _scene_matrix(self, p):
        reps = p['representation_scores']
        labels = list(SCENE_MATRIX_LABELS)
        vals = [float(reps.get(x, 0.0)) for x in labels]
        top = max(vals) if vals else 0.0
        scores = [v / top if top > 0 else 0.0 for v in vals]
        ranked = sorted(zip(labels, scores), key=lambda x: x[1], reverse=True)
        return {'labels': [x[0] for x in ranked], 'scores': [round(float(x[1]), 6) for x in ranked], 'best_scene': ranked[0][0] if ranked else 'text', 'best_score': round(float(ranked[0][1] if ranked else 0.0), 6), 'margin': round(float(ranked[0][1] - ranked[1][1] if len(ranked) > 1 else 0.0), 6), 'feature_order': list(SCENE_MATRIX_FEATURES), 'matrix_shape': [len(labels), len(SCENE_MATRIX_FEATURES)], 'evidence_only': True, 'engine': 'quantum_matrix_v3', 'decision_owner': DECISION_OWNER}

    @classmethod
    def _reference_resolution(cls, text: str, previous_assistant: str, previous_user: str='', semantic_profile: dict[str, Any] | None=None, reference_authorized: bool=False) -> dict:
        """Resolve an already-authorized semantic reference generically.

        Authorization comes from the canonical dialogue vector.  This method
        extracts a candidate antecedent from the immediately previous exchange;
        it does not classify the current turn using word triggers.
        """
        current = cls.normalize(text)
        prev = cls.normalize(previous_assistant)
        if not current or not prev or (not reference_authorized):
            return {'present': False, 'target': '', 'candidates': [], 'confidence': 0.0, 'source': 'semantic_entity_reference', 'anaphoric': False, 'short_followup': False, 'resolved': False}
        profile = semantic_profile if isinstance(semantic_profile, dict) else {}
        candidates: list[str] = []
        committed_state = profile.get('previous_dialogue_state')
        if isinstance(committed_state, dict):
            refs = committed_state.get('references') if isinstance(committed_state.get('references'), dict) else {}
            active_thread = committed_state.get('active_thread') if isinstance(committed_state.get('active_thread'), dict) else {}
            established = committed_state.get('established') if isinstance(committed_state.get('established'), dict) else {}
            for value in [refs.get('active_entity'), *list(active_thread.get('entities') or []), *list(established.get('entities') or []), refs.get('active_result')]:
                value = cls.normalize(value)
                if value and value.casefold() not in {x.casefold() for x in candidates}:
                    candidates.append(value)
        patterns = ('\\b(?:[А-ЯЁA-Z][а-яёa-z]+(?:\\s+[А-ЯЁA-Z][а-яёa-z]+){1,4})\\b', '\\b[А-ЯЁA-Z][а-яёa-z]{2,}\\b')
        stop = {str(item).casefold() for item in getattr(cls, '_STOP', set())}
        for source in (previous_user, prev):
            for pattern in patterns:
                for match in re.findall(pattern, source):
                    value = cls.normalize(match).strip('.,:;()[]{}<>—-"')
                    if value and value not in stop and (value not in candidates):
                        candidates.append(value)
                    if len(candidates) >= 16:
                        break
                if len(candidates) >= 16:
                    break
        if len(candidates) < 16:
            ignored = {str(item).casefold() for item in getattr(cls, '_STOP', set())}
            for token in cls._tokens(previous_user.lower()):
                if len(token) >= 4 and token not in ignored and (token not in {x.lower() for x in candidates}):
                    candidates.append(token)
                if len(candidates) >= 16:
                    break
        target = max(candidates, key=lambda value: (1 if isinstance((committed_state := profile.get('previous_dialogue_state')), dict) and (value.casefold() == cls.normalize((committed_state.get('references') if isinstance(committed_state.get('references'), dict) else {}).get('active_entity')).casefold() or value.casefold() == cls.normalize((committed_state.get('active_thread') if isinstance(committed_state.get('active_thread'), dict) else {}).get('topic')).casefold()) else 0, 1 if any((token.isalpha() for token in cls._tokens(value))) else 0, len(value.split()), len(value)), default='')
        confidence = 0.96 if target else 0.0
        return {'present': bool(target), 'target': target, 'candidates': candidates[:12], 'confidence': confidence, 'source': 'semantic_entity_reference', 'anaphoric': True, 'short_followup': len(cls._tokens(current)) <= 8, 'resolved': bool(target), 'semantic_reference_authorized': True, 'semantic_profile': {'best_dialogue': cls.normalize(profile.get('dialogue_best')), 'best_representation': cls.normalize(profile.get('best_representation'))}}

    def _resolve_scene_context(self, text, state, continuation, reference, memory=False, active_topic=''):
        if not isinstance(state, dict) or not (continuation or reference or memory):
            return {}
        scene = state.get('current_visual_scene') or state.get('active_visual_scene')
        if not isinstance(scene, dict) or not scene.get('scene_id'):
            return {}
        return {'relation': 'current_scene', 'confidence': 1.0, 'scene_id': scene.get('scene_id'), 'turn_id': scene.get('turn_id'), 'topic': self.normalize(scene.get('topic')), 'user_request': self.normalize(scene.get('user_request') or scene.get('current_request')), 'answer': self.normalize(scene.get('april_answer') or scene.get('answer') or scene.get('content')), 'summary': self.normalize(scene.get('summary')), 'render_block_types': list(scene.get('render_block_types') or []), 'presentation_types': list(scene.get('presentation_types') or []), 'render_blocks': list(scene.get('render_blocks') or []), 'presentation_signals': list(scene.get('presentation_signals') or []), 'semantic_state': scene.get('semantic_state') if isinstance(scene.get('semantic_state'), dict) else {}, 'supported_payloads': list(scene.get('supported_payloads') or []), 'renderer_state': scene.get('renderer_state') if isinstance(scene.get('renderer_state'), dict) else {}, 'semantic_source': 'interpretation_scene_resolution_v3', 'evidence_only': True}

    @staticmethod
    def _turn_id_number(value: Any) -> float:
        """Return a sortable turn id without assuming a particular persistence type."""
        try:
            return float(value)
        except Exception:
            return -1.0

    def _select_latest_completed_turn_meaning(self, *, state: dict[str, Any], history: list, last_user: str, last_assistant: str, reply_to: Any) -> dict[str, Any]:
        """
        Recover the newest completed USER→APRIL meaning before interpreting a new turn.

        Persistence contains several representations of the same conversation:
        `last_turn_meaning`, `turn_meaning_history`, and the authenticated chat log.
        They are evidence for one canonical meaning, not competing dialogue states.

        The previous implementation trusted `state["last_turn_meaning"]` even when that
        record was stale. That allowed an older clarification/result to replace the actual
        latest completed answer. We now select by completed turn identity/recency and rebuild
        the meaning from the latest authentic chat pair when the persisted meaning is behind.
        """
        state = state if isinstance(state, dict) else {}
        candidates: list[tuple[float, int, dict[str, Any], str]] = []

        def add(value: Any, source: str, order: int) -> None:
            if not isinstance(value, dict):
                return
            user = self.normalize(value.get('user_request') or (value.get('dialogue_anchor') or {}).get('user') if isinstance(value.get('dialogue_anchor'), dict) else value.get('user_request') or '')
            answer = self.normalize(value.get('answer') or (value.get('dialogue_anchor') or {}).get('april') if isinstance(value.get('dialogue_anchor'), dict) else value.get('answer') or '')
            if not user or not answer:
                return
            turn_number = self._turn_id_number(value.get('turn_id'))
            candidates.append((turn_number, order, value, source))
        add(state.get('last_turn_meaning'), 'state.last_turn_meaning', 10)
        history_meanings = state.get('turn_meaning_history')
        if isinstance(history_meanings, list):
            for index, value in enumerate(history_meanings):
                add(value, 'state.turn_meaning_history', 100 + index)
        latest_reply_number = self._turn_id_number(reply_to)
        if last_user and last_assistant:
            persisted_newest = max((item[0] for item in candidates), default=-1.0)
            if latest_reply_number >= 0 and latest_reply_number > persisted_newest:
                try:
                    rebuilt = QUANTUM_TURN_MEANING_ENGINE.build(last_user, last_assistant, render_blocks=(state.get('current_visual_scene') or {}).get('render_blocks', []) if isinstance(state.get('current_visual_scene'), dict) and self._turn_id_number((state.get('current_visual_scene') or {}).get('turn_id')) == latest_reply_number else [], summary=(state.get('current_visual_scene') or {}).get('summary', '') if isinstance(state.get('current_visual_scene'), dict) and self._turn_id_number((state.get('current_visual_scene') or {}).get('turn_id')) == latest_reply_number else '', turn_id=reply_to, scene_id=(state.get('current_visual_scene') or {}).get('scene_id', '') if isinstance(state.get('current_visual_scene'), dict) and self._turn_id_number((state.get('current_visual_scene') or {}).get('turn_id')) == latest_reply_number else '', semantic_engine=self)
                    return rebuilt
                except Exception:
                    pass
        if not candidates:
            if last_user and last_assistant:
                try:
                    return QUANTUM_TURN_MEANING_ENGINE.build(last_user, last_assistant, turn_id=reply_to, semantic_engine=self)
                except Exception:
                    return {}
            return {}
        candidates.sort(key=lambda item: (item[0], item[1]))
        return deepcopy(candidates[-1][2])

    def interpret(self, text, cognition=None, semantic=None, history=None, state=None):
        text = self.normalize(text)
        if not text:
            return None
        cognition = cognition if isinstance(cognition, dict) else {}
        semantic = semantic if isinstance(semantic, dict) else {}
        state = state if isinstance(state, dict) else {}
        history = history if isinstance(history, list) else []
        last_a, last_u, reply_to = self._history(history)
        last_turn_meaning = self._select_latest_completed_turn_meaning(state=state, history=history, last_user=last_u, last_assistant=last_a, reply_to=reply_to)
        # Live state extends the same semantic anchor. It does not create a
        # parallel dialogue decision path.
        if isinstance(last_turn_meaning, dict) and last_turn_meaning:
            live = deepcopy(last_turn_meaning)
            live_state = live.get('dialogue_state') if isinstance(live.get('dialogue_state'), dict) else {}
            pending_live = state.get('april_pending_task')
            if isinstance(pending_live, dict) and pending_live.get('active'):
                live_state['open_task'] = {
                    **dict(live_state.get('open_task') or {}),
                    'pending_input': True,
                    'expected_input_type': pending_live.get('expected_input_type'),
                    'topic': pending_live.get('topic'),
                }
                live['response_contract'] = {
                    **dict(live.get('response_contract') or {}),
                    'pending_input': True,
                    'pending_input_type': pending_live.get('expected_input_type'),
                }
            active_live = state.get('april_active_task')
            if isinstance(active_live, dict):
                thread = live_state.get('active_thread') if isinstance(live_state.get('active_thread'), dict) else {}
                live_state['active_thread'] = {
                    **thread,
                    # The semantic thread owns the topic. Renderer/object labels
                    # (for example `illustration`) must never overwrite it.
                    'topic': thread.get('topic') or active_live.get('semantic_topic') or active_live.get('topic', ''),
                    'goal': active_live.get('goal') or thread.get('goal', ''),
                    'operation': active_live.get('operation') or thread.get('operation', ''),
                    'entities': list(dict.fromkeys([*(thread.get('entities') or []), active_live.get('semantic_topic') or active_live.get('object') or ''])),
                }
            live['dialogue_state'] = live_state
            last_turn_meaning = live
        selected_turn_number = self._turn_id_number(last_turn_meaning.get('turn_id') if isinstance(last_turn_meaning, dict) else None)
        recent_meanings = []
        transition = QUANTUM_TURN_MEANING_ENGINE.compare(text, last_turn_meaning if isinstance(last_turn_meaning, dict) else {}, semantic_engine=self, recent_meanings=recent_meanings) if isinstance(last_turn_meaning, dict) else {'relation': 'NEW_TOPIC', 'anchor': 'none', 'relation_scores': {}, 'evidence': {}}
        sequential_dialogue = QUANTUM_SEQUENTIAL_DIALOGUE_ENGINE.resolve(
            text,
            last_turn_meaning if isinstance(last_turn_meaning, dict) else {},
            previous_user=last_u,
            previous_answer=last_a,
            recent_history=history,
            semantic_engine=self,
            previous_scene=state.get('current_visual_scene') if isinstance(state.get('current_visual_scene'), dict) else {},
        )
        sequential_relation = str(sequential_dialogue.get('relation') or 'NEW').upper()
        dialogue_trajectory = deepcopy(sequential_dialogue.get('trajectory') or {})
        if sequential_relation == 'CONTINUE':
            transition = {**dict(transition or {}), 'relation': 'DEVELOP_CURRENT', 'anchor': 'last_turn', 'selected_turn_meaning': deepcopy(last_turn_meaning), 'selected_memory_operand': deepcopy(sequential_dialogue.get('selected_pair') or {}), 'source': 'sequential_dialogue_owner', 'sequential_dialogue': deepcopy(sequential_dialogue)}
        elif sequential_relation == 'RECALL':
            transition = {**dict(transition or {}), 'relation': 'REVISIT_RECENT', 'anchor': 'none', 'source': 'sequential_dialogue_owner', 'sequential_dialogue': deepcopy(sequential_dialogue)}
        else:
            transition = {**dict(transition or {}), 'relation': 'NEW_TOPIC', 'anchor': 'none', 'selected_turn_meaning': {}, 'selected_memory_operand': {}, 'source': 'sequential_dialogue_owner', 'sequential_dialogue': deepcopy(sequential_dialogue)}
        last_meaning_topic = self.normalize(last_turn_meaning.get('meaning', {}).get('topic')) if isinstance(last_turn_meaning, dict) and isinstance(last_turn_meaning.get('meaning'), dict) else ''
        last_meaning_goal = self.normalize(last_turn_meaning.get('meaning', {}).get('goal')) if isinstance(last_turn_meaning, dict) and isinstance(last_turn_meaning.get('meaning'), dict) else ''
        if transition.get('relation') in {'DEVELOP_CURRENT', 'REFER_CURRENT'} and transition.get('anchor') == 'last_turn':
            active_topic = last_meaning_topic or self.normalize(state.get('active_topic') or state.get('current_topic'))
            active_goal = last_meaning_goal or self.normalize(state.get('active_goal') or state.get('current_goal'))
            topic_owner = 'last_turn_meaning'
        elif transition.get('relation') == 'REVISIT_RECENT':
            selected = transition.get('selected_turn_meaning') if isinstance(transition.get('selected_turn_meaning'), dict) else {}
            selected_meaning = selected.get('meaning') if isinstance(selected.get('meaning'), dict) else {}
            active_topic = self.normalize(selected_meaning.get('topic') or selected.get('user_request') or '')
            active_goal = self.normalize(selected_meaning.get('goal') or '')
            topic_owner = 'recent_turn_meaning'
        else:
            active_topic = ''
            active_goal = ''
            topic_owner = 'current_request'
        p = self.measure(text, previous_assistant=last_a, previous_user=last_u, active_topic=active_topic, active_goal=active_goal)
        previous_scene = state.get('current_visual_scene') or state.get('active_visual_scene')
        if not isinstance(previous_scene, dict):
            previous_scene = {}
        try:
            scene_topic = self.normalize(previous_scene.get('topic') or previous_scene.get('user_request'))
            scene_meta = previous_scene.get('metadata') if isinstance(previous_scene.get('metadata'), dict) else {}
            internal_scene = bool(previous_scene.get('internal_context') or previous_scene.get('internal_turn') or scene_meta.get('internal_context') or scene_topic.startswith('VISUAL_ANALYSIS:'))
            if internal_scene:
                previous_scene = {}
        except Exception:
            pass
        recent_dialogue_pairs = self._recent_dialogue_pairs(history, limit=10)
        canonical_selected_pair = deepcopy(sequential_dialogue.get('selected_pair') or {})
        canonical_dialogue_relation = 'CONTINUE_TOPIC' if sequential_relation == 'CONTINUE' else 'RECALL' if sequential_relation == 'RECALL' else 'NEW_TOPIC'
        dialogue_vector = {'relation': canonical_dialogue_relation, 'topic_relation': 'SAME_TOPIC' if sequential_relation == 'CONTINUE' else canonical_dialogue_relation, 'request_relation': canonical_dialogue_relation, 'request_dependency': 'continuation' if sequential_relation == 'CONTINUE' else 'recall' if sequential_relation == 'RECALL' else 'independent', 'continuation': sequential_relation == 'CONTINUE', 'reference_to_previous': sequential_relation == 'RECALL', 'three_way_relation': sequential_relation, 'canonical_topic': '', 'selected_memory_operand': canonical_selected_pair, 'selected_memory_index': -1, 'semantic_dialogue_label': p.get('dialogue_best', 'independent'), 'semantic_dialogue_confidence': p.get('dialogue_confidence', 0.0), 'source': 'sequential_dialogue_owner', 'sequential_dialogue': deepcopy(sequential_dialogue), 'trajectory': deepcopy(dialogue_trajectory)}
        d = {'label': 'continuation' if sequential_relation == 'CONTINUE' else 'reference' if sequential_relation == 'RECALL' else p.get('dialogue_best', 'independent'), 'confidence': float(sequential_dialogue.get('confidence', 0.0) or 0.0), 'continuation_score': float(sequential_dialogue.get('scores', {}).get('continuation', 0.0) or 0.0), 'reference_score': float(sequential_dialogue.get('scores', {}).get('reference_semantics', 0.0) or 0.0), 'topic_score': float(sequential_dialogue.get('scores', {}).get('answer_similarity', 0.0) or 0.0)}
        explicit = semantic.get('required_representations') or cognition.get('required_representations') or []
        context_understanding = QUANTUM_CONTEXT_ENGINE.analyze(text, history=history, state=state, semantic=semantic, cognition=cognition, active_topic=active_topic, active_goal=active_goal, previous_scene=previous_scene, semantic_profile=p, canonical_dialogue=sequential_dialogue)
        topic_understanding = context_understanding.get('topic') if isinstance(context_understanding.get('topic'), dict) else {}
        discourse_understanding = context_understanding.get('discourse') if isinstance(context_understanding.get('discourse'), dict) else {}
        dialogue_selection = context_understanding.get('dialogue_selection') if isinstance(context_understanding.get('dialogue_selection'), dict) else {}
        entities_understanding = context_understanding.get('entities') if isinstance(context_understanding.get('entities'), dict) else {}
        sequential_pair = sequential_dialogue.get('selected_pair') if isinstance(sequential_dialogue.get('selected_pair'), dict) else {}
        if sequential_relation == 'CONTINUE':
            dialogue_selection = {**dict(dialogue_selection or {}), 'relation': 'CONTINUE', 'selected_pair': deepcopy(sequential_pair), 'selected_index': -1, 'confidence': sequential_dialogue.get('confidence', 0.0), 'source': 'sequential_dialogue_owner'}
            context_understanding['dialogue_selection'] = deepcopy(dialogue_selection)
            context_understanding['discourse'] = {**dict(context_understanding.get('discourse') or {}), 'relation': 'CONTINUE_TOPIC', 'continuation': True, 'new_topic': False, 'three_way_relation': 'CONTINUE', 'selected_memory_operand': deepcopy(sequential_pair), 'source': 'sequential_dialogue_owner'}
        elif sequential_relation == 'RECALL':
            dialogue_selection = {**dict(dialogue_selection or {}), 'relation': 'RECALL', 'selected_pair': {}, 'selected_index': -1, 'confidence': sequential_dialogue.get('confidence', 0.0), 'source': 'sequential_dialogue_owner'}
            context_understanding['dialogue_selection'] = deepcopy(dialogue_selection)
        else:
            dialogue_selection = {**dict(dialogue_selection or {}), 'relation': 'NEW', 'selected_pair': {}, 'selected_index': -1, 'confidence': sequential_dialogue.get('confidence', 0.0), 'source': 'sequential_dialogue_owner'}
            context_understanding['dialogue_selection'] = deepcopy(dialogue_selection)
            context_understanding['discourse'] = {**dict(context_understanding.get('discourse') or {}), 'relation': 'NEW_TOPIC', 'continuation': False, 'new_topic': True, 'three_way_relation': 'NEW', 'selected_memory_operand': {}, 'source': 'sequential_dialogue_owner'}
        context_relation_raw = str(dialogue_selection.get('relation') or '').upper()
        context_task_state = context_understanding.get('task') if isinstance(context_understanding.get('task'), dict) else {}
        context_history_task = dialogue_selection.get('history_task_context') if isinstance(dialogue_selection.get('history_task_context'), dict) else {}
        context_semantic_dependency = bool(sequential_relation == 'CONTINUE' and context_relation_raw in {'CONTINUE', 'CONTINUE_TOPIC', 'CONTINUATION', 'ARTIFACT_REFERENCE', 'MEMORY_QUERY'} and dialogue_selection.get('selected_pair'))
        if context_semantic_dependency:
            semantic_anchor_meaning = deepcopy(last_turn_meaning) if isinstance(last_turn_meaning, dict) and last_turn_meaning else {'user_request': dialogue_selection.get('selected_pair', {}).get('user') or last_u, 'answer': dialogue_selection.get('selected_pair', {}).get('april') or last_a, 'dialogue_anchor': {'user': dialogue_selection.get('selected_pair', {}).get('user') or last_u, 'april': dialogue_selection.get('selected_pair', {}).get('april') or last_a}, 'source': 'authenticated_latest_dialogue_pair'}
            transition = {**dict(transition or {}), 'relation': 'DEVELOP_CURRENT', 'anchor': 'last_turn', 'selected_turn_meaning': semantic_anchor_meaning, 'source': 'semantic_context_structural_dependency', 'semantic_dependency_proven': True}
        selected_relation = sequential_relation
        selected_pair = deepcopy(sequential_dialogue.get('selected_pair') or {}) if sequential_relation == 'CONTINUE' else {}
        selected_relation = {'CONTINUE_TOPIC': 'CONTINUE', 'CONTINUATION': 'CONTINUE', 'ARTIFACT_REFERENCE': 'CONTINUE', 'MEMORY_QUERY': 'CONTINUE', 'RECALL': 'RECALL', 'NEW_TOPIC': 'NEW', 'INDEPENDENT': 'NEW'}.get(selected_relation, selected_relation)
        if selected_relation == 'CONTINUE' and (last_u or last_a):
            transition = {**dict(transition or {}), 'relation': 'DEVELOP_CURRENT', 'anchor': 'last_turn', 'selected_turn_meaning': deepcopy(last_turn_meaning) if isinstance(last_turn_meaning, dict) and last_turn_meaning else {'user_request': last_u, 'answer': last_a, 'source': 'authenticated_latest_dialogue_pair'}, 'source': 'semantic_context_relation', 'semantic_dependency_proven': True}
        transition_relation = 'DEVELOP_CURRENT' if sequential_relation == 'CONTINUE' else 'REVISIT_RECENT' if sequential_relation == 'RECALL' else 'NEW_TOPIC'
        if transition_relation in {'DEVELOP_CURRENT', 'REFER_CURRENT'} and transition.get('anchor') == 'last_turn':
            if last_u or last_a:
                selected_relation = 'CONTINUE'
                selected_pair = {'user': last_u, 'april': last_a, 'source': 'last_turn_meaning', 'meaning': deepcopy(last_turn_meaning)}
        elif transition_relation == 'NEW_TOPIC':
            if selected_relation != 'CONTINUE':
                selected_relation = 'NEW'
                selected_pair = {}
        elif transition_relation == 'REVISIT_RECENT':
            selected_relation = 'RECALL'
            selected_meaning = transition.get('selected_turn_meaning')
            if isinstance(selected_meaning, dict):
                selected_pair = {'user': self.normalize(selected_meaning.get('user_request')), 'april': self.normalize(selected_meaning.get('answer')), 'source': 'recent_turn_meaning', 'meaning': deepcopy(selected_meaning)}
        if selected_relation == 'CONTINUE':
            dialogue_vector = {**dict(dialogue_vector or {}), 'relation': 'CONTINUE_TOPIC', 'topic_relation': 'SAME_TOPIC', 'request_relation': 'CONTINUE_TOPIC', 'request_dependency': 'continuation', 'continuation': True, 'reference_to_previous': False, 'three_way_relation': 'CONTINUE', 'selected_memory_operand': selected_pair, 'selected_memory_index': dialogue_selection.get('selected_index', -1)}
        elif selected_relation == 'RECALL':
            dialogue_vector = {**dict(dialogue_vector or {}), 'relation': 'RECALL', 'topic_relation': 'RECALL', 'request_relation': 'RECALL', 'request_dependency': 'recall', 'continuation': False, 'reference_to_previous': True, 'three_way_relation': 'RECALL', 'selected_memory_operand': selected_pair, 'selected_memory_index': dialogue_selection.get('selected_index', -1)}
        else:
            dialogue_vector = {**dict(dialogue_vector or {}), 'relation': 'NEW_TOPIC', 'topic_relation': 'NEW_TOPIC', 'request_relation': 'NEW_TOPIC', 'request_dependency': 'independent', 'continuation': False, 'reference_to_previous': False, 'three_way_relation': 'NEW', 'selected_memory_operand': {}, 'selected_memory_index': -1, 'reuse_existing_scene': False, 'previous_scene_id': ''}
        turn_structure_understanding = context_understanding.get('turn_structure') if isinstance(context_understanding.get('turn_structure'), dict) else {}
        task_understanding = context_understanding.get('task') if isinstance(context_understanding.get('task'), dict) else {}
        complete_outputs = [str(x).lower() for x in (task_understanding.get('requested_outputs') if isinstance(task_understanding, dict) else []) if str(x).strip()]
        scene_composition = []
        seen_scene_parts = set()
        for segment in task_understanding.get('output_segments') or []:
            if not isinstance(segment, dict):
                continue
            output = _clean_representation(segment.get('output'))
            if not output:
                continue
            key = (int(segment.get('segment_index', 1) or 1), output)
            if key in seen_scene_parts:
                continue
            seen_scene_parts.add(key)
            scene_composition.append({'segment_index': key[0], 'representation': output, 'segment_text': self.normalize(segment.get('segment_text') or segment.get('text') or ''), 'semantic_source': segment.get('source', 'current_turn_task_matrix'), 'sequence': len(scene_composition)})
        for output in complete_outputs:
            output = _clean_representation(output)
            if not output:
                continue
            if not any((item.get('representation') == output for item in scene_composition)):
                scene_composition.append({'segment_index': 1, 'representation': output, 'segment_text': text, 'semantic_source': 'complete_current_turn', 'sequence': len(scene_composition)})
        if scene_composition and (not any((item.get('representation') == 'text' for item in scene_composition))):
            scene_composition.insert(0, {'segment_index': 1, 'representation': 'text', 'segment_text': text, 'semantic_source': 'human_answer_companion', 'sequence': 0})
        for index, item in enumerate(scene_composition):
            item['sequence'] = index
        local_turn_reference = bool(turn_structure_understanding.get('local_ordinal_reference') and turn_structure_understanding.get('historical_ordinal_reference_blocked'))
        if local_turn_reference:
            local_relation = 'CONTINUE_TOPIC' if selected_relation == 'CONTINUE' else 'RECALL' if selected_relation == 'RECALL' else 'NEW_TOPIC'
            local_topic_relation = 'SAME_TOPIC' if selected_relation == 'CONTINUE' else 'RECALL' if selected_relation == 'RECALL' else 'NEW_TOPIC'
            dialogue_vector = {**dict(dialogue_vector or {}), 'relation': local_relation, 'topic_relation': local_topic_relation, 'request_relation': local_relation, 'request_dependency': 'continuation' if selected_relation == 'CONTINUE' else 'recall' if selected_relation == 'RECALL' else 'independent', 'reference_to_previous': selected_relation == 'RECALL', 'explicit_reference': False, 'anaphoric': False, 'artifact_reference_evidence': False, 'previous_scene_id': '', 'reuse_existing_scene': False, 'local_current_turn_structure': True, 'historical_ordinal_reference_blocked': True}
            d = {**dict(d or {}), 'label': 'question' if d.get('label') in {'reference', 'artifact_reference'} else d.get('label'), 'continuation_score': 0.0, 'reference_score': 0.0, 'topic_score': float(topic_understanding.get('similarity_to_best_pair', 0.0) or 0.0)}
        reconstructed_topic = normalize_text(topic_understanding.get('active'))
        if transition_relation == 'NEW_TOPIC':
            current_content = QuantumContextUnderstandingEngine._content_tokens(text)
            current_content = [token for token in current_content if token.casefold() not in DIALOGUE_TASK_FUNCTION_WORDS]
            current_profile_topic = normalize_text(' '.join(current_content[:6])) if current_content else ''
            active_topic = current_profile_topic or normalize_text(text)
            active_goal = normalize_text(p.get('best_goal') or '')
            topic_owner = 'current_request'
        elif transition_relation in {'DEVELOP_CURRENT', 'REFER_CURRENT'} and transition.get('anchor') == 'last_turn':
            active_topic = normalize_text(last_meaning_topic or reconstructed_topic or active_topic)
            active_goal = normalize_text(last_meaning_goal or active_goal)
            topic_owner = 'last_turn_meaning'
        elif transition_relation == 'REVISIT_RECENT':
            selected = transition.get('selected_turn_meaning') if isinstance(transition.get('selected_turn_meaning'), dict) else {}
            selected_meaning = selected.get('meaning') if isinstance(selected.get('meaning'), dict) else {}
            active_topic = normalize_text(selected_meaning.get('topic') or selected.get('user_request') or active_topic)
            active_goal = normalize_text(selected_meaning.get('goal') or active_goal)
            topic_owner = 'recent_turn_meaning'
        elif reconstructed_topic and topic_understanding.get('relation') in {'SAME_TOPIC', 'CONTINUE_TOPIC', 'RECALL'}:
            active_topic = reconstructed_topic
        # Canonical subject for live dialogue state. Renderer labels such as
        # `image` or `formula` are representations, not the semantic referent.
        dialogue_vector = {**dict(dialogue_vector or {}), 'canonical_topic': normalize_text(active_topic)}
        if selected_relation == 'CONTINUE' and (not local_turn_reference) and discourse_understanding.get('historical_reference') and entities_understanding.get('coreference'):
            coref_packets = entities_understanding.get('coreference') or []
            best_coref = coref_packets[0] if isinstance(coref_packets[0], dict) else {}
            coref_candidates = best_coref.get('candidates') or []
            if coref_candidates and float(best_coref.get('confidence', 0.0) or 0.0) >= 0.34:
                dialogue_vector = {**dict(dialogue_vector or {}), 'relation': 'CONTINUE_TOPIC', 'topic_relation': 'SAME_TOPIC', 'request_relation': 'CONTINUE_TOPIC', 'request_dependency': 'continuation', 'reference_to_previous': True, 'explicit_reference': True, 'anaphoric': True, 'semantic_reference': coref_candidates[0].get('entity'), 'semantic_reference_confidence': float(best_coref.get('confidence', 0.0) or 0.0)}
                d = {**dict(d or {}), 'label': 'reference', 'continuation_score': max(float(d.get('continuation_score', 0.0) or 0.0), float(best_coref.get('confidence', 0.0) or 0.0)), 'reference_score': max(float(d.get('reference_score', 0.0) or 0.0), float(best_coref.get('confidence', 0.0) or 0.0)), 'topic_score': max(float(d.get('topic_score', 0.0) or 0.0), float(topic_understanding.get('similarity_to_best_pair', 0.0) or 0.0))}
        explicit = semantic.get('required_representations') or cognition.get('required_representations') or []
        production, source, locked = self._resolve_production(text, p, explicit)
        context_outputs = [str(x).lower() for x in task_understanding.get('requested_outputs') or []]
        object_scores = p.get('object_scores') if isinstance(p.get('object_scores'), dict) else {}
        op_name = str(p.get('best_operation') or '').lower()
        compatible_context = {'formula': {'calculate', 'answer', 'explain', 'present', 'build', 'modify'}, 'code': {'build', 'modify', 'present', 'explain', 'analyze'}, 'link': {'retrieve', 'present', 'answer', 'list', 'explain'}, 'table': {'build', 'present', 'compare', 'list', 'explain', 'analyze'}, 'graph': {'build', 'present', 'calculate', 'analyze', 'compare', 'list', 'explain'}, 'diagram': {'build', 'present', 'modify', 'explain', 'analyze'}, 'image': {'build', 'present', 'modify'}, 'gallery': {'build', 'present', 'compare', 'list'}}
        context_structured = [item for item in context_outputs if item in compatible_context and op_name in compatible_context[item]]
        context_structured.sort(key=lambda item: float(object_scores.get(item, 0.0) or 0.0), reverse=True)
        if context_structured and (not explicit):
            best_context_rep = context_structured[0]
            best_context_score = float(object_scores.get(best_context_rep, 0.0) or 0.0)
            if best_context_score >= 0.08 and (production == 'text' or best_context_rep != production):
                production = best_context_rep
                source = 'context_task_matrix_resolution'
                locked = True
        current_visual_input_present = bool(state.get('_incoming_visual_evidence') if isinstance(state, dict) else False)
        visual_mode = str(p.get('visual_production_mode') or 'none').lower()
        if current_visual_input_present and visual_mode == 'image_generation':
            visual_mode = 'visual_analysis'
        image_generation_request = visual_mode == 'image_generation'
        lightweight_visual_request = visual_mode == 'diagram'
        complex_image_generation = image_generation_request
        if visual_mode == 'image_generation':
            production = 'image'
            source = 'semantic_visual_image_generation'
            locked = True
        elif visual_mode == 'diagram':
            production = 'diagram'
            source = 'semantic_light_visual_construction'
            locked = True
        continuation = bool(sequential_relation == 'CONTINUE' or dialogue_vector.get('relation') == 'CONTINUE_TOPIC')
        current_task_operation = str(p.get('best_operation') or '').lower()
        current_task_production_request = current_task_operation in {'build', 'modify', 'present', 'calculate'}
        current_explicit_structured = bool(explicit or (current_task_production_request and any((_clean_representation(x) in STRUCTURED_REPRESENTATIONS for x in complete_outputs or []))))
        if continuation and (not current_task_production_request) and (not current_explicit_structured) and (not image_generation_request):
            production = 'text'
            source = 'continuation_answer_without_new_representation'
            locked = True
        if production != 'text' and (not explicit):
            op = str(p.get('best_operation') or '').lower()
            obj = str(p.get('best_object') or '').lower()
            goal = str(p.get('best_goal') or '').lower()
            obj_score = float(p.get('object_scores', {}).get(production, 0.0) or 0.0)
            current_visual_intent = locked or (op in {'build', 'modify', 'present', 'explain'} and obj == production and (obj_score >= 0.1) and (goal in {'visualize', 'transform', 'present', 'organize'}))
            if not current_visual_intent:
                production = 'text'
                source = 'current_turn_representation_not_established'
                locked = False
        if continuation and production == 'text' and isinstance(previous_scene, dict):
            operation = str(p.get('best_operation') or '').lower()
            current_outputs_explicit = bool(complete_outputs or explicit)
            prior_types = [_clean_representation(x) for x in previous_scene.get('render_block_types') or []]
            if not prior_types:
                prior_types = [_clean_representation(block.get('type') or block.get('artifact_type') or block.get('representation')) for block in previous_scene.get('render_blocks') or [] if isinstance(block, dict)]
            prior_structured = [x for x in prior_types if x in STRUCTURED_REPRESENTATIONS]
            continuation_can_produce_structured = bool(current_outputs_explicit and operation in {'modify', 'build', 'present', 'calculate'} and prior_structured)
            if continuation_can_produce_structured:
                current_structured = [_clean_representation(x) for x in complete_outputs if _clean_representation(x) in STRUCTURED_REPRESENTATIONS]
                if current_structured:
                    production = current_structured[0]
                    source = 'current_task_explicit_structured_continuation'
                    locked = True
        reference = bool(dialogue_vector.get('request_relation') == 'ARTIFACT_REFERENCE' or dialogue_vector.get('reference_to_previous'))
        memory = bool(p['dialogue_best'] == 'memory_query' or dialogue_vector.get('request_relation') == 'MEMORY_QUERY')
        semantic_profile_for_reference = {**p, 'dialogue_best': p.get('dialogue_best'), 'previous_dialogue_state': last_turn_meaning.get('dialogue_state') if isinstance(last_turn_meaning, dict) and isinstance(last_turn_meaning.get('dialogue_state'), dict) else {}}
        reference_resolution = self._reference_resolution(text, last_a, last_u, semantic_profile=semantic_profile_for_reference, reference_authorized=reference)
        explicit_reference = bool(dialogue_vector.get('request_relation') == 'ARTIFACT_REFERENCE')
        if reference_resolution.get('resolved') and reference_resolution.get('target') and explicit_reference:
            reference = True
            continuation = True
            dialogue_vector['reference_resolution'] = reference_resolution
            dialogue_vector['resolved_reference'] = reference_resolution.get('target')
            if production == 'text' and isinstance(previous_scene, dict):
                prior_types = [_clean_representation(x) for x in previous_scene.get('render_block_types') or []]
                if not prior_types:
                    prior_types = [_clean_representation(block.get('type') or block.get('artifact_type') or block.get('representation')) for block in previous_scene.get('render_blocks') or [] if isinstance(block, dict)]
                prior_structured = [x for x in prior_types if x in STRUCTURED_REPRESENTATIONS]
                if prior_structured:
                    production = prior_structured[0]
                    source = 'reference_reuse_existing_representation'
                    locked = True
        artifact_reference_answer = bool(reference and dialogue_vector.get('artifact_reference_evidence') and (str(p.get('best_operation') or '').lower() in {'answer', 'list', 'analyze', 'explain', 'retrieve', 'build'}))
        if artifact_reference_answer:
            production = 'text'
            source = 'artifact_reference_answer'
            locked = True
            dialogue_vector['artifact_reference_answer'] = True
        resolved_scene = self._resolve_scene_context(text, state, continuation, reference, memory=memory, active_topic=active_topic)
        state_reference = ''
        if isinstance(last_turn_meaning, dict):
            previous_state = last_turn_meaning.get('dialogue_state')
            if isinstance(previous_state, dict):
                refs = previous_state.get('references')
                if isinstance(refs, dict):
                    state_reference = self.normalize(refs.get('active_entity') or refs.get('active_result') or '')
        trajectory_reference = str(dialogue_trajectory.get('active_referent') or '').strip()
        orthographic_target = str((dialogue_trajectory.get('orthographic_reference') or {}).get('target') or '').strip()
        # A reference exists only when the current turn semantically depends on
        # the active thread. A NEW topic must not inherit the previous referent.
        resolved_reference = (
            (orthographic_target if continuation or reference else '')
            or (trajectory_reference if continuation or reference else '')
            or (reference_resolution.get('target') if continuation or reference else '')
            or (state_reference if continuation or reference else '')
        )
        resolved_request = text
        history_task_context = dict(dialogue_vector.get('history_task_context') or {})
        orthographic_target = str((dialogue_trajectory.get('orthographic_reference') or {}).get('target') or '').strip()
        if orthographic_target and sequential_relation == 'CONTINUE':
            resolved_request = f'{text}\n\nThe current short reference is an orthographic variation of the established active entity: {orthographic_target}. Continue from that entity without asking the user to restate it.'
        if sequential_relation == 'CONTINUE' and (last_u or last_a):
            resolved_request = f'{text}\n\nThe current request is a semantic continuation of the immediately preceding completed USER→APRIL turn. Continue from that result; do not ask the user to repeat information already present.\nPrevious USER request: {last_u}\nPrevious APRIL answer: {last_a}'
            if orthographic_target:
                resolved_request += f'\nSemantic spelling correction: the current reference resolves to "{orthographic_target}".'
        selected_memory = dialogue_vector.get('selected_memory_operand')
        if selected_relation == 'RECALL' and isinstance(selected_memory, dict):
            recalled_user = self.normalize(selected_memory.get('user'))
            recalled_result = self.normalize(selected_memory.get('result') or selected_memory.get('april') or selected_memory.get('assistant'))
            if recalled_user or recalled_result:
                resolved_request = f'{text}\n\nThe current request recalls an older authenticated USER↔APRIL result. Use the recalled result as a concrete context operand and develop it; do not ask the user to resend the previous result.\nRecalled USER request: {recalled_user}\nRecalled APRIL result: {recalled_result}'
                reference = True
                memory = False
                dialogue_vector['resolved_memory_operand'] = {'user': recalled_user, 'result': recalled_result, 'index': dialogue_vector.get('selected_memory_index', -1)}
        if history_task_context.get('required'):
            selected_results = history_task_context.get('selected_results') or []
            lines = []
            for idx, item in enumerate(selected_results, start=1):
                lines.append(f"Historical result {idx}: {item.get('result')} (from USER: {item.get('user')}; APRIL: {item.get('assistant')})")
            resolved_request = f'{text}\n\nThe current calculation is history-dependent. The interpretation engine resolved the required operands from the two most recent concrete numeric results in the authenticated USER↔APRIL dialogue history. Use these values directly; do not ask the user to repeat them.\n' + '\n'.join(lines)
        if resolved_reference and (continuation or reference):
            resolved_request = f'{resolved_request}\nResolved semantic referent: {resolved_reference}. Use this referent as the object of the current request and do not ask the user to repeat established context.'
        if reference_resolution.get('resolved') and reference_resolution.get('target'):
            resolved_scene = dict(resolved_scene or {})
            resolved_scene['reference_target'] = reference_resolution.get('target')
            resolved_scene['reference_resolution'] = dict(reference_resolution)
        evidence = [{'label': k, 'score': float(v), 'source': 'quantum_matrix', 'positive': True, 'details': {}} for k, v in sorted(p['representation_scores'].items(), key=lambda x: x[1], reverse=True) if float(v) >= 0.2]
        domains = [k for k, v in p['domain_scores'].items() if float(v) >= 0.2]
        matrix = self._scene_matrix(p)
        visual_schema_scores = dict(p.get('visual_schema_scores') or {})
        visual_schema_rank = sorted(visual_schema_scores.items(), key=lambda item: float(item[1]), reverse=True)
        visual_schema = visual_schema_rank[0][0] if visual_schema_rank else ''
        visual_schema_confidence = float(visual_schema_rank[0][1]) if visual_schema_rank else 0.0
        text_schema_score = float(p.get('request_features', {}).get('ascii_schema_score', 0.0) or 0.0)
        ascii_schema_advisory = bool(production == 'text' and text_schema_score >= 0.15 and (p.get('best_operation') in {'build', 'present', 'answer', 'explain', 'list', 'modify'}))
        semantic_task = {'operation': p['best_operation'], 'object': p['best_object'], 'goal': p['best_goal'], 'representation': production, 'visual_schema': visual_schema, 'visual_schema_confidence': visual_schema_confidence, 'ascii_schema_advisory': ascii_schema_advisory, 'ascii_schema_score': float(p.get('request_features', {}).get('ascii_schema_score', 0.0) or 0.0), 'operation_scores': p['operation_scores'], 'object_scores': p['object_scores'], 'goal_scores': p['goal_scores']}
        # Canonical scene outputs are the complete current-turn semantic plan.
        # Never collapse them to the single highest-scoring representation.
        canonical_scene_outputs = _scene_clean_outputs(complete_outputs)
        if visual_mode == 'image_generation' and 'image' not in canonical_scene_outputs:
            canonical_scene_outputs.insert(0, 'image')
        elif visual_mode == 'diagram' and 'diagram' not in canonical_scene_outputs:
            canonical_scene_outputs.insert(0, 'diagram')
        if len(canonical_scene_outputs) > 1 and 'text' not in canonical_scene_outputs:
            canonical_scene_outputs.insert(0, 'text')
        complete_outputs = list(dict.fromkeys(canonical_scene_outputs))
        presentation_recommendations = self._presentation_recommendations(text, p, production, locked=locked, continuation=continuation, previous_scene=previous_scene, explicit=explicit, requested_outputs=complete_outputs)

        presentation = {'version': 'quantum_interpretation_transport_v4', 'decision_owner': DECISION_OWNER, 'single_route': True, 'production_representation': production, 'recommendation_policy': {'generated_after_interpretation': True, 'current_request_authoritative': True, 'multiple_representations_allowed': True, 'multiple_renderer_recommendations_allowed': True, 'scene_recommendation_per_representation': True, 'text_intro_renderer': 'MessageTextBlock', 'text_explanation_renderer': 'MessageTextBlock', 'stale_context_cannot_upgrade_current_representation': True}, 'signals': [x['renderer_signal'] for x in presentation_recommendations], 'recommendations': presentation_recommendations, 'scene_plan': [x['scene_recommendation'] for x in presentation_recommendations]}
        if ascii_schema_advisory:
            presentation['format_advisory'] = {'format': 'ascii', 'scope': 'text_block', 'mode': 'optional', 'reason': 'semantic_text_schema_request'}
        previous_dialogue_state = last_turn_meaning.get('dialogue_state') if isinstance(last_turn_meaning, dict) and isinstance(last_turn_meaning.get('dialogue_state'), dict) else {}
        semantic_context_packet = QuantumDialogueStateEngine.build_next_turn_context(previous_dialogue_state, text, relation='CONTINUE' if sequential_relation == 'CONTINUE' else 'RECALL' if sequential_relation == 'RECALL' else 'NEW', resolved_reference=resolved_reference)
        if sequential_relation == 'CONTINUE':
            semantic_context_packet['previous']['meaning'] = deepcopy(last_turn_meaning)
        semantic_context_packet['current'] = {'request': text, 'operation': p.get('best_operation'), 'object': p.get('best_object'), 'goal': p.get('best_goal'), 'representation': production, 'requested_outputs': list(dict.fromkeys(complete_outputs))}
        if visual_mode == 'diagram':
            complete_outputs = [x for x in complete_outputs if x not in {'image', 'gallery'}]
            if 'diagram' not in complete_outputs:
                complete_outputs.insert(0, 'diagram')
        elif visual_mode == 'image_generation':
            complete_outputs = [x for x in complete_outputs if x not in {'diagram', 'gallery'}]
            if 'image' not in complete_outputs:
                complete_outputs.insert(0, 'image')
        result = build_result(text)
        result['dialogue_trajectory'] = deepcopy(dialogue_trajectory)
        structured_requested = [x for x in complete_outputs if x in REPRESENTATION_UNIVERSE and x != 'number']
        if production and production not in structured_requested:
            structured_requested.insert(0, production)
        scene_blueprint = build_scene_blueprint(
            text=text,
            requested_outputs=complete_outputs,
            scene_composition=scene_composition,
            production_representation=production,
            active_topic=active_topic,
            active_goal=active_goal,
            subject=p.get('best_object') or '',
            semantic_summary=self.normalize(f"{p.get('best_operation', 'answer')}: {p.get('best_object', '')} -> {p.get('best_goal', '')}"),
            entities=entities_understanding.get('current') if isinstance(entities_understanding, dict) else [],
            relations=entities_understanding.get('relations') if isinstance(entities_understanding, dict) else [],
            dimensions=(p.get('request_features', {}) if isinstance(p.get('request_features'), dict) else {}).get('dimensions', {}),
            dialogue={
                'relation': dialogue_vector.get('relation', 'NEW_TOPIC'),
                'continuation': bool(continuation),
                'reference_to_previous': bool(reference),
                'context_dependency': 'continuation' if continuation else 'reference' if reference else 'independent',
                'previous_scene_id': str(resolved_scene.get('scene_id') or '').strip() if isinstance(resolved_scene, dict) else '',
                'resolved_reference': resolved_reference,
            },
            flow_id=state.get('flow_id') if isinstance(state, dict) else '',
        )
        result.update({'type': p['dialogue_best'], 'subtype': production, 'scene_type': scene_blueprint.get('scene_kind') or production, 'normalized': text,
 'required_domains': domains, 'candidate_domains': domains, 'required_representations': list(scene_blueprint['representations']), 'candidate_representations': list(scene_blueprint['representations']), 'requested_representations': list(scene_blueprint['representations']), 'requested_representation': production, 'production_representation': production, 'production_representation_locked': locked, 'scene_blueprint': deepcopy(scene_blueprint), 'scene_representations': list(scene_blueprint['representations']), 'scene_nodes': deepcopy(scene_blueprint['nodes']), 'scene_relations': deepcopy(scene_blueprint['relations']), 'production_representation_source': source, 'production_representation_confidence': max(p['representation_scores'].get(production, 0.0), p['object_scores'].get(production, 0.0), p['goal_scores'].get('visualize' if production in {'graph', 'diagram', 'image', 'gallery'} else 'present', 0.0)), 'visual_production_mode': visual_mode, 'visual_production': deepcopy(p.get('visual_production') or {}), 'image_generation_request': image_generation_request, 'lightweight_visual_request': lightweight_visual_request, 'complex_image_generation': complex_image_generation, 'visual_generation_needed': image_generation_request, 'explicit_visual_generation': image_generation_request, 'explicit_image_generation_only': image_generation_request, 'avoid_image_generation_fallback': False if image_generation_request else True, 'representation_evidence': evidence, 'quantum_representation_measurement': {'measurements': evidence, 'production_representation': production, 'production_representation_locked': locked, 'scene_matrix': matrix}, 'semantic_task': semantic_task, 'context_understanding': context_understanding, 'topic_understanding': topic_understanding, 'entity_understanding': entities_understanding, 'turn_structure_understanding': turn_structure_understanding, 'task_understanding': task_understanding, 'scene_composition': deepcopy(scene_composition), 'visual_production_mode': visual_mode, 'visual_production': deepcopy(p.get('visual_production') or {}), 'image_generation_request': image_generation_request, 'lightweight_visual_request': lightweight_visual_request, 'complex_image_generation': complex_image_generation, 'visual_generation_needed': image_generation_request, 'explicit_visual_generation': image_generation_request, 'explicit_image_generation_only': image_generation_request, 'avoid_image_generation_fallback': False if image_generation_request else True, 'image_generation_transport': 'OPENAI_STRUCTURED_SPEC_TO_C_APRIL_IMAGES_GENERATOR' if image_generation_request else '', 'turn_meaning_transition': deepcopy(transition), 'sequential_dialogue': deepcopy(sequential_dialogue), 'last_turn_meaning': deepcopy(last_turn_meaning or {}), 'last_completed_semantic_state': deepcopy(last_turn_meaning.get('dialogue_state', {}) if isinstance(last_turn_meaning, dict) else {}), 'dialogue_state': deepcopy({'version': QuantumDialogueStateEngine.VERSION, 'current_turn': {'user_request': text, 'operation': p.get('best_operation'), 'object': p.get('best_object'), 'goal': p.get('best_goal'), 'representation': production}, 'previous': deepcopy(semantic_context_packet.get('previous') or {}), 'relation': 'CONTINUE' if sequential_relation == 'CONTINUE' else 'RECALL' if sequential_relation == 'RECALL' else 'NEW', 'resolved_reference': resolved_reference, 'source': 'next_turn_semantic_state'}), 'semantic_context_packet': deepcopy(semantic_context_packet), 'active_dialogue_state': deepcopy(semantic_context_packet.get('previous') or {}), 'previous_response_contract': deepcopy(last_turn_meaning.get('response_contract', {}) if isinstance(last_turn_meaning, dict) else {}), 'topic_owner': topic_owner, 'canonical_topic': normalize_text((dialogue_trajectory.get('active_referent') if sequential_relation == 'CONTINUE' else active_topic) or active_topic), 'semantic_ownership': {'relation': transition_relation or 'NEW_TOPIC', 'owner': topic_owner, 'stale_state_topic_ignored': topic_owner == 'current_request', 'immediate_turn_first': True, 'historical_memory_is_evidence_only': True}, 'scene_graph': {'root': 'current_request', 'parts': deepcopy(scene_composition), 'representation_order': list(scene_blueprint['representations']), 'nodes': deepcopy(scene_blueprint['nodes']), 'relations': deepcopy(scene_blueprint['relations']), 'semantic_source': 'canonical_scene_blueprint'}, 'ascii_schema_advisory': ascii_schema_advisory, 'resolved_scene': resolved_scene, 'reference_resolution': reference_resolution, 'presentation_transport': presentation, 'presentation_signal': presentation, 'presentation_recommendations': presentation_recommendations, 'presentation_signals': presentation['signals'], 'scene_recommendations': [x['scene_recommendation'] for x in presentation_recommendations], 'scene_plan': [x['scene_recommendation'] for x in presentation_recommendations], 'dialogue_memory_window': self._recent_dialogue_pairs(history, limit=10), 'dialogue_vector': {**dict(dialogue_vector or {}), 'canonical_topic': normalize_text((dialogue_trajectory.get('active_referent') if sequential_relation == 'CONTINUE' else active_topic) or active_topic), 'reference_resolution': reference_resolution, 'resolved_reference': resolved_reference, 'resolved_request': resolved_request, 'history_dependent_task': bool(history_task_context.get('required')), 'history_window_size': len(self._recent_dialogue_pairs(history, limit=10)), 'history_task_context': history_task_context, 'requested_outputs': complete_outputs, 'output_segments': task_understanding.get('output_segments', []), 'turn_meaning_transition': deepcopy(transition), 'sequential_dialogue': deepcopy(sequential_dialogue), 'selected_meaning_anchor': transition.get('anchor')}, 'dialogue_delta': {'mode': dialogue_vector.get('delta_mode'), 'shared_tokens': dialogue_vector.get('shared_tokens', []), 'new_tokens': dialogue_vector.get('new_tokens', []), 'avoid_repeat': True}, 'render_continuity': {'mode': 'extend' if continuation else 'start', 'avoid_repeat': True, 'reuse_existing_scene': bool(dialogue_vector.get('reuse_existing_scene')), 'previous_scene_id': dialogue_vector.get('previous_scene_id', ''), 'previous_render_types': dialogue_vector.get('previous_render_types', []), 'previous_block_ids': dialogue_vector.get('previous_block_ids', [])}, 'dialogue_contract': {'dialog_act': d['label'], 'current_request': text, 'continuation': continuation, 'reference_to_previous': reference, 'previous_april_turn': last_a, 'previous_user_turn': last_u, 'reply_to': reply_to, 'active_goal': active_goal, 'active_topic': active_topic, 'canonical_topic': normalize_text(active_topic), 'reference_resolution': reference_resolution, 'resolved_reference': resolved_reference, 'artifact_reference_evidence': bool(dialogue_vector.get('artifact_reference_evidence')), 'artifact_reference_answer': bool(dialogue_vector.get('artifact_reference_answer')), 'visual_scene_similarity': float(dialogue_vector.get('visual_scene_similarity', 0.0) or 0.0), 'resolved_request': resolved_request, 'context_topic': active_topic, 'context_relation': topic_understanding.get('relation'), 'context_reference_entities': [item.get('entity') for item in entities_understanding.get('coreference') or [{}] if isinstance(item, dict) for item in item.get('candidates') or [] if item.get('entity')][:8], 'local_current_turn_structure': local_turn_reference, 'history_dependent_task': bool(history_task_context.get('required')), 'history_task_context': history_task_context, 'requested_outputs': complete_outputs, 'output_segments': task_understanding.get('output_segments', []), 'context_dependency': 'continuation' if dialogue_vector.get('three_way_relation') == 'CONTINUE' else 'recall' if dialogue_vector.get('three_way_relation') == 'RECALL' else 'independent', 'three_way_relation': dialogue_vector.get('three_way_relation') or ('CONTINUE' if continuation else 'RECALL' if reference else 'NEW'), 'selected_memory_operand': dialogue_vector.get('selected_memory_operand') or {}, 'trajectory': deepcopy(dialogue_trajectory), 'relation': dialogue_vector.get('relation', 'NEW_TOPIC'), 'subtype': dialogue_vector.get('subtype', 'NEW_TOPIC'), 'turn_meaning_transition': deepcopy(transition), 'last_turn_meaning': deepcopy(last_turn_meaning or {}), 'avoid_repeat': True, 'canonical': True, 'version': 'quantum_dialogue_field_v4'}, 'context_resolution': {'depends_on_previous_dialogue': bool(continuation or reference or memory or history_task_context.get('required')), 'history_dependent_task': bool(history_task_context.get('required')), 'history_task_context': history_task_context, 'resolved_scene': resolved_scene, 'active_topic': active_topic, 'active_goal': active_goal}, 'semantic_profile': {'active_topic': active_topic, 'active_goal': active_goal, 'context_topic_state': topic_understanding, 'context_entity_state': entities_understanding, 'context_task_state': task_understanding, 'previous_april_turn': last_a, 'representation_scores': p['representation_scores'], 'domain_scores': p['domain_scores'], 'capability_scores': p['capability_scores'], 'operation_scores': p['operation_scores'], 'object_scores': p['object_scores'], 'goal_scores': p['goal_scores'], 'context_scores': p['context_scores'], 'semantic_task': semantic_task, 'history_dependent_task': bool(history_task_context.get('required')), 'history_task_context': history_task_context, 'scene_composition': deepcopy(scene_composition), 'turn_meaning_transition': deepcopy(transition), 'engine': 'quantum_interpretation_engine_v9'}, 'quantum_interpretation_field': {'linguistic': self._linguistic(text), 'dialogue': d, 'representation': evidence, 'domain': [{'domain': k, 'score': float(v)} for k, v in p['domain_scores'].items()], 'context_vectors': p['context_scores'], 'semantic_task': semantic_task, 'production': presentation, 'profile': p, 'scene_matrix': matrix, 'decision_owner': DECISION_OWNER, 'evidence_only': True, 'engine': 'quantum_interpretation_engine_v3'}, 'quantum_matrix': matrix, 'matrix_scene': matrix['best_scene'], 'matrix_confidence': matrix['best_score'], 'decision_owner': DECISION_OWNER, 'routing_owner': DECISION_OWNER, 'renderer_owner': DECISION_OWNER, 'provider_calls': 0, 'canonical_transport': TRANSPORT_NAME, 'semantic_authority': True, 'semantic_decision_source': source, 'representation_resolution': 'task_object_goal', 'legacy_keyword_matching': False, 'avoid_trigger_execution': True, 'machine_only': True, 'single_route': True, 'renderer_intent': production != 'text', 'render_intent': production != 'text', 'prefer_renderer': production != 'text', 'renderer_scene_object': production != 'text', 'visual_routing': production in {'graph', 'diagram', 'image', 'gallery'}, 'possible_capability': 'renderer' if production != 'text' else None, 'possible_output': production, 'possible_scene_type': production, 'current_representation': production, 'unresolved_intent': not locked, 'memory_query': memory, 'continuation': d['continuation_score'], 'continuation_target': last_a or active_topic, 'dialogue_relation': dialogue_vector.get('relation', 'NEW_TOPIC'), 'dialogue_subtype': dialogue_vector.get('subtype', 'NEW_TOPIC'), 'visual_schema': visual_schema, 'visual_schema_confidence': visual_schema_confidence, 'required_capabilities': ['semantic_interpretation', 'dialogue_context'], 'required_outputs': structured_requested or [production], 'requested_outputs': complete_outputs or structured_requested or [production], 'response_mode': 'structured' if production != 'text' else 'talk', 'renderer_first': production != 'text', 'discussion_mode': p['capability_scores'].get('discussion', 0.0) >= 0.6, 'space_discussion': p['capability_scores'].get('space', 0.0) >= 0.6, 'exploration': p['capability_scores'].get('exploration', 0.0), 'web_context': p['capability_scores'].get('web', 0.0), 'explicit_image_generation': p['representation_scores'].get('image', 0.0), 'lightweight_visual': production in {'graph', 'diagram', 'image', 'gallery'}, 'contains_object': bool(text), 'contains_explanation': p['capability_scores'].get('information', 0.0) >= 0.6, 'contains_analysis': p['capability_scores'].get('exploration', 0.0) >= 0.6, 'content_role': 'explanation' if p['capability_scores'].get('information', 0.0) >= 0.6 else 'analysis' if p['capability_scores'].get('exploration', 0.0) >= 0.6 else None, 'artifact_contract': {'contract': 'scene_artifact', 'transport': TRANSPORT_NAME, 'scene_type': production, 'representation': [production], 'decision_owner': DECISION_OWNER}, 'semantic_engine_diagnostics': {'engine': 'quantum_interpretation_engine_v4', 'domain_representation_gates': False, 'capability_representation_gates': False, 'lexical_routing': False, 'token_overlap_context': False, 'production_resolution': 'task_object_goal', 'single_route': True, 'decision_owner': DECISION_OWNER}})
        result['evidence'] = {'representation': evidence, 'domain': [{'domain': k, 'score': float(v)} for k, v in p['domain_scores'].items()], 'math': p['representation_scores'].get('formula', 0.0), 'code': p['representation_scores'].get('code', 0.0), 'web': p['capability_scores'].get('web', 0.0), 'image': p['representation_scores'].get('image', 0.0), 'continuation': d['continuation_score'], 'exploration': p['capability_scores'].get('exploration', 0.0), 'information': p['capability_scores'].get('information', 0.0), 'dialogue': result['dialogue_contract']}
        result['interpretation_state'] = synchronize_interpretation_context(build_interpretation_state(), result)
        result['transport_state'] = export_transport_state(result['interpretation_state'], result)
        result['transport_diagnostics'] = build_transport_diagnostics(result)
        bridge_machine_response(result, result['transport_state'])
        result['estimated_action_count'] = 0
        result['response_complexity'] = None
        result['factory_targets'] = []
        result['factory_order'] = {'owner': DECISION_OWNER, 'status': 'evidence_only'}
        result['scene_strategy'] = {'scene_strategy': 'evidence_only', 'preferred_blocks': [x['representation'] for x in presentation_recommendations if x['representation'] != 'text'] or [production], 'presentation_recommendations': presentation_recommendations, 'scene_recommendations': [x['scene_recommendation'] for x in presentation_recommendations], 'scene_plan': [x['scene_recommendation'] for x in presentation_recommendations], 'scene_composition': deepcopy(scene_composition), 'decision_owner': DECISION_OWNER, 'recommendations_only': True}
        return result
    PRESENTATION_RENDERERS = {'text': 'MessageTextBlock', 'code': 'CodeBlock', 'graph': 'GraphBlock', 'diagram': 'GalleryBlock', 'image': 'GalleryBlock', 'gallery': 'GalleryBlock', 'link': 'LinkCard', 'table': 'TableBlock', 'formula': 'MessageTextBlock', 'file': 'LinkCard', 'audio': 'MessageTextBlock', 'video': 'MessageTextBlock', 'action': 'MessageTextBlock', 'scene': 'GalleryBlock', 'memory': 'MessageTextBlock', 'visual_context': 'GalleryBlock'}
    PRESENTATION_LABELS = {'text': 'textual answer', 'code': 'executable code', 'graph': 'graph/chart', 'diagram': 'diagram or geometric construction', 'image': 'image', 'gallery': 'image gallery', 'link': 'link cards', 'table': 'table', 'formula': 'mathematical notation', 'file': 'file/resource', 'audio': 'audio', 'video': 'video', 'action': 'interactive action', 'scene': 'visual scene', 'memory': 'memory explanation', 'visual_context': 'visual context'}
    PRESENTATION_SCENE_PROFILES = {'text': ('explanation', 'message', 'human-readable answer'), 'code': ('code_example', 'message_intro -> code -> message_explanation', 'source code plus implementation context'), 'graph': ('data_visualization', 'message_intro -> graph -> message_explanation', 'series, axes, labels, units and requested ranges'), 'diagram': ('diagram_or_construction', 'message_intro -> gallery_diagram -> message_explanation', 'nodes/shapes/relations/dimensions and construction facts'), 'image': ('image', 'message_intro -> gallery_image -> message_explanation', 'generated or selected image with visual context'), 'gallery': ('image_collection', 'message_intro -> gallery -> message_explanation', 'ordered image collection with per-image meaning'), 'link': ('resource_links', 'message_intro -> link_cards -> message_explanation', 'URL, title and short purpose for each resource'), 'table': ('structured_data', 'message_intro -> table -> message_explanation', 'rows, columns, headers, units and values'), 'formula': ('mathematical_explanation', 'message_intro -> message_formula -> message_explanation', 'formula plus variable definitions and interpretation'), 'file': ('resource_file', 'message_intro -> link_or_file -> message_explanation', 'resource identity and purpose'), 'audio': ('audio', 'message_intro -> audio_resource -> message_explanation', 'audio resource metadata and purpose'), 'video': ('video', 'message_intro -> video_resource -> message_explanation', 'video resource metadata and purpose'), 'action': ('interactive_action', 'message_intro -> action -> message_explanation', 'action target, parameters and expected result'), 'scene': ('composite_visual_scene', 'message_intro -> visual_scene -> message_explanation', 'scene objects, spatial relations and visual semantics'), 'memory': ('memory_explanation', 'message_intro -> message_explanation', 'resolved prior context'), 'visual_context': ('visual_analysis', 'message_intro -> gallery_context -> message_explanation', 'visual evidence and interpretation')}

    @classmethod
    def _presentation_recommendations(cls, text, profile, production, *, locked=False, continuation=False, previous_scene=None, explicit=None, requested_outputs=None):
        """Return post-interpretation presentation/scene recommendations.

        The current semantic task is authoritative. Evidence may justify zero,
        one, or many additional representations; no renderer-count cap exists.
        """
        profile = profile if isinstance(profile, dict) else {}
        rep_scores = dict(profile.get('representation_scores') or {})
        obj_scores = dict(profile.get('object_scores') or {})
        op_scores = dict(profile.get('operation_scores') or {})
        explicit_values = list(dict.fromkeys((_clean_representation(x) for x in explicit or [] if _clean_representation(x))))
        requested_values = list(dict.fromkeys((_clean_representation(x) for x in requested_outputs or [] if _clean_representation(x))))
        compatible_ops = {'graph': {'build', 'modify', 'present', 'calculate', 'analyze', 'list', 'explain'}, 'diagram': {'build', 'modify', 'present', 'explain'}, 'table': {'build', 'modify', 'present', 'compare', 'list', 'explain'}, 'formula': {'build', 'modify', 'present', 'calculate', 'explain', 'answer'}, 'link': {'retrieve', 'present', 'answer'}, 'code': {'build', 'modify', 'present', 'explain'}, 'image': {'build', 'modify', 'present'}, 'gallery': {'build', 'present'}, 'file': {'retrieve', 'present'}, 'audio': {'build', 'present'}, 'video': {'build', 'present'}, 'action': {'build', 'modify', 'present'}, 'scene': {'build', 'modify', 'present'}, 'memory': {'retrieve', 'answer', 'present'}, 'visual_context': {'answer', 'analyze', 'explain'}}
        op = str(profile.get('best_operation') or 'answer').lower()
        candidates = set(explicit_values)
        candidates.update(requested_values)
        if production:
            candidates.add(production)
        for label, value in rep_scores.items():
            score = float(value or 0.0)
            obj_score = float(obj_scores.get(label, 0.0) or 0.0)
            if label == 'text':
                if score >= 0.14:
                    candidates.add(label)
                continue
            if label in explicit_values or label == production or (op in compatible_ops.get(label, set()) and score >= 0.16 and (obj_score >= 0.07)):
                candidates.add(label)
        if any((x != 'text' for x in candidates)):
            candidates.add('text')
        ordered = [production] if production else []
        ordered += [x for x, _ in sorted(((x, float(rep_scores.get(x, 0.0) or 0.0)) for x in candidates if x != production), key=lambda item: item[1], reverse=True)]
        if 'text' in candidates and 'text' not in ordered:
            ordered.insert(0, 'text')
        ordered = list(dict.fromkeys(ordered))
        scene_id = str(previous_scene.get('scene_id') or '') if isinstance(previous_scene, dict) else ''
        out = []
        for idx, label in enumerate(ordered):
            if label not in REPRESENTATION_UNIVERSE:
                continue
            renderer = cls.PRESENTATION_RENDERERS.get(label, 'MessageTextBlock')
            role, composition, payload = cls.PRESENTATION_SCENE_PROFILES.get(label, cls.PRESENTATION_SCENE_PROFILES['text'])
            continuing_scene = bool(continuation and scene_id and (label != 'text'))
            out.append({'recommendation_id': f'semantic-presentation-{idx + 1}', 'representation': label, 'representation_label': cls.PRESENTATION_LABELS.get(label, label), 'renderer': renderer, 'renderer_signal': {'type': label, 'renderer': renderer, 'web_renderer': renderer, 'viewer': WEB_RENDERER_REGISTRY.get(label, WEB_RENDERER_REGISTRY['text']).get('viewer', renderer), 'fallback_renderer': WEB_RENDERER_REGISTRY.get(label, WEB_RENDERER_REGISTRY['text']).get('fallback_renderer', 'MessageTextBlock'), 'web_registry_version': WEB_RENDERER_REGISTRY_VERSION, 'signal_channel': 'canonical_web_render_signal_v2', 'owner': DECISION_OWNER, 'source': 'QUANTUM_INTERPRETATION_ENGINE', 'evidence_only': True}, 'semantic_basis': {'representation_score': round(float(rep_scores.get(label, 0.0) or 0.0), 6), 'object_score': round(float(obj_scores.get(label, 0.0) or 0.0), 6), 'operation': op, 'goal': str(profile.get('best_goal') or 'understand'), 'is_production_representation': label == production, 'production_locked': bool(locked and label == production), 'explicit_current_request': label in explicit_values}, 'response_role': 'supporting_explanation' if label == 'text' else 'primary_representation', 'scene_recommendation': {'role': role, 'order_hint': 'representation' if label != 'text' else 'narrative', 'composition': composition, 'sequence': [{'role': 'introduction', 'renderer': 'MessageTextBlock', 'content_role': 'request_essence'}, {'role': 'representation', 'renderer': renderer, 'type': label, 'content_role': 'specialized_result'}, {'role': 'explanation', 'renderer': 'MessageTextBlock', 'content_role': 'result_explanation'}] if label != 'text' else [{'role': 'answer', 'renderer': 'MessageTextBlock', 'content_role': 'human_answer'}], 'intro_via': 'MessageTextBlock', 'renderer': renderer, 'explanation_via': 'MessageTextBlock', 'payload_expectation': payload, 'scene_relation': 'continue_existing_scene' if continuing_scene else 'new_scene', 'reuse_scene_id': scene_id if continuing_scene else '', 'avoid_repeat': continuing_scene, 'build_scene_after_semantic_understanding': True, 'independent_scene_recommendation': True}, 'text_guidance': {'introduction': 'Briefly state the essence of the current user request and what this representation will show.', 'explanation': 'Explain the produced result, its main meaning and purpose after the specialized block.'}, 'advisory_only': True})
        return out

    def fast_semantic_profile(self, text, previous_assistant='', previous_user='', active_topic='', active_goal=''):
        return self.measure(text, previous_assistant=previous_assistant, previous_user=previous_user, active_topic=active_topic, active_goal=active_goal)

    def turn_measurement(self, text, previous_assistant='', previous_user='', active_goal='', active_topic=''):
        p = self.measure(text, previous_assistant=previous_assistant, previous_user=previous_user, active_goal=active_goal, active_topic=active_topic)
        return {'linguistic': self._linguistic(text), 'dialogue_nli': {'labels': list(p['dialogue_scores']), 'scores': list(p['dialogue_scores'].values()), 'source': 'quantum_matrix'}, 'representation_nli': {'labels': list(p['representation_scores']), 'scores': list(p['representation_scores'].values()), 'source': 'quantum_matrix'}, 'domain_nli': {'labels': list(p['domain_scores']), 'scores': list(p['domain_scores'].values()), 'source': 'quantum_matrix'}, 'capability_nli': {'labels': list(p['capability_scores']), 'scores': list(p['capability_scores'].values()), 'source': 'quantum_matrix'}, 'embeddings': dict(p['context_scores']), 'decision_owner': DECISION_OWNER, 'evidence_only': True, 'engine': 'quantum_interpretation_turn_engine_v3'}

    def classify(self, text, hypotheses):
        p = self.measure(text)
        merged = {}
        for fam in ('dialogue', 'representation', 'domain', 'capability', 'operation', 'object', 'goal'):
            merged.update(p.get(f'{fam}_scores', {}))
        ranked = sorted(((h, float(merged.get(h, 0.0))) for h in hypotheses), key=lambda x: x[1], reverse=True)
        return {'labels': [x[0] for x in ranked], 'scores': [x[1] for x in ranked], 'source': 'quantum_matrix'}

@dataclass
class SemanticEvidence:
    label: str
    score: float
    source: str
    positive: bool = True
    details: Dict[str, Any] | None = None

    def as_dict(self) -> Dict[str, Any]:
        return {'label': self.label, 'score': max(0.0, min(1.0, float(self.score))), 'source': self.source, 'positive': bool(self.positive), 'details': self.details or {}}

def build_result(text: str) -> dict[str, Any]:
    return {'type': 'text', 'subtype': None, 'scene_type': None, 'normalized': text, 'content_role': None, 'contains_object': bool(text), 'contains_explanation': False, 'contains_analysis': False, 'contains_legend': False, 'scene_composition_ready': True, 'renderer_intent': False, 'discussion_mode': False, 'space_discussion': False, 'lightweight_visual': False, 'exploration': False, 'continuation': False, 'web_context': False, 'explicit_image_generation': False, 'cognition_assisted': True, 'continuity_aware': True, 'scene_aware': True, 'supports_executor': True, 'prefer_renderer': False, 'prefer_guidance': False, 'prefer_execution': False, 'prefer_continuation': False, 'active_topic_slot': None, 'topic_continuity': False, 'avoid_force_generation': True, 'avoid_hidden_escalation': True, 'avoid_telegram_behavior': True, 'avoid_trigger_execution': True, 'provider_safe': True, 'renderer_first': False, 'machine_only': True, 'semantic_bridge': True, 'orchestration_safe': True, 'continuity_preserved': True, 'required_domains': [], 'candidate_domains': [], 'required_representations': [], 'candidate_representations': [], 'domain_confidence': {}, 'response_complexity': None, 'estimated_action_count': 0, 'decision_owner': DECISION_OWNER, 'routing_owner': DECISION_OWNER, 'renderer_owner': DECISION_OWNER, 'provider_calls': 0, 'single_route': True}

def estimate_action_count(result: dict[str, Any]) -> int:
    reps = set(result.get('required_representations', []) or [])
    domains = set(result.get('required_domains', []) or [])
    count = len(reps) + len(domains)
    count += int(bool(result.get('contains_analysis') or result.get('contains_explanation')))
    count += 2 if result.get('explicit_image_generation') else 0
    return max(1, count)

def determine_response_complexity(result: dict[str, Any]) -> str:
    actions = estimate_action_count(result)
    if actions <= 1:
        return RESPONSE_COMPLEXITY_LOW
    if actions <= 3:
        return RESPONSE_COMPLEXITY_MEDIUM
    return RESPONSE_COMPLEXITY_HIGH

def build_factory_order(result: dict[str, Any]) -> dict[str, Any]:
    domains = list(result.get('required_domains', []) or [])
    return {'intent': result.get('type'), 'goal': result.get('subtype'), 'required_domains': domains, 'required_rooms': list(domains), 'required_artifacts': list(result.get('required_representations', []) or []), 'quality_target': 0.95, 'owner': DECISION_OWNER, 'status': 'evidence_only'}

def build_scene_strategy(result: dict[str, Any]) -> dict[str, Any]:
    return {'scene_strategy': 'evidence_only', 'preferred_blocks': list(result.get('required_representations', []) or []), 'content_role': result.get('content_role'), 'scene_priority': 'normal', 'scene_contribution_mode': True, 'scene_builder_profile': 'processor_selected', 'decision_owner': DECISION_OWNER}

def build_interpretation_state() -> dict[str, dict[str, Any]]:
    return {'dialogue': {}, 'evidence': {}, 'cognition': {}, 'scene': {}, 'artifacts': {}, 'executor': {}, 'diagnostics': {}}
INTERPRETATION_TRANSPORT_FIELDS = {'dialogue_profile': ('dialogue', 'profile'), 'semantic_evidence_engine': ('evidence', 'engine'), 'dialogue_cognition_matrix': ('cognition', 'matrix'), 'semantic_dialogue_graph': ('dialogue', 'graph'), 'scene_profile': ('scene', 'profile'), 'artifact_contract': ('artifacts', 'contract'), 'executor_preparation_contract': ('executor', 'contract')}
INTERPRETATION_ROUTE = tuple(INTERPRETATION_TRANSPORT_FIELDS)
INTERPRETATION_ENTRYPOINT = TRANSPORT_NAME
INTERPRETATION_STATE_TEMPLATE = build_interpretation_state()

def safe_result_get(result: Any, key: str, default: Any=None) -> Any:
    if not isinstance(result, dict):
        return default
    value = result.get(key, default)
    return default if value is None else value

def ensure_transport_defaults(state: dict[str, Any] | None) -> dict[str, Any]:
    state = state or {}
    for key in ('dialogue', 'scene', 'executor', 'artifacts', 'diagnostics'):
        state.setdefault(key, {})
    return state

def synchronize_interpretation_context(state: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
    state = ensure_transport_defaults(state)
    state['dialogue']['profile'] = result.get('semantic_profile')
    state['dialogue']['contract'] = result.get('dialogue_contract')
    state['evidence']['engine'] = result.get('quantum_interpretation_field')
    state['scene']['profile'] = result.get('scene_profile')
    state['scene']['matrix'] = result.get('quantum_matrix')
    state['scene']['resolved'] = result.get('resolved_scene')
    state['scene']['presentation'] = result.get('presentation_transport')
    state['artifacts']['contract'] = result.get('artifact_contract')
    state['executor']['contract'] = result.get('executor_preparation_contract')
    return state

def export_transport_state(state: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
    state = ensure_transport_defaults(state)
    for field, (section, key) in INTERPRETATION_TRANSPORT_FIELDS.items():
        if field in result:
            state[section][key] = result[field]
    state.setdefault('presentation', {})
    state['presentation']['transport'] = result.get('presentation_transport')
    state['presentation']['signals'] = list(result.get('presentation_signals') or [])
    state['diagnostics']['route'] = [{'node': node, 'status': 'evidence', 'payload': result.get(node)} for node in INTERPRETATION_ROUTE]
    return state

def resolve_interpretation_payload(result: dict[str, Any]) -> dict[str, Any]:
    return result.get(TRANSPORT_NAME, {}) if isinstance(result, dict) else {}

def propagate_canonical_response(result: dict[str, Any], state: dict[str, Any]) -> dict[str, Any]:
    transport = state.setdefault('transport', {})
    response = transport.setdefault('response', {})
    response['content'] = safe_result_get(result, 'normalized') or safe_result_get(result, 'assistant_response', '')
    return result

def _quantum_scene_projection(scene: dict[str, Any] | None) -> dict[str, Any]:
    scene = scene if isinstance(scene, dict) else {}
    return {'scene_id': scene.get('scene_id'), 'turn_id': scene.get('turn_id'), 'relation': scene.get('relation'), 'topic': scene.get('topic'), 'user_request': scene.get('user_request'), 'answer': scene.get('answer'), 'summary': scene.get('summary'), 'semantic_state': scene.get('semantic_state') or {}, 'render_blocks': scene.get('render_blocks') or [], 'presentation_signals': scene.get('presentation_signals') or [], 'presentation_types': scene.get('presentation_types') or [], 'renderer_state': scene.get('renderer_state') or {}}

def bridge_machine_response(result: dict[str, Any], state: dict[str, Any]) -> dict[str, Any]:
    machine = state.setdefault('machine_response', {})
    scene = state.setdefault('scene_contract', {})
    content = machine.get('content') or result.get('normalized') or result.get('assistant_response', '')
    machine['content'] = content
    scene.update({'content': content, 'answer': content, 'summary': content})
    if isinstance(result.get('resolved_scene'), dict):
        scene['resolved_scene'] = _quantum_scene_projection(result.get('resolved_scene'))
    if isinstance(result.get('presentation_transport'), dict):
        scene['presentation_transport'] = result.get('presentation_transport')
    result['machine_response'] = machine
    result['scene_contract'] = scene
    return result

def validate_response_complexity(result: dict[str, Any]) -> dict[str, Any]:
    complexity = result.get('response_complexity') or RESPONSE_COMPLEXITY_LOW
    result['response_complexity'] = complexity
    result['estimated_action_count'] = result.get('estimated_action_count') or 0
    result['semantic_response_complexity'] = complexity
    result['machine_response_complexity'] = complexity
    return result

def export_response_complexity(result: dict[str, Any]) -> dict[str, Any]:
    return {key: result.get(key) for key in ('response_complexity', 'estimated_action_count', 'semantic_response_complexity', 'machine_response_complexity')}

def build_transport_diagnostics(result: dict[str, Any]) -> dict[str, Any]:
    return {'has_transport': bool(result.get(TRANSPORT_NAME)), 'has_machine_response': bool(result.get('machine_response')), 'has_scene_contract': bool(result.get('scene_contract')), 'normalized': bool(result.get('normalized')), 'decision_owner': result.get('decision_owner'), 'provider_calls': result.get('provider_calls', 0)}

def build_interpretation_route(state: dict[str, Any], result: dict[str, Any]):
    state = export_transport_state(state, result)
    return state['diagnostics']['route']
QUANTUM_INTERPRETATION_ENGINE = QuantumInterpretationEngine()
QUANTUM_CONTEXT_ENGINE = QuantumContextUnderstandingEngine(QUANTUM_INTERPRETATION_ENGINE)
QUANTUM_SEQUENTIAL_DIALOGUE_ENGINE = QuantumSequentialDialogueEngine()
QUANTUM_FAST_SEMANTIC = QUANTUM_INTERPRETATION_ENGINE
QUANTUM_LINGUISTIC_ENGINE = QUANTUM_INTERPRETATION_ENGINE
QUANTUM_EMBEDDING_ENGINE = QUANTUM_INTERPRETATION_ENGINE
QUANTUM_INTENT_ENGINE = QUANTUM_INTERPRETATION_ENGINE
QUANTUM_EVIDENCE_FUSION = QUANTUM_INTERPRETATION_ENGINE
QUANTUM_DIALOGUE_ENGINE = QUANTUM_INTERPRETATION_ENGINE
QUANTUM_TURN_MEANING_ENGINE = QuantumTurnMeaningEngine()

def build_turn_meaning_state(user_request: str, answer: str, *, render_blocks: list[dict[str, Any]] | None=None, summary: str='', turn_id: Any=None, scene_id: str='') -> dict[str, Any]:
    """Build the persistent semantic meaning of a completed USER→APRIL turn."""
    return QUANTUM_TURN_MEANING_ENGINE.build(user_request, answer, render_blocks=render_blocks, summary=summary, turn_id=turn_id, scene_id=scene_id, semantic_engine=QUANTUM_INTERPRETATION_ENGINE)

def compare_request_to_turn_meaning(current_request: str, turn_meaning: dict[str, Any] | None) -> dict[str, Any]:
    """Compare a new request with the meaning of the immediately previous turn."""
    return QUANTUM_TURN_MEANING_ENGINE.compare(current_request, turn_meaning, semantic_engine=QUANTUM_INTERPRETATION_ENGINE)
QuantumFastSemanticEngine = QuantumInterpretationEngine
QuantumLinguisticEngine = QuantumInterpretationEngine
QuantumEmbeddingEngine = QuantumInterpretationEngine
QuantumIntentEngine = QuantumInterpretationEngine
QuantumEvidenceFusionEngine = QuantumInterpretationEngine
QuantumDialogueEngine = QuantumInterpretationEngine
QuantumSceneInterpretationMatrix = QuantumInterpretationEngine

class QuantumMemoryUnderstandingEngine:
    """Parallel analysis of dialogue memory and visual-response memory.

    Evidence-only: it never routes, selects, rewrites, or creates renderer
    signals. It reconstructs relevant prior visual context for the existing
    Quantum Processor so the next response can be a new artifact carrying the
    meaning/schema of the previous visual response.
    """
    VERSION = 'QUANTUM-MEMORY-UNDERSTANDING-V1'
    MAX_DIALOG_TURNS = 6
    MAX_VISUAL_BLOCKS = 4
    MAX_VISUAL_HISTORY = 4

    @staticmethod
    def _text(value):
        return str(value or '').strip()

    @staticmethod
    def _compact(value, depth=0):
        if depth > 3 or value in (None, '', [], {}):
            return None
        if isinstance(value, (str, int, float, bool)):
            return value
        if isinstance(value, dict):
            out = {}
            for key, item in list(value.items())[:24]:
                compacted = QuantumMemoryUnderstandingEngine._compact(item, depth + 1)
                if compacted not in (None, '', [], {}):
                    out[str(key)] = compacted
            return out
        if isinstance(value, (list, tuple)):
            out = []
            for item in list(value)[:24]:
                compacted = QuantumMemoryUnderstandingEngine._compact(item, depth + 1)
                if compacted not in (None, '', [], {}):
                    out.append(compacted)
            return out
        return str(value)

    @classmethod
    def _dialogue_text(cls, history):
        result = []
        if not isinstance(history, list):
            return result
        for item in history[-cls.MAX_DIALOG_TURNS:]:
            if not isinstance(item, dict):
                continue
            role = cls._text(item.get('role')).lower()
            content = cls._text(item.get('content') or item.get('text') or item.get('answer'))
            if role and content:
                result.append(f'{role}: {content}')
        return result

    @classmethod
    def _visual_candidates(cls, visual_context):
        if not isinstance(visual_context, dict):
            return []
        candidates = []
        active = visual_context.get('active_visual_scene')
        if isinstance(active, dict):
            candidates.append(active)
        history = visual_context.get('visual_scene_history') or []
        if isinstance(history, list):
            candidates.extend((x for x in history[-cls.MAX_VISUAL_HISTORY:] if isinstance(x, dict)))
        result, seen = ([], set())
        for scene in candidates:
            sid = cls._text(scene.get('scene_id') or scene.get('id'))
            key = sid or str(sorted(((str(k), str(v)) for k, v in list(scene.items())[:8])))
            if key in seen:
                continue
            seen.add(key)
            result.append(scene)
        return result

    @classmethod
    def _extract_visual_schema(cls, scene):
        blocks = scene.get('render_blocks') or scene.get('blocks') or []
        structured = []
        if isinstance(blocks, list):
            for block in blocks[:cls.MAX_VISUAL_BLOCKS]:
                if not isinstance(block, dict):
                    continue
                kind = cls._text(block.get('type') or block.get('artifact_type') or block.get('representation')).lower()
                if not kind or kind in {'text', 'markdown'}:
                    continue
                payload = block.get('payload')
                if not isinstance(payload, dict):
                    artifact = block.get('artifact')
                    payload = artifact.get('payload') if isinstance(artifact, dict) else None
                if not isinstance(payload, dict):
                    candidate = block.get(kind)
                    payload = candidate if isinstance(candidate, dict) else {}
                structured.append({'type': kind, 'renderer': cls._text(block.get('renderer')), 'viewer': cls._text(block.get('viewer')), 'block_id': cls._text(block.get('block_id')), 'payload': cls._compact(payload)})
        return {'scene_id': cls._text(scene.get('scene_id') or scene.get('id')), 'topic': cls._text(scene.get('topic') or scene.get('user_request') or scene.get('current_request')), 'user_request': cls._text(scene.get('user_request') or scene.get('current_request')), 'answer': cls._text(scene.get('april_answer') or scene.get('answer') or scene.get('content')), 'summary': cls._text(scene.get('summary')), 'render_block_types': [cls._text(x).lower() for x in scene.get('render_block_types') or [] if cls._text(x)], 'presentation_types': [cls._text(x).lower() for x in scene.get('presentation_types') or [] if cls._text(x)], 'render_blocks': structured, 'semantic_state': cls._compact(scene.get('semantic_state') or {})}

    def analyze(self, current_request, *, dialogue_memory=None, visual_memory=None, interpretation=None, dynamic_memory=None):
        current_request = self._text(current_request)
        dialogue_memory = dialogue_memory if isinstance(dialogue_memory, dict) else {}
        visual_memory = visual_memory if isinstance(visual_memory, dict) else {}
        interpretation = interpretation if isinstance(interpretation, dict) else {}
        dynamic_memory = dynamic_memory if isinstance(dynamic_memory, dict) else {}
        dialogue_vector = interpretation.get('dialogue_vector') if isinstance(interpretation.get('dialogue_vector'), dict) else {}
        dialogue_contract = interpretation.get('dialogue_contract') if isinstance(interpretation.get('dialogue_contract'), dict) else {}
        relation = self._text(dialogue_vector.get('relation') or dialogue_contract.get('relation')).upper()
        three_way = self._text(dialogue_vector.get('three_way_relation') or dialogue_contract.get('three_way_relation')).upper()
        continuation = bool(dialogue_vector.get('continuation') or dialogue_contract.get('continuation') or relation in {'CONTINUE_TOPIC', 'CONTINUATION'} or (three_way == 'CONTINUE'))
        reference = bool(dialogue_vector.get('reference_to_previous') or dialogue_contract.get('reference_to_previous') or relation == 'ARTIFACT_REFERENCE' or (three_way == 'RECALL'))
        selected_memory_operand = dialogue_vector.get('selected_memory_operand')
        if not isinstance(selected_memory_operand, dict):
            selected_memory_operand = {}
        candidates = self._visual_candidates(visual_memory)
        schemas = [self._extract_visual_schema(scene) for scene in candidates]
        active_schema = schemas[0] if schemas else {}
        current_rep = self._text(interpretation.get('production_representation') or interpretation.get('requested_representation') or interpretation.get('scene_type')).lower()
        prior_types = set(active_schema.get('render_block_types') or [])
        compare = [active_schema[k] for k in ('topic', 'user_request', 'answer') if active_schema.get(k)]
        similarity = QUANTUM_EMBEDDING_ENGINE.similarities(current_request, compare) if compare else {}
        relevance = max((float(similarity.get(value, 0.0)) for value in compare), default=0.0)
        related_visual = bool(active_schema and (continuation or reference or current_rep in prior_types or (relevance >= 0.35)))
        selected = active_schema if related_visual else {}
        prior_data = []
        for block in (selected.get('render_blocks') or [])[:self.MAX_VISUAL_BLOCKS]:
            if isinstance(block, dict) and isinstance(block.get('payload'), dict):
                prior_data.append({'type': block.get('type'), 'renderer': block.get('renderer'), 'block_id': block.get('block_id'), 'payload': block.get('payload')})
        return {'engine': self.VERSION, 'version': self.VERSION, 'decision_owner': DECISION_OWNER, 'evidence_only': True, 'lexical_triggers': False, 'score_routing': False, 'parallel_memory_channels': False, 'single_dialogue_owner': True, 'dialogue_memory': {'history_present': bool(self._dialogue_text(dialogue_memory.get('history'))), 'recent_turns': self._dialogue_text(dialogue_memory.get('history')), 'active_topic': self._text(dialogue_contract.get('active_topic') or interpretation.get('active_topic')), 'active_goal': self._text(dialogue_contract.get('active_goal') or interpretation.get('active_goal')), 'relation': relation, 'three_way_relation': three_way or ('CONTINUE' if continuation else 'RECALL' if reference else 'NEW'), 'continuation': continuation, 'reference_to_previous': reference, 'selected_memory_operand': selected_memory_operand}, 'visual_memory': {'available': bool(active_schema), 'related': related_visual, 'relevance': round(relevance, 6), 'selected_scene_id': selected.get('scene_id') if selected else '', 'schema': selected, 'prior_render_types': sorted(prior_types), 'prior_structured_blocks': prior_data}, 'memory_reconstruction': {'current_request': current_request, 'dialogue_meaning': self._text(dialogue_contract.get('resolved_request') or dialogue_contract.get('current_request') or current_request), 'visual_reference': 'previous_visual_response' if related_visual else 'none', 'semantic_link': 'continuation' if three_way == 'CONTINUE' else 'recall' if three_way == 'RECALL' else 'independent', 'selected_memory_operand': selected_memory_operand, 'context_available': bool(dialogue_memory.get('history') or active_schema or dynamic_memory.get('matches') or selected_memory_operand), 'relevant_dynamic_memory_count': len(dynamic_memory.get('matches') or [])}, 'generation_intent': {'requested_representation': current_rep or None, 'create_new_visual_artifact': bool(related_visual and current_rep in STRUCTURED_REPRESENTATIONS), 'preserve_meaning_from_previous_visual': bool(related_visual)}}
QUANTUM_MEMORY_UNDERSTANDING_ENGINE = QuantumMemoryUnderstandingEngine()

def normalize_text(text: Any) -> str:
    return QUANTUM_INTERPRETATION_ENGINE.normalize(text)

def normalize_lower(text: Any) -> str:
    return normalize_text(text).lower()

def contains_any(text: str, words: Sequence[str]) -> bool:
    tokens = set(QUANTUM_INTERPRETATION_ENGINE._tokens(normalize_text(text)))
    return bool(tokens & {normalize_lower(x) for x in words})

def _semantic_evidence_stub(kind: str, text: str) -> bool:
    return contains_any(text, (kind,))

def detect_domain_candidates(text: str):
    return [x['domain'] for x in QUANTUM_INTERPRETATION_ENGINE.domains(text)['measurements'] if float(x['score']) >= 0.45]

def build_domain_confidence(text: str):
    return {x['domain']: round(float(x['score']), 4) for x in QUANTUM_INTERPRETATION_ENGINE.domains(text)['measurements'] if float(x['score']) >= 0.2}

def _capability_scores(text: str) -> dict[str, float]:
    return QUANTUM_INTERPRETATION_ENGINE.measure(text)['capability_scores']

def measure_representation_evidence(text: str) -> list[dict[str, Any]]:
    return [SemanticEvidence(x['type'], float(x['score']), 'quantum_matrix').as_dict() for x in QUANTUM_INTERPRETATION_ENGINE.representations(text)['measurements']]

def detect_representation_candidates(text: str):
    return [x['label'] for x in measure_representation_evidence(text) if float(x['score']) >= 0.45]

def semantic_evidence_math(text: str) -> float:
    return QUANTUM_INTERPRETATION_ENGINE.measure(text)['representation_scores'].get('formula', 0.0)

def semantic_evidence_renderer(text: str) -> float:
    return max(QUANTUM_INTERPRETATION_ENGINE.measure(text)['representation_scores'].values(), default=0.0)

def semantic_evidence_image(text: str) -> float:
    return QUANTUM_INTERPRETATION_ENGINE.measure(text)['representation_scores'].get('image', 0.0)

def semantic_evidence_exploration(text: str) -> float:
    return _capability_scores(text).get('exploration', 0.0)

def semantic_evidence_continuation(text: str, previous_assistant: str='') -> float:
    return QUANTUM_INTERPRETATION_ENGINE.dialogue(text, previous_assistant=previous_assistant)['dialogue']['continuation_score']

def semantic_evidence_web(text: str) -> float:
    return _capability_scores(text).get('web', 0.0)

def semantic_evidence_code(text: str) -> float:
    return _capability_scores(text).get('code', 0.0)

def semantic_evidence_information(text: str) -> float:
    return _capability_scores(text).get('information', 0.0)

def detect_discussion_mode(text: str) -> float:
    return _capability_scores(text).get('discussion', 0.0)

def detect_space_discussion(text: str) -> float:
    return _capability_scores(text).get('space', 0.0)

def detect_lightweight_visual(text: str) -> float:
    scores = QUANTUM_INTERPRETATION_ENGINE.measure(text)['representation_scores']
    return max(scores.get('image', 0.0), scores.get('diagram', 0.0), scores.get('graph', 0.0))

def detect_scene_type(text: str, cognition=None):
    cognition = cognition if isinstance(cognition, dict) else {}
    required = [str(x).lower() for x in cognition.get('required_representations', ()) or ()]
    return required[0] if required else QUANTUM_INTERPRETATION_ENGINE.measure(text)['scene_matrix']['best_scene']

def _is_micro_social_turn(text: Any) -> bool:
    p = QUANTUM_INTERPRETATION_ENGINE.measure(normalize_text(text))
    return bool(p['fast_social'] and len(normalize_text(text).split()) <= 24)

def _semantic_identity_request(text: Any) -> bool:
    return bool(QUANTUM_INTERPRETATION_ENGINE.measure(normalize_text(text))['identity_request'])

def _dialogue_signal_contract(text: str, history: list, state: dict, semantic: dict, cognition: dict | None=None, precomputed_profile: dict[str, Any] | None=None):
    cognition = cognition if isinstance(cognition, dict) else {}
    state = state if isinstance(state, dict) else {}
    semantic = semantic if isinstance(semantic, dict) else {}
    previous_assistant, previous_user, reply_to = QUANTUM_INTERPRETATION_ENGINE._history(history)
    active_goal = normalize_text(state.get('active_goal') or state.get('current_goal') or semantic.get('active_goal') or cognition.get('active_goal'))
    active_topic = normalize_text(state.get('active_topic') or state.get('current_topic') or semantic.get('current_topic') or cognition.get('active_topic'))
    measured = QUANTUM_INTERPRETATION_ENGINE.dialogue(text, previous_assistant=previous_assistant, previous_user=previous_user, active_goal=active_goal, active_topic=active_topic)
    d = measured['dialogue']
    continuation = bool(previous_assistant and (d['label'] in {'continuation', 'reformulation', 'correction', 'reference', 'affirmation', 'rejection'} or d['continuation_score'] >= 0.72))
    return {'dialog_act': d['label'], 'current_request': text, 'continuation': continuation, 'reference_to_previous': bool(previous_assistant and d['reference_score'] >= 0.6), 'previous_april_turn': previous_assistant, 'previous_user_turn': previous_user, 'reply_to': reply_to, 'active_goal': active_goal, 'active_topic': active_topic, 'topic_score': d['topic_score'], 'goal_score': d['goal_score'], 'continuation_score': d['continuation_score'], 'reference_score': d['reference_score'], 'topic_shift': bool(active_topic and (not continuation) and (d['topic_score'] < 0.35)), 'history_available': bool(history), 'turn_count': len(history), 'semantic_measurement': measured, 'confidence': d['confidence'], 'decision_owner': DECISION_OWNER, 'evidence_only': True, 'canonical': True}

def _semantic_context_packet(text: str, history: list, state: dict, semantic: dict, cognition: dict) -> dict[str, Any]:
    result = QUANTUM_INTERPRETATION_ENGINE.interpret(text, cognition=cognition, semantic=semantic, history=history, state=state)
    return result.get('quantum_interpretation_field', {})

def _base_interpret_request(text, cognition=None, semantic=None, history=None, state=None):
    return interpret_request(text, cognition, semantic, history, state)

def interpret_request(text, cognition=None, semantic=None, history=None, state=None):
    return QUANTUM_INTERPRETATION_ENGINE.interpret(text, cognition=cognition, semantic=semantic, history=history, state=state)

def build_semantic_dialog_profile(text, cognition=None, semantic=None, assistant_response=None, dialogue_history=None, vision_context=None):
    cognition = cognition or {}
    semantic = semantic or {}
    return {'input_text': text, 'assistant_response': assistant_response, 'dialogue_history': dialogue_history or [], 'vision_context': vision_context or {}, 'active_goal': cognition.get('active_goal') or semantic.get('active_goal'), 'active_topic': cognition.get('active_topic_slot') or semantic.get('current_topic'), 'semantic_state': semantic, 'requires_scene_builder': False, 'profile_version': 'quantum_matrix_v2'}

def build_scene_construction_profile(semantic_profile):
    return {'requires_scene_builder': False, 'scene_type': 'dialogue', 'dialogue_mode': 'semantic_unified', 'context_source': 'quantum_matrix', 'decision_owner': DECISION_OWNER, 'profile_version': 'quantum_matrix_v2'}

def build_scene_artifact_contract(semantic_profile, scene_profile):
    return {'contract': 'scene_artifact', 'transport': TRANSPORT_NAME, 'semantic_profile': semantic_profile or {}, 'scene_profile': scene_profile or {}, 'representation': 'processor_decides', 'profile_version': 'quantum_matrix_v2'}

def build_unified_scene_context(semantic_profile, scene_profile, artifact_contract, voice_context=None, vision_context=None, gallery_context=None, file_context=None, assistant_response=None, dialogue_history=None, memory_state=None):
    return {'semantic_profile': semantic_profile or {}, 'scene_profile': scene_profile or {}, 'artifact_contract': artifact_contract or {}, 'voice_context': voice_context or {}, 'vision_context': vision_context or {}, 'gallery_context': gallery_context or {}, 'file_context': file_context or {}, 'assistant_response': assistant_response, 'dialogue_history': dialogue_history or [], 'active_goal': (semantic_profile or {}).get('active_goal'), 'active_scene': (scene_profile or {}).get('scene_type', 'dialogue'), 'memory_state': memory_state or {}, 'continuity_state': {'single_route': True, 'transport': TRANSPORT_NAME, 'scene_contract': 'canonical'}, 'profile_version': 'quantum_matrix_v2'}

def build_scene_execution_plan(semantic_profile, scene_profile, artifact_contract, unified_scene_context=None):
    context = unified_scene_context or build_unified_scene_context(semantic_profile, scene_profile, artifact_contract)
    return {'transport': TRANSPORT_NAME, 'scene_contract': 'canonical', 'scene_context': context, 'scene_type': (scene_profile or {}).get('scene_type', 'dialogue'), 'representation': 'processor_decides', 'execution_mode': 'single_quantum_matrix_pipeline', 'decision_owner': DECISION_OWNER, 'profile_version': 'quantum_matrix_v2'}

def build_unified_interpretation_state(scene_context, processor_state=None):
    return {'transport': TRANSPORT_NAME, 'scene_context': scene_context or {}, 'processor_state': processor_state or {}, 'dialogue_vector': (scene_context or {}).get('dialogue_history', []), 'assistant_response': (scene_context or {}).get('assistant_response'), 'voice_context': (scene_context or {}).get('voice_context', {}), 'vision_context': (scene_context or {}).get('vision_context', {}), 'gallery_context': (scene_context or {}).get('gallery_context', {}), 'file_context': (scene_context or {}).get('file_context', {}), 'active_goal': (scene_context or {}).get('active_goal'), 'active_scene': (scene_context or {}).get('active_scene'), 'executor_mode': 'single_scene_contract', 'profile_version': 'quantum_matrix_v2'}

def build_semantic_processor_state(interpretation_state, execution_plan=None):
    state = interpretation_state or {}
    return {'transport': TRANSPORT_NAME, 'processor_contract': 'canonical', 'interpretation_state': state, 'execution_plan': execution_plan or {}, 'semantic_inputs': {'text': state.get('scene_context', {}).get('semantic_profile', {}).get('input_text'), 'voice': state.get('voice_context', {}), 'images': state.get('vision_context', {}), 'gallery': state.get('gallery_context', {}), 'files': state.get('file_context', {}), 'assistant': state.get('assistant_response'), 'history': state.get('dialogue_vector', [])}, 'scene_understanding': {'active_scene': state.get('active_scene'), 'active_goal': state.get('active_goal'), 'continuity': True, 'single_route': True}, 'profile_version': 'quantum_matrix_v2'}

def build_dialogue_understanding_core(processor_state, executor_state=None):
    inputs = (processor_state or {}).get('semantic_inputs', {})
    return {'transport': TRANSPORT_NAME, 'dialogue_understanding': {'user_text': inputs.get('text'), 'voice': inputs.get('voice'), 'images': inputs.get('images'), 'gallery': inputs.get('gallery'), 'files': inputs.get('files'), 'assistant_response': inputs.get('assistant'), 'dialogue_history': inputs.get('history', []), 'scene_understanding': (processor_state or {}).get('scene_understanding', {})}, 'processor_reasoning': {'single_scene': True, 'history_aware': True, 'response_context': True, 'executor_shared_context': executor_state or {}}, 'profile_version': 'quantum_matrix_v2'}

def optimize_dialogue_understanding(dialogue_core):
    return {'transport': TRANSPORT_NAME, 'dialogue_understanding': (dialogue_core or {}).get('dialogue_understanding', {}), 'optimization': {'semantic_priority': ['current_request', 'active_goal', 'dialogue_history', 'multimodal_context'], 'multi_evidence': True, 'response_continuity': True, 'scene_consistency': True, 'executor_alignment': True}, 'canonical_reasoning': {'single_scene': True, 'single_contract': True, 'single_transport': True, 'preserve_dialogue_vector': True}, 'profile_version': 'quantum_matrix_v2'}

def build_semantic_interpretation_contract(dialogue_optimization):
    return {'transport': TRANSPORT_NAME, 'semantic_contract': {'mode': 'canonical_semantic', 'single_scene': True, 'single_dialogue': True, 'single_processor': True, 'single_executor': True}, 'dialogue_optimization': dialogue_optimization or {}, 'reasoning_policy': {'current_request_authoritative': True, 'multimodal_fusion': True, 'multi_evidence': True, 'trigger_independent': True, 'scene_continuity': True}, 'profile_version': 'quantum_matrix_v2'}

def build_canonical_semantic_runtime(semantic_contract, processor_state, dialogue_core):
    dialogue = (dialogue_core or {}).get('dialogue_understanding', {})
    return {'transport': TRANSPORT_NAME, 'scene': dialogue.get('scene_understanding', {}), 'dialogue': dialogue, 'processor': processor_state or {}, 'reasoning_policy': (semantic_contract or {}).get('reasoning_policy', {}), 'continuity_vector': {'history': dialogue.get('dialogue_history', []), 'assistant': dialogue.get('assistant_response'), 'goal': dialogue.get('scene_understanding', {}).get('active_goal')}, 'compatibility': {'enabled': False, 'trigger_execution': False, 'keyword_matching': False}, 'profile_version': 'quantum_matrix_v2'}

def fuse_semantic_inputs(runtime_state):
    runtime_state = runtime_state or {}
    inputs = dict(runtime_state.get('input_sources', {}))
    continuity = runtime_state.get('continuity_vector', {})
    return {'transport': TRANSPORT_NAME, 'scene': runtime_state.get('scene', {}), 'goal': continuity.get('goal'), 'history': continuity.get('history', []), 'assistant_response': continuity.get('assistant'), 'modalities': {k: inputs.get(k) for k in ('text', 'voice', 'images', 'gallery', 'files')}, 'semantic_state': {'single_route': True, 'multimodal_fusion': True, 'legacy_trigger_enabled': False, 'context_complete': True}, 'available_modalities': [k for k, v in inputs.items() if v not in (None, {}, [], '')], 'profile_version': 'quantum_matrix_v2'}

def build_processor_execution_context(runtime_state):
    fused = fuse_semantic_inputs(runtime_state or {})
    return {'transport': TRANSPORT_NAME, 'semantic_context': fused, 'executor_context': fused, 'processor_context': fused, 'decision_owner': DECISION_OWNER, 'profile_version': 'quantum_matrix_v2'}
SEMANTIC_EVIDENCE_PRIORITY = ('current_request', 'active_goal', 'dialogue_history', 'voice_context', 'vision_context', 'gallery_context', 'file_context', 'semantic_profile')
LEGACY_TRIGGER_FLAGS = ()
CANONICAL_SEMANTIC_RUNTIME = {'transport': TRANSPORT_NAME, 'reasoning': 'quantum_matrix', 'legacy_trigger_execution': False, 'single_scene': True, 'single_processor': True, 'single_executor': True}
SEMANTIC_INTERPRETATION_CORE = {'decision_source': DECISION_OWNER, 'routing': 'processor_owned', 'legacy_mode': 'isolated', 'scene_contract': 'artifact_first', 'executor_contract': 'advisory_only', 'history_model': 'evidence_based', 'confidence_policy': 'multi_evidence'}
SEMANTIC_PIPELINE = INTERPRETATION_ROUTE

def _runtime_ready_guard() -> None:
    return None

def _ensure_semantic_runtime() -> None:
    return None

def preload_semantic_runtime() -> None:
    return None

def start_semantic_accelerator() -> None:
    return None

def _ensure_nli_runtime() -> None:
    return None

def _lightweight_linguistic(text: str) -> Dict[str, Any]:
    return QUANTUM_INTERPRETATION_ENGINE._linguistic(normalize_text(text))

def _stanza_lang_ready(lang: str) -> bool:
    return False

def _stanza_resources_ready() -> bool:
    return False

def _provision_stanza_resources() -> None:
    return None
