"""تحميل أيقونات SVG المخصصة وتلوينها حسب المظهر الحالي."""

from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import QByteArray, Qt
from PySide6.QtGui import QIcon, QImage, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer

ICON_DIR = (
    Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))
    / "app"
    / "icons"
)
_current_color = "#1f2937"
_cache: dict[tuple[str, int, str], QIcon] = {}


def set_icon_color(color: str) -> None:
    global _current_color
    _current_color = color
    _cache.clear()


def icon(name: str, size: int = 24, color: str | None = None) -> QIcon:
    color = color or _current_color
    key = (name, size, color)
    if key in _cache:
        return _cache[key]
    path = ICON_DIR / f"{name}.svg"
    if not path.exists():
        result = QIcon()
    else:
        svg = path.read_text(encoding="utf-8").replace("{COLOR}", color)
        renderer = QSvgRenderer(QByteArray(svg.encode("utf-8")))
        image = QImage(size, size, QImage.Format.Format_ARGB32)
        image.fill(Qt.GlobalColor.transparent)
        painter = QPainter(image)
        renderer.render(painter)
        painter.end()
        result = QIcon(QPixmap.fromImage(image))
    _cache[key] = result
    return result
