# === file: canvas_formatter.py ===

def format_code_block(content, file_name=None, block_name=None):
    header = ""

    if file_name:
        header += f"# === file: {file_name} ===\n"
    if block_name:
        header += f"# === block: {block_name} ===\n\n"

    return f"{header}{content}"


def format_text(content):
    if not content:
        return content

    # убираем лишние пробелы и переносы
    return content.strip()
