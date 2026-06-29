@echo off
echo ============================================
echo   PoE Gem Overlay - Build EXE
echo ============================================

echo [1/3] Installing PyInstaller...
python -m pip install pyinstaller > nul 2>&1
echo [1/3] PyInstaller OK

echo [2/3] Building EXE...
python -m PyInstaller --noconfirm --onefile --windowed --name "PoE_Gem_Overlay" --add-data "icons;icons" --hidden-import "mss" --hidden-import "PIL" --hidden-import "PIL.Image" --hidden-import "PIL.ImageOps" --hidden-import "PIL.ImageFilter" --hidden-import "pytesseract" --hidden-import "keyboard" --hidden-import "cv2" --hidden-import "requests" --hidden-import "difflib" app.py

echo [3/3] Done!
echo.
if exist "dist\PoE_Gem_Overlay.exe" (
    echo SUCCESS: dist\PoE_Gem_Overlay.exe
    echo NOTE: Tesseract OCR must be installed separately.
) else (
    echo ERROR: Build failed. Check output above.
)
echo.
pause
