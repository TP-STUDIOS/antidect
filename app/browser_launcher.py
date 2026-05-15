import json
import subprocess
import sys
import time
from pathlib import Path
from urllib.parse import urlparse

from playwright.sync_api import sync_playwright

import applog
import fingerprint
import profile_manager
import settings as app_settings
from http_auth_relay import HttpAuthRelay
from i18n import t
from proxy_utils import to_playwright_proxy

log = applog.get("launcher")

DEFAULT_START_URL = "https://2ip.ru/"
BLANK_URLS = (
    "about:blank",
    "chrome://newtab/",
    "chrome://new-tab-page/",
    "about:newtab",
    "about:home",
)

def _ensure_browser_installed(browser_type: str) -> None:
    path: Path | None = None
    try:
        with sync_playwright() as p:
            br = getattr(p, browser_type, None)
            if br is not None:
                exe = br.executable_path
                if exe:
                    path = Path(exe)
    except Exception:
        pass
    if path and path.exists():
        return

    print(f"⏳ Installing {browser_type} (~100 MB, one-time)...")
    log.info("installing playwright browser: %s", browser_type)
    try:
        result = subprocess.run(
            [sys.executable, "-m", "playwright", "install", browser_type],
            timeout=900,
        )
        if result.returncode != 0:
            raise RuntimeError(f"`playwright install {browser_type}` returned {result.returncode}")
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"`playwright install {browser_type}` timed out (>15 min)")
    print(f"✓ {browser_type} installed")
    log.info("installed %s", browser_type)

def _ensure_session_restore(user_data_dir: Path) -> bool:
    prefs_path = user_data_dir / "Default" / "Preferences"
    first_launch = not prefs_path.exists()

    prefs: dict = {}
    if not first_launch:
        try:
            prefs = json.loads(prefs_path.read_text(encoding="utf-8"))
        except Exception:
            prefs = {}

    session = prefs.setdefault("session", {})
    session["restore_on_startup"] = 1
    session["startup_urls"] = []

    profile_section = prefs.setdefault("profile", {})
    profile_section["exit_type"] = "Normal"
    profile_section["exited_cleanly"] = True

    prefs_path.parent.mkdir(parents=True, exist_ok=True)
    prefs_path.write_text(json.dumps(prefs, ensure_ascii=False), encoding="utf-8")
    return first_launch

def _unpack_crx_files(extensions_dir: Path) -> None:
    import zipfile

    for crx in extensions_dir.glob("*.crx"):
        target = extensions_dir / crx.stem
        if target.exists():
            continue
        try:
            with zipfile.ZipFile(crx) as zf:
                zf.extractall(target)
        except Exception as e:
            print(f"⚠ Cannot unpack {crx.name}: {e}")

def _collect_extensions(
    extensions_dir: Path, names: list[str]
) -> tuple[list[str], list[str]]:
    _unpack_crx_files(extensions_dir)
    found, missing = [], []
    for name in names or []:
        path = extensions_dir / name
        if path.exists() and path.is_dir():
            found.append(str(path.resolve()))
        else:
            missing.append(name)
    return found, missing

def _languages_from_locale(locale: str | None) -> list[str] | None:
    if not locale:
        return None
    primary = locale.replace("_", "-")
    base = primary.split("-")[0]
    if primary == base:
        return [primary]
    return [primary, base]

