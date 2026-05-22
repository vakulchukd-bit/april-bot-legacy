# === file: canvas_formatter.py ===

# =====================================================
# 🧠 APRIL CANVAS FORMATTER
# =====================================================

"""
Canvas formatter April.

Этот слой:

- НЕ telegram formatter;
- НЕ personality layer;
- НЕ beautifier.

Он:

- подготавливает scene objects;
- передаёт semantic render blocks;
- помогает web-space renderer;
- сохраняет object continuity.

Canvas formatter —
это bridge между
April cognition
и April Space.
"""

# =====================================================
# 🔥 CODE BLOCK
# =====================================================

def format_code_block(
    content,
    file_name=None,
    block_name=None
):

    header = ""

    if file_name:

        header += (
            f"# === file: "
            f"{file_name} ===\n"
        )

    if block_name:

        header += (
            f"# === block: "
            f"{block_name} ===\n\n"
        )

    return f"{header}{content}"


# =====================================================
# 🔥 TEXT
# =====================================================

def format_text(content):

    if not content:
        return content

    return content.strip()


# =====================================================
# 🔥 FORMULA BLOCK
# =====================================================

def format_formula_block(
    formula,
    label="FORMULA"
):

    formula = (
        formula or ""
    ).strip()

    if not formula:

        return ""

    return (
        f"[[formula]]\n"
        f"label={label}\n"
        f"content={formula}\n"
        f"[[/formula]]"
    )


# =====================================================
# 🔥 GRAPH BLOCK
# =====================================================

def format_graph_block(
    graph,
    title="GRAPH"
):

    graph = (
        graph or ""
    ).strip()

    if not graph:

        return ""

    return (
        f"[[graph]]\n"
        f"title={title}\n"
        f"content={graph}\n"
        f"[[/graph]]"
    )


# =====================================================
# 🔥 SCENE OBJECT
# =====================================================

def format_scene_object(
    object_type,
    content="",
    meta=None
):

    object_type = (
        object_type or ""
    ).strip()

    content = (
        content or ""
    ).strip()

    meta = meta or {}

    if not object_type:
        return ""

    lines = [

        f"[[{object_type}]]"
    ]

    for key, value in meta.items():

        lines.append(
            f"{key}={value}"
        )

    if content:

        lines.append(
            f"content={content}"
        )

    lines.append(
        f"[[/{object_type}]]"
    )

    return "\n".join(lines)
