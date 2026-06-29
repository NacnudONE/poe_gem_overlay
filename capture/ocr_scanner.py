import pytesseract
from PIL import Image, ImageFilter, ImageOps
import os

# Знаходимо Tesseract автоматично
_TESSERACT_PATHS = [
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
    r"C:\Users\{}\AppData\Local\Programs\Tesseract-OCR\tesseract.exe".format(os.getenv("USERNAME", "")),
]

_found = next((p for p in _TESSERACT_PATHS if os.path.exists(p)), None)
if _found:
    pytesseract.pytesseract.tesseract_cmd = _found
else:
    print("УВАГА: Tesseract OCR не знайдено!")
    print("Встанови з: https://github.com/UB-Mannheim/tesseract/wiki")
    print("Стандартний шлях: C:\\Program Files\\Tesseract-OCR\\tesseract.exe")


def preprocess(image: Image.Image) -> Image.Image:
    """Готує зображення для OCR: сірі тони → бінаризація → збільшення."""
    # Переводимо в сірі тони
    gray = image.convert("L")

    # Збільшуємо у 2 рази — OCR краще читає великий текст
    w, h = gray.size
    upscaled = gray.resize((w * 2, h * 2), Image.LANCZOS)

    # Бінаризація: текст PoE зазвичай світлий на темному фоні
    # Інвертуємо щоб отримати темний текст на світлому — Tesseract так краще читає
    inverted = ImageOps.invert(upscaled)

    # Підвищуємо контраст через threshold
    binarized = inverted.point(lambda px: 255 if px > 100 else 0)

    return binarized


def scan(image: Image.Image) -> list[str]:
    """
    Запускає OCR на зображенні.
    Повертає список рядків тексту (без порожніх і занадто коротких).
    """
    processed = preprocess(image)

    # Запускаємо Tesseract (англійська мова, режим рядків)
    raw_text = pytesseract.image_to_string(
        processed,
        lang="eng",
        config="--psm 6"  # psm 6 = вважати блоком тексту
    )

    lines = []
    for line in raw_text.splitlines():
        cleaned = line.strip()
        # Відкидаємо рядки < 3 символів або суто цифри/символи
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
        # Якщо передано файл як аргумент
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
