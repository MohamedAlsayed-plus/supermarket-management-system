"""إعدادات الاتصال المخزنة محليًا.

لا يتم تضمين config.json في المستودع؛ استخدم config.example.json كنموذج.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

# عند التشغيل من PyInstaller، الملفات المرفقة تُستخرج داخل sys._MEIPASS.
# في التطوير العادي تكون الحزمة هي مجلد المشروع نفسه.
ROOT = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))
SQL_SCRIPT_PATH = ROOT / "sql" / "SupermarketDB.sql"


def _config_location() -> Path:
    """الإعدادات في مجلد المستخدم عند توزيع البرنامج كملف تنفيذي."""
    if getattr(sys, "frozen", False):
        base = Path(os.environ.get("APPDATA") or str(Path.home()))
        return base / "SupermarketDB" / "config.json"
    return ROOT / "config.json"


CONFIG_PATH = _config_location()

DEFAULT_CONFIG: dict[str, Any] = {
    "server": "localhost\\SQLEXPRESS",
    "database": "SupermarketDB",
    "auth": "windows",  # "windows" أو "sql"
    "username": "",
    "save_password": False,
    "password": "",
}


def load_config() -> dict[str, Any]:
    """قراءة الإعدادات مع دمج القيم الافتراضية."""
    config = dict(DEFAULT_CONFIG)
    try:
        data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return config
    if isinstance(data, dict):
        for key in DEFAULT_CONFIG:
            if key in data:
                config[key] = data[key]
    return config


def save_config(config: dict[str, Any]) -> None:
    """حفظ الإعدادات بترتيب ثابت، مع UTF-8 لدعم العربية."""
    data = {key: config.get(key, DEFAULT_CONFIG[key]) for key in DEFAULT_CONFIG}
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def read_schema_script() -> str:
    """قراءة سيناريو إنشاء قاعدة البيانات."""
    return SQL_SCRIPT_PATH.read_text(encoding="utf-8-sig")
