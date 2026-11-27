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
from app.theme import apply_theme  # noqa: E402
from app.user_login_dialog import UserLoginDialog  # noqa: E402


def main() -> int:
    application = QApplication(sys.argv)
    application.setApplicationName("SupermarketDB")
    application.setFont(arabic_font())
    application.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
    config = load_config()
    apply_theme(application, str(config.get("theme", "light")) == "dark")

    dialog = LoginDialog(config)
    if dialog.exec() != QDialog.Accepted or dialog.database is None:
        return 0

    user_dialog = UserLoginDialog(dialog.database)
    if user_dialog.exec() != QDialog.Accepted or user_dialog.user is None:
        dialog.database.close()
        return 0

    window = MainWindow(dialog.database, user_dialog.user)
    window.show()
    return application.exec()


if __name__ == "__main__":
    raise SystemExit(main())
