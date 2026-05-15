import json
import os
import shutil
import sys
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Optional

import presets as fp_presets
from i18n import t
from proxy_utils import normalize_proxy_string

BASE_DIR = Path(__file__).parent
PROFILES_FILE = BASE_DIR / "profiles.json"
BROWSER_DATA_DIR = BASE_DIR / "browser_data"
EXTENSIONS_DIR = BASE_DIR / "extensions"

PROFILE_DEFAULTS = {
    "proxy": None,
    "extensions": [],
    "timezone": None,
    "locale": None,
    "geolocation": None,
    "webrtc_protection": None,
    "fingerprint_noise": None,
    "spoof_hardware": None,
    "hide_webdriver": None,
    "block_notifications": None,
    "start_url": None,
    "notes": "",
    "fingerprint_preset": None,
}

def _ensure_dirs() -> None:
    BROWSER_DATA_DIR.mkdir(exist_ok=True)
    EXTENSIONS_DIR.mkdir(exist_ok=True)

def load_profiles() -> dict:
    if not PROFILES_FILE.exists():
        return {}
    with PROFILES_FILE.open("r", encoding="utf-8") as f:
        return json.load(f)

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

def save_profiles(profiles: dict) -> None:
    _atomic_write_text(PROFILES_FILE, json.dumps(profiles, indent=2, ensure_ascii=False))

def _next_profile_id(profiles: dict) -> str:
    n = 1
    while f"profile_{n}" in profiles:
        n += 1
    return f"profile_{n}"

def _random_desktop_ua() -> str:
    return fp_presets.pick_random()["user_agent"]

def random_fingerprint_preset() -> dict:
    return fp_presets.pick_random()

def _resolve_id(profiles: dict, identifier: str) -> str:
    if identifier in profiles:
        return identifier
    for pid, p in profiles.items():
        if p["name"] == identifier:
            return pid
    raise KeyError(t("pm.profile_not_found", name=identifier))

def _apply_defaults(profile: dict) -> dict:
    for k, v in PROFILE_DEFAULTS.items():
        profile.setdefault(k, v)
    return profile

def create_profile(
    name: str,
    proxy: Optional[str] = None,
    extensions: Optional[list] = None,
    *,
    timezone: Optional[str] = None,
    locale: Optional[str] = None,
    geolocation: Optional[dict] = None,
    webrtc_protection: Optional[bool] = None,
    fingerprint_noise: Optional[bool] = None,
    spoof_hardware: Optional[bool] = None,
    hide_webdriver: Optional[bool] = None,
    block_notifications: Optional[bool] = None,
    start_url: Optional[str] = None,
    notes: str = "",
) -> tuple[str, dict]:
    _ensure_dirs()
    profiles = load_profiles()

    if any(p["name"] == name for p in profiles.values()):
        raise ValueError(t("pm.name_exists", name=name))

    normalized_proxy = normalize_proxy_string(proxy)

    profile_id = _next_profile_id(profiles)
    preset = fp_presets.pick_random()
    profile = {
        "name": name,
        "user_agent": preset["user_agent"],
        "fingerprint_preset": preset,
        "proxy": normalized_proxy,
        "extensions": list(extensions) if extensions else [],
        "timezone": timezone,
        "locale": locale,
        "geolocation": geolocation,
        "webrtc_protection": webrtc_protection,
        "fingerprint_noise": fingerprint_noise,
        "spoof_hardware": spoof_hardware,
        "hide_webdriver": hide_webdriver,
        "block_notifications": block_notifications,
        "start_url": start_url,
        "notes": notes or "",
        "created_at": datetime.now().isoformat(timespec="seconds"),
    }

    profiles[profile_id] = profile
    save_profiles(profiles)
    (BROWSER_DATA_DIR / profile_id).mkdir(exist_ok=True)
    return profile_id, profile

