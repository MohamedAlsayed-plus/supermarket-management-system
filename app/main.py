"""نقطة تشغيل التطبيق: python -m app.main"""

from __future__ import annotations

import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PySide6.QtCore import Qt  # noqa: E402
from PySide6.QtWidgets import QApplication, QDialog  # noqa: E402

from app.config import load_config  # noqa: E402
from app.login_dialog import LoginDialog  # noqa: E402
from app.main_window import MainWindow  # noqa: E402
from app.rtl import arabic_font  # noqa: E402


def main() -> int:
    application = QApplication(sys.argv)
    application.setApplicationName("SupermarketDB")
    application.setFont(arabic_font())
    application.setLayoutDirection(Qt.LayoutDirection.RightToLeft)

    dialog = LoginDialog(load_config())
    if dialog.exec() != QDialog.Accepted or dialog.database is None:
        return 0

    window = MainWindow(dialog.database)
    window.show()
    return application.exec()


if __name__ == "__main__":
    raise SystemExit(main())
