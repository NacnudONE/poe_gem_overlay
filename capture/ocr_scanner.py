from PIL import Image
from capture.windows_ocr import ocr as win_ocr


def preprocess(image: Image.Image) -> Image.Image:
    """Збільшує зображення — Windows OCR краще читає великий текст."""
    w, h = image.size
    return image.resize((w * 2, h * 2), Image.LANCZOS)


def scan(image: Image.Image) -> list[str]:
    """
    Запускає OCR на зображенні через Windows вбудований двигун.
    Повертає список рядків тексту (без порожніх і коротких).
    """
    processed = preprocess(image)
    raw_text = win_ocr(processed)

    lines = []
    for line in raw_text.splitlines():
        cleaned = line.strip()
        if len(cleaned) >= 3 and any(c.isalpha() for c in cleaned):
            lines.append(cleaned)

    return lines


def get_brightness(image: Image.Image) -> float:
    """Повертає середню яскравість зображення (0-255)."""
    gray = image.convert("L")
    pixels = list(gray.getdata())
    return sum(pixels) / len(pixels) if pixels else 0


# --- Тест ---
if __name__ == "__main__":
    import sys
    from capture.screen_capture import calibrate, capture_region

    if len(sys.argv) > 1:
        img = Image.open(sys.argv[1])
    else:
        print("Вибери регіон з назвами каменів...")
        region = calibrate()
        if not region:
            print("Скасовано")
            exit()
        x, y, w, h = region
        img = capture_region(x, y, w, h)

    print("\nРезультат OCR:")
    lines = scan(img)
    for line in lines:
        print(f"  → {line}")

    if not lines:
        print("  (нічого не розпізнано)")
