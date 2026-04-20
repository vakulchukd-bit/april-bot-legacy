# blocks/image_utils.py

from PIL import Image
import io


def compress_image(image_bytes, max_size=1024, quality=80):
    """
    Уменьшает размер изображения:
    - ресайз по максимальной стороне
    - конвертация в JPEG
    - сжатие качества
    """

    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")

    # ===== RESIZE =====
    width, height = img.size
    max_dim = max(width, height)

    if max_dim > max_size:
        ratio = max_size / max_dim
        new_size = (int(width * ratio), int(height * ratio))
        img = img.resize(new_size, Image.LANCZOS)

    # ===== COMPRESS =====
    buffer = io.BytesIO()
    img.save(buffer, format="JPEG", quality=quality, optimize=True)

    return buffer.getvalue()
