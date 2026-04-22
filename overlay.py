import signal
import sys
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QComboBox, QFrame, QToolButton, QTextEdit,
)
from PyQt6.QtCore import Qt, QPoint, QRect, pyqtSignal
from PyQt6.QtGui import QColor, QPainter, QFont, QFontMetrics

from capture import CaptureWorker
from ocr import TextBlock

RESIZE_MARGIN = 8
LANGUAGES = ["English", "Japanese", "Chinese (Simplified)", "Chinese (Traditional)",
             "Korean", "French", "German", "Spanish", "Russian", "Thai", "Vietnamese"]


class OverlayWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setMinimumSize(320, 200)
        self.resize(520, 420)
        self.setMouseTracking(True)

        self._resizing = False
        self._resize_edge = None
        self._resize_start_pos = QPoint()
        self._resize_start_geo = QRect()

        self._build_ui()
        self._start_capture()

    def _start_capture(self):
        self._capture = CaptureWorker(
            self._capture_region,
            lambda: self.bottom_area.get_languages()[0],
            lambda: self.bottom_area.get_languages()[1],
            interval_ms=2000,
        )
        self._capture.frame_ready.connect(self._on_frame)
        self._capture.blocks_ready.connect(self._on_blocks)
        self.bottom_area.toggle_capture.connect(self._on_toggle)
        self.bottom_area.retranslate.connect(self._on_retranslate)
        self._capture.start()

    def _capture_region(self):
        tl = self.mapToGlobal(self.top_area.pos())
        pad = RESIZE_MARGIN
        left   = tl.x() + pad
        top    = tl.y() + pad
        right  = left + self.top_area.width()  - pad * 2
        bottom = top  + self.top_area.height() - pad * 2
        return (left, top, right, bottom) if right > left and bottom > top else None

    def _on_frame(self, frame):
        h, w = frame.shape[:2]
        self.top_area.set_status(f"캡처됨  {w}×{h}")

    def _on_blocks(self, blocks: list):
        self.bottom_area.set_blocks(blocks)

    def _on_toggle(self, active: bool):
        if active:
            self._capture.resume()
        else:
            self._capture.pause()

    def _on_retranslate(self):
        self._capture._last_text = None  # 캐시 리셋 → 다음 캡처 시 강제 재번역

    def closeEvent(self, event):
        self._capture.stop()
        super().closeEvent(event)
        QApplication.quit()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(RESIZE_MARGIN, RESIZE_MARGIN, RESIZE_MARGIN, RESIZE_MARGIN)
        layout.setSpacing(0)

        self.top_area = CaptureArea(self)

        divider = QFrame()
        divider.setFixedHeight(2)
        divider.setStyleSheet("background-color: rgba(255,255,255,100);")

        self.bottom_area = TranslationArea(self)

        layout.addWidget(self.top_area, 1)
        layout.addWidget(divider)
        layout.addWidget(self.bottom_area, 1)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QColor(255, 255, 255, 60))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        m = RESIZE_MARGIN // 2
        painter.drawRect(self.rect().adjusted(m, m, -m, -m))

    # ── Resize logic ─────────────────────────────────────────────────────────

    def _get_edge(self, pos):
        x, y, w, h, m = pos.x(), pos.y(), self.width(), self.height(), RESIZE_MARGIN
        edge = ""
        if y < m:       edge += "N"
        elif y > h - m: edge += "S"
        if x < m:       edge += "W"
        elif x > w - m: edge += "E"
        return edge or None

    _CURSOR_MAP = {
        "N":  Qt.CursorShape.SizeVerCursor,
        "S":  Qt.CursorShape.SizeVerCursor,
        "W":  Qt.CursorShape.SizeHorCursor,
        "E":  Qt.CursorShape.SizeHorCursor,
        "NW": Qt.CursorShape.SizeFDiagCursor,
        "SE": Qt.CursorShape.SizeFDiagCursor,
        "NE": Qt.CursorShape.SizeBDiagCursor,
        "SW": Qt.CursorShape.SizeBDiagCursor,
    }

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            edge = self._get_edge(event.pos())
            if edge:
                self._resizing = True
                self._resize_edge = edge
                self._resize_start_pos = event.globalPosition().toPoint()
                self._resize_start_geo = self.geometry()
                event.accept()

    def mouseMoveEvent(self, event):
        if self._resizing:
            self._do_resize(event.globalPosition().toPoint())
        else:
            edge = self._get_edge(event.pos())
            self.setCursor(self._CURSOR_MAP[edge]) if edge else self.unsetCursor()

    def mouseReleaseEvent(self, event):
        self._resizing = False
        self._resize_edge = None

    def _do_resize(self, gpos):
        dx = gpos.x() - self._resize_start_pos.x()
        dy = gpos.y() - self._resize_start_pos.y()
        geo = QRect(self._resize_start_geo)
        e = self._resize_edge
        if "E" in e: geo.setRight(geo.right() + dx)
        if "S" in e: geo.setBottom(geo.bottom() + dy)
        if "W" in e: geo.setLeft(geo.left() + dx)
        if "N" in e: geo.setTop(geo.top() + dy)
        if geo.width() >= self.minimumWidth() and geo.height() >= self.minimumHeight():
            self.setGeometry(geo)


