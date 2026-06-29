"""
Запусти цей скрипт ПЕРЕД першим запуском main.py
щоб перевірити що все налаштовано правильно.
"""
import sys
import os

print("=" * 55)
print("  PoE Gem Overlay — Перевірка налаштувань")
print("=" * 55)

ok = True

# 1. Python version
print(f"\n[1] Python: {sys.version.split()[0]}", end="")
if sys.version_info >= (3, 10):
    print(" ✓")
else:
    print(" ✗ (потрібен Python 3.10+)")
    ok = False

# 2. Бібліотеки
libs = ["mss", "PIL", "pytesseract", "requests", "keyboard"]
print("\n[2] Бібліотеки Python:")
for lib in libs:
    try:
        __import__(lib)
        print(f"    {lib:<15} ✓")
    except ImportError:
        print(f"    {lib:<15} ✗  → pip install {lib}")
        ok = False

# 3. Tesseract OCR
print("\n[3] Tesseract OCR:")
tesseract_paths = [
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
]
found_tesseract = None
for path in tesseract_paths:
    if os.path.exists(path):
        found_tesseract = path
        break

if found_tesseract:
    print(f"    Знайдено: {found_tesseract} ✓")
else:
    print("    НЕ ЗНАЙДЕНО ✗")
    print()
    print("    Встанови Tesseract OCR:")
    print("    1. Відкрий: https://github.com/UB-Mannheim/tesseract/wiki")
    print("    2. Завантаж 'tesseract-ocr-w64-setup-5.x.x.exe'")
    print("    3. Встанови в стандартну папку")
    print("       (C:\\Program Files\\Tesseract-OCR\\)")
    ok = False

# 4. Підключення до інтернету (poe.watch)
print("\n[4] Підключення до poe.watch:")
try:
    import requests
    r = requests.get("https://api.poe.watch/categories", timeout=8)
    if r.ok:
        print("    poe.watch доступний ✓")
    else:
        print(f"    poe.watch недоступний ({r.status_code}) ✗")
        ok = False
except Exception as e:
    print(f"    Помилка: {e} ✗")
    ok = False

# 5. Конфіг
print("\n[5] Налаштування (config.py):")
import config
print(f"    Ліга: {config.LEAGUE}")
print(f"    Гаряча клавіша: {config.HOTKEY}")

# Підсумок
print("\n" + "=" * 55)
if ok:
    print("  Все готово! Запускай: python main.py")
else:
    print("  Є проблеми — виправ їх за інструкціями вище")
print("=" * 55)
