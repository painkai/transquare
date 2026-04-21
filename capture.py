import dxcam
import numpy as np
from PyQt6.QtCore import QThread, pyqtSignal
from ocr import recognize, TextBlock
from translate import translate


class CaptureWorker(QThread):
    """
    별도 스레드에서 dxcam으로 지정 영역을 주기적으로 캡처 후 OCR + 번역.
    blocks_ready: list[TextBlock] (번역된 블록 리스트)
    """
    frame_ready = pyqtSignal(object)
    blocks_ready = pyqtSignal(object)  # list[TextBlock]

    def __init__(self, get_region, get_src_lang, get_tgt_lang, interval_ms: int = 2000):
        super().__init__()
        self.get_region = get_region
        self.get_src_lang = get_src_lang
        self.get_tgt_lang = get_tgt_lang
        self.interval_ms = interval_ms
        self._running = False
        self._paused = True
        self._camera = None
        self._last_text = None

    # ── public API ────────────────────────────────────────────────────────────

    def set_interval(self, ms: int):
        self.interval_ms = max(200, ms)

    def pause(self):
        self._paused = True

    def resume(self):
        self._paused = False

    def stop(self):
        self._running = False
        self.wait()

    # ── thread body ───────────────────────────────────────────────────────────

    def run(self):
        self._camera = dxcam.create(output_color="BGR")
        self._running = True

        while self._running:
            if self._paused:
                self.msleep(200)
                continue

            region = self.get_region()
            if region and region[2] > region[0] and region[3] > region[1]:
                frame = self._camera.grab(region=region)
                if frame is not None:
                    self.frame_ready.emit(frame)
                    src_lang = self.get_src_lang()
                    tgt_lang = self.get_tgt_lang()

                    blocks = recognize(frame, src_lang)
                    if not blocks:
                        self.msleep(self.interval_ms)
                        continue

                    full_text = "\n\n".join(b.text for b in blocks)
                    if full_text == self._last_text:
                        self.msleep(self.interval_ms)
                        continue
                    self._last_text = full_text

                    translated = [
                        TextBlock(
                            text=translate(b.text, src_lang, tgt_lang),
                            est_px=b.est_px,
                        )
                        for b in blocks
                    ]
                    self.blocks_ready.emit(translated)

            self.msleep(self.interval_ms)

        self._camera.release()
        self._camera = None
