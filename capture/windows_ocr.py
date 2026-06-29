"""
Windows вбудований OCR двигун (Windows.Media.Ocr).
Не потребує Tesseract — працює на будь-якому Windows 10/11.
"""
import asyncio
from PIL import Image

import winrt.windows.media.ocr as _winrt_ocr
import winrt.windows.graphics.imaging as _winrt_img
import winrt.windows.storage.streams as _winrt_streams
from winrt.windows.globalization import Language


def _get_loop() -> asyncio.AbstractEventLoop:
    try:
        loop = asyncio.get_event_loop()
        if loop.is_closed():
            raise RuntimeError
        return loop
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop


async def _recognize_async(pil_image: Image.Image) -> str:
    img = pil_image.convert("RGBA")
    w, h = img.size
    data = img.tobytes()

    buf = _winrt_streams.Buffer(len(data))
    buf.length = len(data)
    with memoryview(buf) as mv:
        mv[:] = data

    bitmap = _winrt_img.SoftwareBitmap.create_copy_from_buffer(
        buf,
        _winrt_img.BitmapPixelFormat.RGBA8,
        w, h,
        _winrt_img.BitmapAlphaMode.STRAIGHT,
    )

    engine = _winrt_ocr.OcrEngine.try_create_from_language(Language("en-US"))
    if engine is None:
        engine = _winrt_ocr.OcrEngine.try_create_from_user_profile_languages()
    if engine is None:
        return ""

    result = await engine.recognize_async(bitmap)
    return result.text if result else ""


def ocr(pil_image: Image.Image) -> str:
    """Розпізнає текст на зображенні без Tesseract."""
    return _get_loop().run_until_complete(_recognize_async(pil_image))