class CaptureArea(QWidget):
    """상단 투명 영역 — 드래그로 창 이동"""

    def __init__(self, parent):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setMouseTracking(True)
        self._drag_pos = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        top_bar = QHBoxLayout()
        hint = QLabel("[ 캡처 영역 ]")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hint.setStyleSheet("color: rgba(255,255,255,45); font-size: 11px; letter-spacing: 2px;")

        close_btn = QToolButton()
        close_btn.setText("✕")
        close_btn.setFixedSize(20, 20)
        close_btn.setToolTip("종료")
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.setStyleSheet("""
            QToolButton {
                background: transparent;
                color: rgba(255,255,255,60);
                border: none;
                font-size: 11px;
            }
            QToolButton:hover { color: rgba(255,80,80,220); }
        """)
        close_btn.clicked.connect(self.window().close)

        top_bar.addWidget(hint, 1)
        top_bar.addWidget(close_btn)
        layout.addLayout(top_bar)

        self._status = QLabel("")
        self._status.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignBottom)
        self._status.setStyleSheet("color: rgba(120,255,120,160); font-size: 10px;")

        layout.addStretch()
        layout.addWidget(self._status)

    def set_status(self, text: str):
        self._status.setText(text)

    def paintEvent(self, event):
        painter = QPainter(self)
        # alpha=1: 완전 투명처럼 보이지만 마우스 이벤트는 수신
        painter.fillRect(self.rect(), QColor(0, 0, 0, 1))

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            # 테두리 resize 영역이면 부모에게 넘김
            if self.window()._get_edge(self.mapTo(self.window(), event.pos())):
                event.ignore()
                return
            self._drag_pos = event.globalPosition().toPoint() - self.window().frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if self._drag_pos is not None and event.buttons() == Qt.MouseButton.LeftButton:
            self.window().move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event):
        self._drag_pos = None