def update_profile(identifier: str, updates: dict) -> tuple[str, dict]:
    profiles = load_profiles()
    pid = _resolve_id(profiles, identifier)
    profile = profiles[pid]

    if "name" in updates and updates["name"] != profile["name"]:
        new_name = updates["name"].strip()
        if not new_name:
            raise ValueError(t("pm.name_empty"))
        if any(p["name"] == new_name for k, p in profiles.items() if k != pid):
            raise ValueError(t("pm.name_taken", name=new_name))
        profile["name"] = new_name

    if "proxy" in updates:
        profile["proxy"] = normalize_proxy_string(updates["proxy"]) if updates["proxy"] else None

    for key in (
        "user_agent", "extensions", "timezone", "locale", "geolocation",
        "webrtc_protection", "fingerprint_noise", "spoof_hardware",
        "hide_webdriver", "block_notifications",
        "start_url", "notes", "fingerprint_preset",
    ):
        if key in updates:
            profile[key] = updates[key]

    profiles[pid] = profile
    save_profiles(profiles)
    return pid, profile

def delete_profile(identifier: str) -> str:
    profiles = load_profiles()
    profile_id = _resolve_id(profiles, identifier)
    profiles.pop(profile_id)
    save_profiles(profiles)

    data_dir = BROWSER_DATA_DIR / profile_id
    if data_dir.exists():
        shutil.rmtree(data_dir, ignore_errors=True)
    return profile_id

def get_profile(identifier: str) -> tuple[str, dict]:
    profiles = load_profiles()
    profile_id = _resolve_id(profiles, identifier)
    return profile_id, _apply_defaults(profiles[profile_id])

def clone_profile(identifier: str, new_name: str, *, copy_session: bool = True) -> tuple[str, dict]:
    _ensure_dirs()
    profiles = load_profiles()
    src_id = _resolve_id(profiles, identifier)

    if any(p["name"] == new_name for p in profiles.values()):
        raise ValueError(t("pm.name_taken", name=new_name))

    new_id = _next_profile_id(profiles)
    cloned = dict(profiles[src_id])
    cloned["name"] = new_name
    cloned["created_at"] = datetime.now().isoformat(timespec="seconds")
    profiles[new_id] = cloned
    save_profiles(profiles)

    dst_dir = BROWSER_DATA_DIR / new_id
    src_dir = BROWSER_DATA_DIR / src_id
    if copy_session and src_dir.exists():
        shutil.copytree(src_dir, dst_dir, dirs_exist_ok=True, ignore=shutil.ignore_patterns(".lock"))
    else:
        dst_dir.mkdir(exist_ok=True)

    return new_id, cloned

def export_profile(identifier: str, dest_path: Path) -> Path:
    profiles = load_profiles()
    pid = _resolve_id(profiles, identifier)
    profile = profiles[pid]

    dest_path = Path(dest_path)
    if dest_path.is_dir():
        safe_name = "".join(c for c in profile["name"] if c.isalnum() or c in "-_")
        dest_path = dest_path / f"{pid}_{safe_name or 'profile'}.zip"

    dest_path.parent.mkdir(parents=True, exist_ok=True)
    src_dir = BROWSER_DATA_DIR / pid

    with zipfile.ZipFile(dest_path, "w", zipfile.ZIP_DEFLATED) as zf:
        meta = {"profile_id": pid, "profile": profile, "exported_at": datetime.now().isoformat(timespec="seconds")}
        zf.writestr("profile.json", json.dumps(meta, indent=2, ensure_ascii=False))
        if src_dir.exists():
            for root, _dirs, files in os.walk(src_dir):
                for f in files:
                    if f == ".lock":
                        continue
                    abs_path = Path(root) / f
                    rel = abs_path.relative_to(src_dir)
                    zf.write(abs_path, arcname=str(Path("browser_data") / rel))
    return dest_path