def launch_profile(profile_id: str, profile: dict, base_dir: Path) -> None:
    log.info("launch start: id=%s name=%s proxy=%s", profile_id, profile.get("name"), bool(profile.get("proxy")))
    eff = app_settings.effective_for_profile(profile)
    browser_type = (profile.get("browser_type") or eff.get("browser_type") or "firefox").lower()
    if browser_type not in ("firefox", "chromium"):
        browser_type = "firefox"
    is_firefox = browser_type == "firefox"

    _ensure_browser_installed(browser_type)

    user_data_dir = base_dir / "browser_data" / profile_id
    user_data_dir.mkdir(parents=True, exist_ok=True)

    if not profile_manager.acquire_lock(
        profile_id, check_pid=eff.get("lock_check_pid", True)
    ):
        _locked, pid = profile_manager.is_locked(profile_id)
        raise RuntimeError(t("launcher.locked", pid=pid))

    auth_relay: HttpAuthRelay | None = None
    try:
        extensions_dir = base_dir / "extensions"
        extensions_dir.mkdir(exist_ok=True)
        ext_paths, missing = _collect_extensions(
            extensions_dir, profile.get("extensions") or []
        )
        for name in missing:
            print(f"⚠ {t('launcher.ext_missing')} {name}")

        if is_firefox:
            first_launch = not any(user_data_dir.glob("*"))
        else:
            first_launch = _ensure_session_restore(user_data_dir)

        proxy_dict = to_playwright_proxy(profile.get("proxy"))

        if (
            proxy_dict
            and proxy_dict.get("server", "").startswith(("http://", "https://"))
            and (proxy_dict.get("username") or proxy_dict.get("password"))
        ):
            from urllib.parse import urlparse as _urlp
            up = _urlp(proxy_dict["server"])
            auth_relay = HttpAuthRelay(
                up.hostname, up.port,
                proxy_dict.get("username", ""),
                proxy_dict.get("password", ""),
                upstream_scheme=up.scheme,
            )
            local_port = auth_relay.start()
            log.info("started HTTP auth-injection relay on 127.0.0.1:%d (upstream %s)", local_port, proxy_dict["server"])
            proxy_dict = {"server": f"http://127.0.0.1:{local_port}"}

        args: list[str] = []
        if not is_firefox:
            args = fingerprint.build_chromium_args(eff)
            args.append("--restore-last-session")
            if ext_paths:
                joined = ",".join(ext_paths)
                args.append(f"--disable-extensions-except={joined}")
                args.append(f"--load-extension={joined}")
            if proxy_dict and proxy_dict.get("server", "").startswith("socks"):
                args.append("--disable-quic")

        ctx_kwargs: dict = dict(
            user_data_dir=str(user_data_dir.resolve()),
            headless=False,
            proxy=proxy_dict,
            args=args,
            viewport={
                "width": int(eff.get("viewport_width", 1280)),
                "height": int(eff.get("viewport_height", 800)),
            },
            accept_downloads=True,
        )
        if not is_firefox:
            ctx_kwargs["user_agent"] = profile.get("user_agent")
        if profile.get("timezone"):
            ctx_kwargs["timezone_id"] = profile["timezone"]
        if profile.get("locale"):
            ctx_kwargs["locale"] = profile["locale"]
        geo = profile.get("geolocation")
        if geo and geo.get("latitude") is not None and geo.get("longitude") is not None:
            ctx_kwargs["geolocation"] = {
                "latitude": float(geo["latitude"]),
                "longitude": float(geo["longitude"]),
                "accuracy": float(geo.get("accuracy", 100)),
            }
            ctx_kwargs["permissions"] = ["geolocation"]

        if is_firefox:
            ctx_kwargs["firefox_user_prefs"] = {
                "browser.startup.page": 3,
                "browser.sessionstore.enabled": True,
                "browser.sessionstore.resume_from_crash": True,
                "browser.sessionstore.restore_on_demand": False,
                "network.proxy.socks_remote_dns": True,
                "privacy.resistFingerprinting": False,
                "dom.webdriver.enabled": False,
                "useAutomationExtension": False,
                "media.peerconnection.enabled": not bool(eff.get("webrtc_protection")),
            }

        start_url = (
            profile.get("start_url")
            or eff.get("default_start_url")
            or DEFAULT_START_URL
        )
        target_host = urlparse(start_url).hostname

        languages = _languages_from_locale(profile.get("locale"))
        init_script = fingerprint.build_init_script(
            profile_id, eff,
            languages=languages,
            preset=profile.get("fingerprint_preset"),
            browser_type=browser_type,
        )

        print(t("launcher.starting_chromium"))
        with sync_playwright() as p:
            browser_inst = getattr(p, browser_type)
            context = browser_inst.launch_persistent_context(**ctx_kwargs)
            if init_script.strip():
                context.add_init_script(init_script)
            print(t("launcher.chromium_up", n=len(context.pages)))

            existing_target: list = []
            for page in list(context.pages):
                try:
                    if urlparse(page.url).hostname == target_host:
                        existing_target.append(page)
                except Exception:
                    pass

            if existing_target:
                main_page = existing_target[0]
                for extra in existing_target[1:]:
                    try:
                        extra.close()
                    except Exception:
                        pass
            else:
                main_page = context.new_page()

            try:
                try:
                    main_page.goto(start_url, wait_until="commit", timeout=8000)
                except TypeError:
                    main_page.goto(start_url, wait_until="domcontentloaded", timeout=8000)
            except Exception as e:
                print(t("launcher.url_failed", url=start_url, err=type(e).__name__))
            try:
                main_page.bring_to_front()
            except Exception:
                pass

            if len(context.pages) > 1:
                for page in list(context.pages):
                    if page is main_page:
                        continue
                    try:
                        if page.url in BLANK_URLS:
                            page.close()
                    except Exception:
                        pass

            if not first_launch and eff.get("reload_restored_tabs"):
                reloaded = 0
                for page in list(context.pages):
                    if page is main_page:
                        continue
                    try:
                        url = page.url
                    except Exception:
                        continue
                    if not url or url in BLANK_URLS:
                        continue
                    try:
                        try:
                            page.reload(wait_until="commit", timeout=8000)
                        except TypeError:
                            page.reload(wait_until="domcontentloaded", timeout=8000)
                        reloaded += 1
                    except Exception:
                        pass
                if reloaded:
                    log.info("reloaded %d restored tabs for init-script consistency", reloaded)

            kind = t("launcher.kind.first") if first_launch else t("launcher.kind.restored")
            print(t("launcher.running", name=profile["name"], kind=kind, url=start_url))

            try:
                while True:
                    try:
                        pages = context.pages
                    except Exception:
                        break
                    if not pages:
                        break
                    time.sleep(1)
            except KeyboardInterrupt:
                pass
            finally:
                try:
                    context.close()
                except Exception:
                    pass
    finally:
        try:
            if auth_relay is not None:
                auth_relay.stop()
        except Exception:
            pass
        profile_manager.release_lock(profile_id)
        log.info("launch end: id=%s", profile_id)
