import json
import os
import tempfile
from pathlib import Path
from typing import Any

def _atomic_write_text(path: Path, data: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=path.name + ".", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(data)
            f.flush()
            try:
                os.fsync(f.fileno())
            except Exception:
                pass
        os.replace(tmp, path)
    except Exception:
        try:
            os.unlink(tmp)
        except Exception:
            pass
        raise

BASE_DIR = Path(__file__).parent
SETTINGS_FILE = BASE_DIR / "settings.json"

DEFAULT_SETTINGS: dict[str, Any] = {
    "language": "en",
    "browser_type": "firefox",

    "webrtc_protection": True,
    "fingerprint_noise": True,
    "spoof_hardware": True,
    "hide_webdriver": True,
    "block_notifications": False,
    "reload_restored_tabs": False,

    "auto_geolocate_proxy": True,
    "lookup_timeout_seconds": 5,

    "default_start_url": "https://2ip.ru/",
    "viewport_width": 1280,
    "viewport_height": 800,

    "lock_check_pid": True,
    "auto_clear_stale_locks": True,
}

LANGUAGES = (("en", "English"), ("ru", "Русский"))

BROWSERS = (
    ("firefox", "Firefox  (native SOCKS5 auth, recommended)"),
    ("chromium", "Chromium  (Chrome extensions)"),
)

TOGGLEABLE_KEYS = (
    "webrtc_protection",
    "fingerprint_noise",
    "spoof_hardware",
    "hide_webdriver",
    "block_notifications",
    "reload_restored_tabs",
    "auto_geolocate_proxy",
    "lock_check_pid",
    "auto_clear_stale_locks",
)

TOGGLE_LABELS = {
    "webrtc_protection": "WebRTC-защита (флаги + JS-гард от утечки IP)",
    "fingerprint_noise": "Шум canvas / WebGL",
    "spoof_hardware": "Подмена hardwareConcurrency / deviceMemory",
    "hide_webdriver": "Скрывать navigator.webdriver",
    "block_notifications": "Блокировать запросы уведомлений",
    "auto_geolocate_proxy": "Авто-привязка timezone/locale/гео к прокси",
    "lock_check_pid": "Проверять PID при lock-файле",
    "auto_clear_stale_locks": "Чистить мёртвые lock-файлы при старте",
}

def load_settings() -> dict:
    if not SETTINGS_FILE.exists():
        save_settings(DEFAULT_SETTINGS)
        return dict(DEFAULT_SETTINGS)
    with SETTINGS_FILE.open("r", encoding="utf-8") as f:
        data = json.load(f)
    changed = False
    for k, v in DEFAULT_SETTINGS.items():
        if k not in data:
            data[k] = v
            changed = True
    if changed:
        save_settings(data)
    return data

def save_settings(settings: dict) -> None:
    _atomic_write_text(SETTINGS_FILE, json.dumps(settings, indent=2, ensure_ascii=False))

def get(key: str) -> Any:
    return load_settings().get(key, DEFAULT_SETTINGS.get(key))

def set_value(key: str, value: Any) -> None:
    s = load_settings()
    s[key] = value
    save_settings(s)

def effective_for_profile(profile: dict) -> dict:
    s = load_settings()
    for key in TOGGLEABLE_KEYS:
        prof_val = profile.get(key)
        if prof_val is not None:
            s[key] = bool(prof_val)
    return s