def import_profile(zip_path: Path, override_name: Optional[str] = None) -> tuple[str, dict]:
    _ensure_dirs()
    zip_path = Path(zip_path)
    if not zip_path.exists():
        raise FileNotFoundError(t("pm.file_not_found", path=zip_path))

    with zipfile.ZipFile(zip_path, "r") as zf:
        try:
            meta_bytes = zf.read("profile.json")
        except KeyError as exc:
            raise ValueError(t("pm.archive_no_meta")) from exc
        meta = json.loads(meta_bytes.decode("utf-8"))
        profile = meta["profile"]

        profiles = load_profiles()
        desired_name = (override_name or profile["name"]).strip()
        if not desired_name:
            raise ValueError(t("pm.new_name_empty"))

        if any(p["name"] == desired_name for p in profiles.values()):
            base = desired_name
            i = 2
            while any(p["name"] == f"{base}_{i}" for p in profiles.values()):
                i += 1
            desired_name = f"{base}_{i}"

        new_id = _next_profile_id(profiles)
        new_profile = dict(profile)
        new_profile["name"] = desired_name
        new_profile["created_at"] = datetime.now().isoformat(timespec="seconds")
        profiles[new_id] = _apply_defaults(new_profile)
        save_profiles(profiles)

        dst_dir = BROWSER_DATA_DIR / new_id
        dst_dir.mkdir(parents=True, exist_ok=True)
        dst_root = dst_dir.resolve()
        for member in zf.namelist():
            if not member.startswith("browser_data/") or member.endswith("/"):
                continue
            rel = Path(member).relative_to("browser_data")
            target = (dst_dir / rel).resolve()
            try:
                target.relative_to(dst_root)
            except ValueError:
                raise ValueError(t("pm.zip_slip", member=member))
            target.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(member) as src, target.open("wb") as dst:
                shutil.copyfileobj(src, dst)

    return new_id, profiles[new_id]

def _lock_path(profile_id: str) -> Path:
    return BROWSER_DATA_DIR / profile_id / ".lock"

def _pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    if sys.platform == "win32":
        try:
            import ctypes

            PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
            STILL_ACTIVE = 259
            kernel32 = ctypes.windll.kernel32
            handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
            if not handle:
                return False
            try:
                exit_code = ctypes.c_ulong()
                if not kernel32.GetExitCodeProcess(handle, ctypes.byref(exit_code)):
                    return False
                return exit_code.value == STILL_ACTIVE
            finally:
                kernel32.CloseHandle(handle)
        except Exception:
            return True
    else:
        try:
            os.kill(pid, 0)
            return True
        except OSError:
            return False
        except Exception:
            return True

def is_locked(profile_id: str, check_pid: bool = True) -> tuple[bool, Optional[int]]:
    path = _lock_path(profile_id)
    if not path.exists():
        return False, None
    pid: Optional[int] = None
    try:
        pid = int(path.read_text(encoding="utf-8").strip())
    except Exception:
        return True, None
    if check_pid and not _pid_alive(pid):
        return False, pid
    return True, pid

def acquire_lock(profile_id: str, check_pid: bool = True) -> bool:
    path = _lock_path(profile_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    locked, _pid = is_locked(profile_id, check_pid=check_pid)
    if locked:
        return False
    try:
        path.unlink(missing_ok=True)
    except Exception:
        pass
    path.write_text(str(os.getpid()), encoding="utf-8")
    return True

def release_lock(profile_id: str) -> None:
    try:
        _lock_path(profile_id).unlink(missing_ok=True)
    except Exception:
        pass

def clear_stale_locks() -> list[str]:
    cleared = []
    if not BROWSER_DATA_DIR.exists():
        return cleared
    for d in BROWSER_DATA_DIR.iterdir():
        if not d.is_dir():
            continue
        locked, _pid = is_locked(d.name, check_pid=True)
        if not locked and _lock_path(d.name).exists():
            release_lock(d.name)
            cleared.append(d.name)
    return cleared