class TranslationArea(QWidget):
    """하단 반투명 영역 — 번역 결과 + 언어 선택"""

    toggle_capture = pyqtSignal(bool)  # True = resume, False = pause
    retranslate = pyqtSignal()

    def __init__(self, parent):
        super().__init__(parent)
        self._active = False
        self._build_ui()

    def _build_ui(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(10, 4, 4, 10)
        root.setSpacing(4)

        # ── 왼쪽: 언어 패널 + 번역 텍스트 ───────────────────────────────
        left = QVBoxLayout()
        left.setSpacing(4)

        self.lang_panel = QWidget()
        self.lang_panel.setVisible(False)
        lang_layout = QHBoxLayout(self.lang_panel)
        lang_layout.setContentsMargins(0, 0, 0, 4)
        lang_layout.setSpacing(6)

        combo_style = """
            QComboBox {
                background: rgba(20,20,30,200);
                color: rgba(255,255,255,220);
                border: 1px solid rgba(255,255,255,70);
                border-radius: 4px;
                padding: 2px 8px;
                font-size: 11px;
                min-width: 140px;
            }
            QComboBox::drop-down { border: none; width: 18px; }
            QComboBox QAbstractItemView {
                background: rgba(20,20,30,240);
                color: white;
                selection-background-color: rgba(80,100,200,180);
            }
        """
        self.src_combo = QComboBox()
        self.tgt_combo = QComboBox()
        for combo in (self.src_combo, self.tgt_combo):
            combo.addItems(LANGUAGES)
            combo.setStyleSheet(combo_style)

        self.src_combo.setCurrentText("English")
        self.tgt_combo.setCurrentText("Korean")

        arrow = QLabel("→")
        arrow.setStyleSheet("color: rgba(255,255,255,130); font-size: 14px;")

        lang_layout.addWidget(self.src_combo)
        lang_layout.addWidget(arrow)
        lang_layout.addWidget(self.tgt_combo)
        lang_layout.addStretch()
        left.addWidget(self.lang_panel)

        self.trans_view = QTextEdit()
        self.trans_view.setReadOnly(True)
        self.trans_view.setFrameStyle(QFrame.Shape.NoFrame)
        self.trans_view.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.trans_view.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.trans_view.document().setDocumentMargin(10)
        self.trans_view.setStyleSheet("""
            QTextEdit {
                background: transparent;
                color: rgba(240,240,255,210);
                border: none;
            }
        """)
        self.trans_view.setHtml("<p style='color:rgba(240,240,255,120); font-size:11px;'>번역 결과가 여기에 표시됩니다.</p>")
        left.addWidget(self.trans_view, 1)

        root.addLayout(left, 1)

        # ── 오른쪽: 세로 버튼 열 ─────────────────────────────────────────
        btn_col = QVBoxLayout()
        btn_col.setSpacing(6)
        btn_col.setContentsMargins(0, 0, 0, 0)

        self.play_btn = QToolButton()
        self.play_btn.setText("▶")
        self.play_btn.setFixedSize(22, 22)
        self.play_btn.setToolTip("번역 시작")
        self.play_btn.setStyleSheet("""
            QToolButton {
                background: transparent;
                color: rgba(100,220,100,180);
                border: none;
                font-size: 13px;
            }
            QToolButton:hover { color: rgba(100,255,100,255); }
        """)
        self.play_btn.clicked.connect(self._toggle)

        retry_btn = QToolButton()
        retry_btn.setText("↺")
        retry_btn.setFixedSize(22, 22)
        retry_btn.setToolTip("다시 번역")
        retry_btn.setStyleSheet("""
            QToolButton {
                background: transparent;
                color: rgba(180,180,255,160);
                border: none;
                font-size: 14px;
            }
            QToolButton:hover { color: rgba(200,200,255,255); }
        """)
        retry_btn.clicked.connect(self.retranslate)

        self.lang_btn = QToolButton()
        self.lang_btn.setText("⚙")
        self.lang_btn.setFixedSize(22, 22)
        self.lang_btn.setToolTip("언어 설정")
        self.lang_btn.setStyleSheet("""
            QToolButton {
                background: transparent;
                color: rgba(255,255,255,90);
                border: none;
                font-size: 13px;
            }
            QToolButton:hover { color: rgba(255,255,255,230); }
        """)
        self.lang_btn.clicked.connect(self._toggle_lang_panel)

        for btn in (self.play_btn, retry_btn, self.lang_btn):
            btn.setCursor(Qt.CursorShape.PointingHandCursor)

        btn_col.addWidget(self.play_btn)
        btn_col.addWidget(retry_btn)
        btn_col.addWidget(self.lang_btn)
        btn_col.addStretch()

        root.addLayout(btn_col)

    def _toggle(self):
        self._active = not self._active
        self.toggle_capture.emit(self._active)
        if self._active:
            self.play_btn.setText("⏹")
            self.play_btn.setToolTip("번역 중지")
            self.play_btn.setStyleSheet("""
                QToolButton {
                    background: transparent;
                    color: rgba(220,80,80,200);
                    border: none;
                    font-size: 13px;
                }
                QToolButton:hover { color: rgba(255,80,80,255); }
            """)
        else:
            self.play_btn.setText("▶")
            self.play_btn.setToolTip("번역 시작")
            self.play_btn.setStyleSheet("""
                QToolButton {
                    background: transparent;
                    color: rgba(100,220,100,180);
                    border: none;
                    font-size: 13px;
                }
                QToolButton:hover { color: rgba(100,255,100,255); }
            """)

    def _toggle_lang_panel(self):
        self.lang_panel.setVisible(not self.lang_panel.isVisible())

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(8, 8, 20, 185))

    def get_languages(self):
        return self.src_combo.currentText(), self.tgt_combo.currentText()

    BOLD_THRESHOLD_PX = 20
    BLOCK_SPACING = 14  # 블록 하단 여백(px) — 구분 공간 포함

    def _block_sizes(self, blocks: list, scale: float) -> list[int]:
        """scale 기준으로 블록별 폰트 크기 계산 (제곱근 비율로 차이 완화)."""
        import math
        max_est = max((b.est_px for b in blocks), default=1) or 1
        sizes = []
        for b in blocks:
            ratio = math.sqrt(b.est_px / max_est) if b.est_px > 0 else 0.5
            px = max(8, int(32 * scale * ratio))
            sizes.append(px)
        return sizes

    def _total_height(self, blocks: list, sizes: list[int], w: int) -> int:
        total = 0
        for block, px in zip(blocks, sizes):
            f = QFont()
            f.setPixelSize(px)
            fm = QFontMetrics(f)
            rect = fm.boundingRect(0, 0, w, 9999, Qt.TextFlag.TextWordWrap, block.text)
            total += rect.height() + self.BLOCK_SPACING
        return total

    def set_blocks(self, blocks: list):
        """블록별 폰트 크기 비율을 유지하면서 뷰에 전부 들어오도록 조정."""
        doc_margin = int(self.trans_view.document().documentMargin())
        w = self.trans_view.viewport().width() - doc_margin * 2
        h = self.trans_view.viewport().height() - doc_margin * 2
        if w <= 0 or h <= 0 or not blocks:
            return

        # 이진 탐색으로 전체가 h 안에 들어오는 최대 scale 찾기
        lo, hi = 0.1, 1.0
        for _ in range(12):
            mid = (lo + hi) / 2
            if self._total_height(blocks, self._block_sizes(blocks, mid), w) <= h:
                lo = mid
            else:
                hi = mid
        sizes = self._block_sizes(blocks, lo)

        parts = []
        for block, px in zip(blocks, sizes):
            bold = "bold" if block.est_px >= self.BOLD_THRESHOLD_PX else "normal"
            safe = block.text.replace("&", "&amp;").replace("<", "&lt;").replace("\n", "<br>")
            parts.append(
                f'<p style="margin:0 0 {self.BLOCK_SPACING}px 0; font-size:{px}px; '
                f'font-weight:{bold}; color:rgba(240,240,255,210);">{safe}</p>'
            )

        self.trans_view.setHtml("".join(parts))


if __name__ == "__main__":
    app = QApplication(sys.argv)
    font = app.font()
    font.setPointSize(10)
    app.setFont(font)
    signal.signal(signal.SIGINT, lambda *_: app.quit())
    win = OverlayWindow()
    win.show()
    sys.exit(app.exec())
