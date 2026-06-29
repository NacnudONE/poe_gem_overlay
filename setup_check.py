"""
Run this script BEFORE the first launch of app.py
to verify that everything is configured correctly.
"""
import sys
import os

print("=" * 55)
print("  PoE Gem Overlay -- Setup Check")
print("=" * 55)

ok = True

# 1. Python version
print(f"\n[1] Python: {sys.version.split()[0]}", end="")
if sys.version_info >= (3, 10):
    print(" OK")
else:
    print(" FAIL (Python 3.10+ required)")
    ok = False

# 2. Libraries
libs = ["mss", "PIL", "cv2", "numpy", "requests", "keyboard", "winrt"]
print("\n[2] Python libraries:")
for lib in libs:
    try:
        __import__(lib)
        print(f"    {lib:<15} OK")
    except ImportError:
        print(f"    {lib:<15} MISSING  ->  pip install -r requirements.txt")
        ok = False

# 3. Windows OCR
print("\n[3] Windows OCR engine:")
try:
    import winrt.windows.media.ocr as _ocr
    langs = _ocr.OcrEngine.get_available_recognizer_languages()
    lang_ids = [str(l.language_tag) for l in langs]
    en_ok = any("en" in lid.lower() for lid in lang_ids)
    print(f"    Available languages: {', '.join(lang_ids[:5])}")
    if en_ok:
        print("    English OCR: OK")
    else:
        print("    English OCR: NOT FOUND")
        print("    Go to Windows Settings -> Time & Language -> Language")
        print("    and add English (United States) with OCR support.")
        ok = False
except Exception as e:
    print(f"    ERROR: {e}")
    ok = False

# 4. Internet (poe.ninja)
print("\n[4] Internet (poe.ninja):")
try:
    import requests
    r = requests.get("https://poe.ninja", timeout=8)
    if r.ok:
        print("    poe.ninja: OK")
    else:
        print(f"    poe.ninja: ERROR ({r.status_code})")
        ok = False
except Exception as e:
    print(f"    ERROR: {e}")
    ok = False

# 5. Config
print("\n[5] Config (config.py):")
import config
print(f"    League:  {config.LEAGUE}")
print(f"    Hotkey:  {config.HOTKEY}")

# Summary
print("\n" + "=" * 55)
if ok:
    print("  All good! Run: python app.py")
else:
    print("  Issues found -- fix them using the instructions above.")
print("=" * 55)
