"""
Читає назву каменя з tooltip PoE 1.
Tooltip з'являється у лівій частині екрану.
Назва — ПЕРШИЙ великий бірюзовий рядок тексту зверху.
"""
import re
import cv2
import numpy as np
from PIL import Image
import mss
from capture.windows_ocr import ocr as win_ocr

# Бірюзовий колір назви каменя в PoE 1 (HSV OpenCV-scale)
TEAL_LOWER = np.array([70, 50, 100])
TEAL_UPPER = np.array([130, 255, 255])

# Мінімальна кількість бірюзових пікселів у рядку (в % ширини) щоб вважати рядком заголовка
MIN_ROW_FILL = 0.03


def capture_screen() -> np.ndarray:
    """Захоплює весь основний монітор."""
    with mss.mss() as sct:
        monitor = sct.monitors[1]
        shot = sct.grab(monitor)
        img = Image.frombytes("RGB", shot.size, shot.bgra, "raw", "BGRX")
        return cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)


def find_title_band(cv_img: np.ndarray) -> tuple | None:
    """
    Шукає горизонтальну смугу бірюзового тексту назви каменя.
    Tooltip в PoE 1 знаходиться у лівих ~65% екрану.
    Повертає (x, y, w, h) смуги або None.
    """
    h_img, w_img = cv_img.shape[:2]
    search_w = int(w_img * 0.65)
    region = cv_img[:, :search_w]

    hsv = cv2.cvtColor(region, cv2.COLOR_BGR2HSV)
    teal_mask = cv2.inRange(hsv, TEAL_LOWER, TEAL_UPPER)

    # Кількість бірюзових пікселів в кожному рядку
    row_counts = np.sum(teal_mask > 0, axis=1)
    min_px = search_w * MIN_ROW_FILL

    teal_rows = np.where(row_counts > min_px)[0]
    if len(teal_rows) < 2:
        return None

    # Групуємо сусідні рядки в смуги
    bands = []
    start = teal_rows[0]
    prev = teal_rows[0]
    for r in teal_rows[1:]:
        if r - prev > 10:
            bands.append((start, prev))
            start = r
        prev = r
    bands.append((start, prev))

    # Беремо НАЙВИЩУ (topmost) смугу — назва каменя завжди вгорі tooltip
    best_band = None
    for y_top, y_bot in sorted(bands, key=lambda b: b[0]):
        band_h = y_bot - y_top + 1
        if band_h < 3:
            continue
        best_band = (y_top, y_bot)
        break

    if best_band is None:
        return None

    y_top, y_bot = best_band
    pad = 6
    return (0, max(0, y_top - pad), search_w, (y_bot + pad) - (y_top - pad))


def ocr_title_strip(cv_img: np.ndarray, band: tuple) -> str | None:
    """OCR бірюзового тексту на заданій смузі."""
    x, y, w, h = band
    strip = cv_img[y:y + h, x:x + w]
    if strip.size == 0:
        return None

    # Маска тільки бірюзових пікселів — чисте зображення тексту
    hsv = cv2.cvtColor(strip, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv, TEAL_LOWER, TEAL_UPPER)

    # Збільшуємо для кращого OCR
    scale = max(2, 80 // max(h, 1))
    big = cv2.resize(mask, (w * scale, h * scale), interpolation=cv2.INTER_LANCZOS4)

    pil = Image.fromarray(big)
    text = win_ocr(pil).strip()

    # Очищаємо: тільки літери і пробіли
    cleaned = re.sub(r"[^a-zA-Z '\-]", "", text).strip()
    cleaned = re.sub(r"\s+", " ", cleaned)

    # Прибираємо OCR-сміття: короткі слова (1-2 символи) з початку і кінця
    words = cleaned.split()
    while words and len(words[0]) <= 2:
        words.pop(0)
    while words and len(words[-1]) <= 2:
        words.pop()
    cleaned = " ".join(words)

    if len(cleaned) > 4 and any(c.isalpha() for c in cleaned):
        return cleaned
    return None


def scan_tooltip() -> str | None:
    """
    Сканує екран і повертає назву каменя з tooltip, або None.
    """
    cv_img = capture_screen()
    band = find_title_band(cv_img)
    if band is None:
        return None
    return ocr_title_strip(cv_img, band)


# --- Тест на скріншоті ---
if __name__ == "__main__":
    import sys

    path = sys.argv[1] if len(sys.argv) > 1 else None
    if path:
        img = cv2.imread(path)
        if img is None:
            print(f"Не вдалось відкрити: {path}")
            exit(1)
    else:
        print("Захоплюю екран...")
        img = capture_screen()

    print(f"Розмір зображення: {img.shape[1]}x{img.shape[0]}")

    band = find_title_band(img)
    print(f"Title band: {band}")

    if band:
        x, y, w, h = band
        # Зберігаємо для перевірки
        debug_strip = img[y:y + h, x:x + w].copy()
        cv2.imwrite("dbg_title_strip.png", debug_strip)
        print("Saved dbg_title_strip.png")

        # Бірюзова маска для перевірки
        hsv = cv2.cvtColor(debug_strip, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(hsv, TEAL_LOWER, TEAL_UPPER)
        cv2.imwrite("dbg_title_mask.png", mask)
        print("Saved dbg_title_mask.png")

        name = ocr_title_strip(img, band)
        print(f"\nНазва каменя: {name!r}")
    else:
        print("Бірюзовий заголовок не знайдено (tooltip не відкрито?)")

        # Зберігаємо аналіз кольорів
        h_img, w_img = img.shape[:2]
        search_w = int(w_img * 0.65)
        region = img[:, :search_w]
        hsv = cv2.cvtColor(region, cv2.COLOR_BGR2HSV)
        teal_mask = cv2.inRange(hsv, TEAL_LOWER, TEAL_UPPER)
        row_counts = np.sum(teal_mask > 0, axis=1)
        print(f"Max teal pixels in any row: {row_counts.max()} (need > {int(search_w * MIN_ROW_FILL)})")
        cv2.imwrite("dbg_teal_mask.png", teal_mask)
        print("Saved dbg_teal_mask.png")
