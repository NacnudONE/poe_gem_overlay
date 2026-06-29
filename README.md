# ⚗ PoE Gem Overlay

[🇺🇦 Українська](#українська) | [🇬🇧 English](#english)

---

## Українська

Overlay для **Path of Exile 1**, який показує ціни Transfigured Gems у реальному часі прямо поверх гри.

### Як це працює

Програма стежить за tooltip каменя під курсором миші. Щойно ти наводиш мишу на Transfigured Gem у вікні лабіринту — overlay показує поточну ціну з PoE Trade API.

### Функції

- 🔍 Автоматичне розпізнавання назви каменя через OCR
- 💰 Ціна в chaos і divine orb у реальному часі
- 🏆 Підсвічує найдорожчий камінь серед знайдених
- 🌍 Вибір ліги з актуального списку
- 🇺🇦 / 🇬🇧 Перемикання мови інтерфейсу (UA / EN)
- 🖱️ Click-through overlay — не заважає грі

### Вимоги

- Windows 10 / 11
- Python 3.10+
- [Tesseract OCR](https://github.com/UB-Mannheim/tesseract/wiki) — встановити в стандартну папку `C:\Program Files\Tesseract-OCR\`

### Встановлення

```bash
git clone https://github.com/NacnudONE/poe_gem_overlay.git
cd poe_gem_overlay
pip install -r requirements.txt
```

### Запуск

```bash
python app.py
```

Або завантаж готовий **[EXE з релізів](https://github.com/NacnudONE/poe_gem_overlay/releases/latest)** — Tesseract OCR все одно потрібен.

### Перевірка налаштувань

```bash
python setup_check.py
```

### Використання

1. Запусти `app.py`
2. Вибери лігу зі списку
3. Натисни **Старт**
4. Наводь мишу на камені у вікні лабіринту — ціни з'являться в overlay
5. Кнопка `F9` — вкл/викл overlay поверх гри

### Структура проекту

```
poe_gem_overlay/
├── app.py               ← головний GUI
├── config.py            ← налаштування
├── core/
│   ├── trade_fetcher.py ← ціни з PoE Trade API
│   ├── price_fetcher.py ← ціни з poe.watch
│   ├── gem_matcher.py   ← пошук збігів
│   └── icon_db.py       ← база іконок
├── capture/
│   ├── tooltip_scanner.py  ← сканування tooltip
│   ├── ocr_scanner.py      ← OCR розпізнавання
│   └── screen_capture.py   ← захоплення екрану
└── ui/
    ├── overlay.py       ← click-through вікно
    └── i18n.py          ← переклади
```

---

## English

A real-time **Path of Exile 1** overlay that displays Transfigured Gem prices directly over the game.

### How It Works

The app monitors the gem tooltip under your cursor. When you hover over a Transfigured Gem in the Labyrinth reward window, the overlay instantly shows the current price from the PoE Trade API.

### Features

- 🔍 Automatic gem name detection via OCR
- 💰 Real-time prices in chaos and divine orbs
- 🏆 Highlights the most valuable gem
- 🌍 League selection from a live list
- 🇺🇦 / 🇬🇧 Language toggle (UA / EN)
- 🖱️ Click-through overlay — doesn't interfere with gameplay

### Requirements

- Windows 10 / 11
- Python 3.10+
- [Tesseract OCR](https://github.com/UB-Mannheim/tesseract/wiki) — install to the default path `C:\Program Files\Tesseract-OCR\`

### Installation

```bash
git clone https://github.com/NacnudONE/poe_gem_overlay.git
cd poe_gem_overlay
pip install -r requirements.txt
```

### Run

```bash
python app.py
```

Or download the prebuilt **[EXE from Releases](https://github.com/NacnudONE/poe_gem_overlay/releases/latest)** — Tesseract OCR is still required.

### Check Setup

```bash
python setup_check.py
```

### Usage

1. Launch `app.py`
2. Select your league from the dropdown
3. Click **Start**
4. Hover over gems in the Labyrinth reward window — prices appear in the overlay
5. Press `F9` to toggle the overlay on/off

### Project Structure

```
poe_gem_overlay/
├── app.py               ← main GUI
├── config.py            ← settings
├── core/
│   ├── trade_fetcher.py ← prices from PoE Trade API
│   ├── price_fetcher.py ← prices from poe.watch
│   ├── gem_matcher.py   ← fuzzy name matching
│   └── icon_db.py       ← icon database
├── capture/
│   ├── tooltip_scanner.py  ← tooltip scanning
│   ├── ocr_scanner.py      ← OCR recognition
│   └── screen_capture.py   ← screen capture
└── ui/
    ├── overlay.py       ← click-through window
    └── i18n.py          ← translations
```

### License

MIT
