@echo off
chcp 65001 > nul
echo ============================================
echo   PoE Gem Overlay — Збірка EXE
echo ============================================

:: Встановлюємо PyInstaller якщо потрібно
pip show pyinstaller > nul 2>&1
if errorlevel 1 (
    echo [1/3] Встановлюю PyInstaller...
    pip install pyinstaller
) else (
    echo [1/3] PyInstaller вже встановлено
)

echo [2/3] Збираю EXE...
pyinstaller --noconfirm ^
  --onefile ^
  --windowed ^
  --name "PoE_Gem_Overlay" ^
  --add-data "icons;icons" ^
  --hidden-import "mss" ^
  --hidden-import "PIL" ^
  --hidden-import "PIL.Image" ^
  --hidden-import "PIL.ImageOps" ^
  --hidden-import "PIL.ImageFilter" ^
  --hidden-import "pytesseract" ^
  --hidden-import "keyboard" ^
  --hidden-import "cv2" ^
  --hidden-import "requests" ^
  --hidden-import "difflib" ^
  app.py

echo [3/3] Готово!
echo.
if exist "dist\PoE_Gem_Overlay.exe" (
    echo  EXE знаходиться тут: dist\PoE_Gem_Overlay.exe
    echo.
    echo  ВАЖЛИВО: Tesseract OCR має бути встановлений окремо.
    echo  Стандартний шлях: C:\Program Files\Tesseract-OCR\tesseract.exe
) else (
    echo  Помилка збірки! Перевір вивід вище.
)
echo.
pause
