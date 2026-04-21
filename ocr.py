import asyncio
import io
from dataclasses import dataclass

import numpy as np
from PIL import Image
from winsdk.windows.media.ocr import OcrEngine
from winsdk.windows.globalization import Language
from winsdk.windows.graphics.imaging import BitmapDecoder, BitmapPixelFormat, BitmapAlphaMode
from winsdk.windows.storage.streams import InMemoryRandomAccessStream, DataWriter

LANG_TAG = {
    "English": "en",
    "Japanese": "ja",
    "Chinese (Simplified)": "zh-Hans",
    "Chinese (Traditional)": "zh-Hant",
    "Korean": "ko",
    "French": "fr",
    "German": "de",
    "Spanish": "es",
    "Russian": "ru",
    "Thai": "th",
    "Vietnamese": "vi",
}


@dataclass
class TextBlock:
    text: str
    est_px: int  # 추정 원문 폰트 크기 (픽셀)


def _median(values: list[float]) -> float:
    s = sorted(values)
    return s[len(s) // 2]


def _group_into_blocks(lines_data: list[dict]) -> list[TextBlock]:
    """줄 높이 변화와 줄 간격으로 블록 분리."""
    if not lines_data:
        return []

    blocks: list[list[dict]] = []
    current = [lines_data[0]]

    print(f"\n── OCR 블록 분석 ──────────────────────────")
    print(f"  [0] h={lines_data[0]['height']:.0f}  \"{lines_data[0]['text'][:40]}\"")

    for i in range(1, len(lines_data)):
        prev = lines_data[i - 1]
        curr = lines_data[i]
        gap = curr["top"] - prev["bottom"]
        height_ratio = curr["height"] / prev["height"] if prev["height"] > 0 else 1
        gap_thr = prev["height"] * 1.0
        new_block = gap > gap_thr or abs(height_ratio - 1) > 0.3

        print(f"  [{i}] h={curr['height']:.0f}  gap={gap:.0f}(thr={gap_thr:.0f})  "
              f"ratio={height_ratio:.2f}  → {'★NEW' if new_block else 'same'}"
              f"  \"{curr['text'][:40]}\"")

        if new_block:  # gap > h*1.0 or size change > 30%
            blocks.append(current)
            current = [curr]
        else:
            current.append(curr)

    blocks.append(current)

    result = []
    print(f"── 최종 블록 ──────────────────────────────")
    for idx, block_lines in enumerate(blocks):
        text = "\n".join(l["text"] for l in block_lines)
        est_px = int(max(l["height"] for l in block_lines))
        print(f"  BLOCK {idx+1}: est_px={est_px}  {len(block_lines)}줄  "
              f"\"{text[:60].replace(chr(10), ' / ')}\"")
        result.append(TextBlock(text=text, est_px=est_px))
    return result


async def _recognize_async(frame_bgr: np.ndarray, lang_tag: str) -> list[TextBlock]:
    language = Language(lang_tag)
    if not OcrEngine.is_language_supported(language):
        return [TextBlock(f"[언어 미지원: {lang_tag}]", 0)]
    engine = OcrEngine.try_create_from_language(language)
    if engine is None:
        return [TextBlock("[OCR 엔진 없음]", 0)]

    rgb = frame_bgr[:, :, ::-1]
    buf = io.BytesIO()
    Image.fromarray(rgb).save(buf, format="PNG")
    png_bytes = buf.getvalue()

    stream = InMemoryRandomAccessStream()
    writer = DataWriter(stream)
    writer.write_bytes(png_bytes)
    await writer.store_async()
    await writer.flush_async()
    stream.seek(0)

    decoder = await BitmapDecoder.create_async(stream)
    bitmap = await decoder.get_software_bitmap_async(
        BitmapPixelFormat.BGRA8, BitmapAlphaMode.PREMULTIPLIED
    )
    result = await engine.recognize_async(bitmap)
    if not result or not result.lines:
        return []

    # 줄별 메타데이터 수집
    lines_data = []
    for line in result.lines:
        words = list(line.words)
        if not words:
            continue
        word_heights = [w.bounding_rect.height for w in words]
        tops = [w.bounding_rect.y for w in words]
        bottoms = [w.bounding_rect.y + w.bounding_rect.height for w in words]
        lines_data.append({
            "text": " ".join(w.text for w in words),
            "height": _median(word_heights),
            "top": min(tops),
            "bottom": max(bottoms),
        })

    lines_data.sort(key=lambda l: l["top"])
    return _group_into_blocks(lines_data)


def recognize(frame_bgr: np.ndarray, lang: str = "English") -> list[TextBlock]:
    tag = LANG_TAG.get(lang, "en")
    return asyncio.run(_recognize_async(frame_bgr, tag))
