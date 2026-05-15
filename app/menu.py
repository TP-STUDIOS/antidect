import os
import sys
from pathlib import Path
from typing import Optional

import questionary
from prompt_toolkit.application import Application
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout import Layout
from prompt_toolkit.layout.containers import Window
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.styles import Style as PTStyle
from questionary import Choice, Separator, Style
from rich.align import Align
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

import browser_launcher
import i18n
import ip_geo
import profile_manager
import settings as app_settings
from i18n import t
from proxy_utils import check_alive as _check_proxy_alive, normalize_proxy_string

BANNER = r""" █████╗ ███╗   ██╗████████╗██╗██████╗ ███████╗████████╗███████╗ ██████╗████████╗
██╔══██╗████╗  ██║╚══██╔══╝██║██╔══██╗██╔════╝╚══██╔══╝██╔════╝██╔════╝╚══██╔══╝
███████║██╔██╗ ██║   ██║   ██║██║  ██║█████╗     ██║   █████╗  ██║        ██║
██╔══██║██║╚██╗██║   ██║   ██║██║  ██║██╔══╝     ██║   ██╔══╝  ██║        ██║
██║  ██║██║ ╚████║   ██║   ██║██████╔╝███████╗   ██║   ███████╗╚██████╗   ██║
╚═╝  ╚═╝╚═╝  ╚═══╝   ╚═╝   ╚═╝╚═════╝ ╚══════╝   ╚═╝   ╚══════╝ ╚═════╝   ╚═╝"""

BASE_DIR = Path(__file__).parent
console = Console()

MENU_STYLE = Style([
    ("qmark", "fg:#00d7ff bold"),
    ("question", "bold"),
    ("answer", "fg:#5fff87 bold"),
    ("pointer", "fg:#00d7ff bold"),
    ("highlighted", "fg:#00d7ff bold"),
    ("selected", "fg:#5fff87"),
    ("instruction", "fg:#808080 italic"),
])

_CONFIRM_STYLE = PTStyle.from_dict({
    "qmark": "#00d7ff bold",
    "question": "bold",
    "answer": "#5fff87 bold",
    "hint": "#808080 italic",
})

def _native_confirm(message: str, default: bool = False) -> Optional[bool]:
    answer = [default]

    def get_tokens():
        ans = t("confirm.yes") if answer[0] else t("confirm.no")
        return [
            ("class:qmark", "? "),
            ("class:question", message + "  "),
            ("class:answer", f"[{ans}]"),
            ("class:hint", "   " + t("confirm.hint")),
        ]

    kb = KeyBindings()

    def _yes_factory():
        def _h(event):
            event.app.exit(result=True)
        return _h

    def _no_factory():
        def _h(event):
            event.app.exit(result=False)
        return _h

    for k in ("y", "Y", "н", "Н"):
        kb.add(k, eager=True)(_yes_factory())
    for k in ("n", "N", "т", "Т"):
        kb.add(k, eager=True)(_no_factory())

    @kb.add("enter")
    def _enter(event):
        event.app.exit(result=answer[0])

    @kb.add("escape", eager=True)
    def _esc(event):
        event.app.exit(result=None)

    @kb.add("c-c", eager=True)
    def _ctrl_c(event):
        event.app.exit(result=None)

    app = Application(
        layout=Layout(
            Window(FormattedTextControl(get_tokens), height=1, always_hide_cursor=True)
        ),
        key_bindings=kb,
        style=_CONFIRM_STYLE,
    )
    try:
        return app.run()
    except KeyboardInterrupt:
        return None

class _ConfirmWrapper:
    def __init__(self, message: str, default: bool = False) -> None:
        self._message = message
        self._default = default

    def ask(self):
        return _native_confirm(self._message, self._default)

    def unsafe_ask(self):
        return self.ask()

def _patched_confirm(message: str, default: bool = False, **_kwargs):
    return _ConfirmWrapper(message, default)

questionary.confirm = _patched_confirm

_orig_select = questionary.select
_orig_checkbox = questionary.checkbox

_orig_text = questionary.text

def _add_esc_cancel(q):
    try:
        @q.application.key_bindings.add("escape", eager=True)
        def _esc(event):
            event.app.exit(result=None)
    except Exception:
        pass
    return q

def _patched_select(message, choices, *args, **kwargs):
    kwargs.setdefault("instruction", t("hint.use_arrows"))
    return _add_esc_cancel(_orig_select(message, choices, *args, **kwargs))

def _patched_checkbox(message, choices, *args, **kwargs):
    kwargs.setdefault("instruction", t("hint.checkbox"))
    return _add_esc_cancel(_orig_checkbox(message, choices, *args, **kwargs))

def _patched_text(message, *args, **kwargs):
    return _add_esc_cancel(_orig_text(message, *args, **kwargs))

questionary.select = _patched_select
questionary.checkbox = _patched_checkbox
questionary.text = _patched_text

BACK = "__back__"

def _hard_clear() -> None:
    os.system("cls" if sys.platform == "win32" else "clear")

def _header() -> None:
    _hard_clear()
    profiles = profile_manager.load_profiles()
    total = len(profiles)
    with_proxy = sum(1 for p in profiles.values() if p.get("proxy"))
    no_proxy = total - with_proxy
    ext_total = sum(len(p.get("extensions") or []) for p in profiles.values())

    banner = Text(BANNER, style="bold cyan")
    stats = Text.from_markup(
        f"[white]{t('stats.profiles')}:[/white] [bold]{total}[/bold]   "
        f"[white]{t('stats.with_proxy')}:[/white] [bold green]{with_proxy}[/bold green]   "
        f"[white]{t('stats.without_proxy')}:[/white] [bold yellow]{no_proxy}[/bold yellow]   "
        f"[white]{t('stats.extensions')}:[/white] [bold]{ext_total}[/bold]"
    )

    console.print(Panel(
        Align.center(banner),
        border_style="cyan",
        padding=(0, 1),
        subtitle="[dim]mini-antidetect[/dim]",
        subtitle_align="right",
    ))
    telegram = "Telegram: @TPStudioDev"
    credit_row = Table.grid(expand=True)
    credit_row.add_column(width=len(telegram))
    credit_row.add_column(justify="center", ratio=1)
    credit_row.add_column(width=len(telegram), justify="right", no_wrap=True)
    credit_row.add_row(
        "",
        "[dim cyan]──────[/dim cyan]  [bold #00d7ff]TPStudio[/bold #00d7ff]  [dim cyan]──────[/dim cyan]",
        f"[#00d7ff]{telegram}[/#00d7ff]",
    )
    console.print(credit_row)
    console.print(Align.center(stats))
    console.print(Align.center(Text(t("hint.nav"), style="dim italic")))
    console.print()

def _pause() -> None:
    questionary.press_any_key_to_continue(
        t("press_any_key"),
        style=MENU_STYLE,
    ).ask()

def _profile_flags(pid: str, p: dict) -> str:
    flags = []
    if p.get("timezone") or p.get("locale"):
        flags.append("[cyan]TZ[/cyan]")
    if p.get("geolocation"):
        flags.append("[magenta]GEO[/magenta]")
    locked, _ = profile_manager.is_locked(pid)
    if locked:
        flags.append("[bold red]LOCK[/bold red]")
    return " ".join(flags) or "—"

def _show_table(profiles: dict) -> None:
    table = Table(show_lines=False)
    table.add_column("ID", style="cyan", no_wrap=True)
    table.add_column("Имя", style="bold")
    table.add_column("Прокси")
    table.add_column("Локаль/TZ", style="dim")
    table.add_column("Ext", justify="right")
    table.add_column("Флаги")
    table.add_column("Создан", style="dim")
    for pid, p in profiles.items():
        loc_tz = p.get("locale") or "—"
        if p.get("timezone"):
            loc_tz = f"{loc_tz} / {p['timezone']}"
        table.add_row(
            pid,
            p["name"],
            p.get("proxy") or "—",
            loc_tz,
            str(len(p.get("extensions") or [])),
            Text.from_markup(_profile_flags(pid, p)),
            p.get("created_at", ""),
        )
    console.print(table)

def _available_extensions() -> list[str]:
    ext_dir = BASE_DIR / "extensions"
    ext_dir.mkdir(exist_ok=True)
    return sorted(d.name for d in ext_dir.iterdir() if d.is_dir())

def _pick_profile(question: str) -> Optional[str]:
    profiles = profile_manager.load_profiles()
    if not profiles:
        console.print(f"[yellow]{t('no_profiles')}[/yellow]")
        _pause()
        return None

    pid_w = max(len(pid) for pid in profiles.keys())
    name_w = max(len(p["name"]) for p in profiles.values())

    choices = []
    for pid, p in profiles.items():
        proxy = p.get("proxy") or "—"
        ext_count = len(p.get("extensions") or [])
        locked, _ = profile_manager.is_locked(pid)
        marker = " [LOCK]" if locked else ""
        title = (
            f"{pid:<{pid_w}}  │  "
            f"{p['name']:<{name_w}}  │  "
            f"proxy: {proxy}  │  "
            f"ext: {ext_count}{marker}"
        )
        choices.append(Choice(title=title, value=pid))
    choices.append(Choice(title=t("profiles.back"), value=BACK))

    pid = questionary.select(question, choices=choices, style=MENU_STYLE).ask()
    if pid is None or pid == BACK:
        return None
    return pid

def _ask_proxy(initial: Optional[str] = None) -> Optional[str]:
    def _validate(v: str):
        if not v.strip():
            return True
        try:
            normalize_proxy_string(v)
            return True
        except ValueError as e:
            return str(e)

    proxy = questionary.text(
        t("create.proxy_prompt"),
        default=initial or "",
        validate=_validate,
        style=MENU_STYLE,
    ).ask()
    if proxy is None or not proxy.strip():
        return None
    proxy = proxy.strip()

    if "://" in proxy:
        scheme = proxy.split("://", 1)[0].lower()
        if scheme not in ("http", "https", "socks5", "socks5h"):
            scheme = "http"
        rest = proxy
    else:
        picked = questionary.select(
            t("proxy.scheme_picker"),
            choices=[
                Choice(title=t("proxy.scheme.http"), value="http"),
                Choice(title=t("proxy.scheme.socks5"), value="socks5"),
            ],
            style=MENU_STYLE,
            use_indicator=False,
            qmark="›",
        ).ask()
        if picked is None:
            return None
        scheme = picked
        rest = proxy

    if "://" in rest:
        body = rest.split("://", 1)[1]
        has_auth = "@" in body
    elif "@" in rest:
        has_auth = True
    else:
        has_auth = len(rest.split(":")) >= 4
    if scheme == "socks5" and has_auth:
        console.print(f"[red]✗[/red] {t('create.socks5_auth_unsupported')}")
        _pause()
        return None

    console.print(f"[dim]{t('create.proxy_checking')}[/dim]")
    schemes_to_try = ("http", "https") if scheme == "http" else (scheme,)
    if "://" in rest:
        schemes_to_try = (scheme,)

    for try_scheme in schemes_to_try:
        candidate = normalize_proxy_string(rest, default_scheme=try_scheme)
        alive, _ = _check_proxy_alive(candidate, timeout=4.0)
        if alive:
            console.print(
                f"[green]{t('ok')} {t('create.proxy_alive')}[/green] "
                f"[dim]({try_scheme.upper()})[/dim]"
            )
            return candidate

    console.print(f"[yellow]{t('create.proxy_dead')}[/yellow]")
    keep = questionary.confirm(
        t("create.proxy_use_anyway"), default=False, style=MENU_STYLE
    ).ask()
    return normalize_proxy_string(rest, default_scheme=scheme) if keep else None

def _maybe_attach_geo(proxy: Optional[str]) -> dict:
    s = app_settings.load_settings()
    if not s.get("auto_geolocate_proxy"):
        return {}
    do_it = questionary.confirm(
        t("create.auto_geo") + ("" if proxy else t("create.auto_geo.no_proxy_hint")),
        default=True,
        style=MENU_STYLE,
    ).ask()
    if not do_it:
        return {}

    console.print(f"[dim]{t('create.geo_query')}[/dim]")
    info = ip_geo.lookup(proxy, timeout=int(s.get("lookup_timeout_seconds", 5)))
    if not info or info.get("error"):
        err = info.get("error") if info else "no response"
        console.print(f"[yellow]{t('create.geo_failed')}[/yellow] {err}")
        return {}

    console.print(
        f"[green]{t('create.geo_detected')}[/green] IP=[bold]{info['ip']}[/bold]  "
        f"country=[bold]{info['country']}[/bold]  "
        f"TZ=[bold]{info['timezone']}[/bold]  "
        f"locale=[bold]{info['locale']}[/bold]"
    )
    accept = questionary.confirm(
        t("create.geo_apply"), default=True, style=MENU_STYLE
    ).ask()
    if not accept:
        return {}

    return {
        "timezone": info["timezone"],
        "locale": info["locale"],
        "geolocation": {
            "latitude": info["latitude"],
            "longitude": info["longitude"],
            "accuracy": 100,
        },
    }

def list_action() -> None:
    _header()
    profiles = profile_manager.load_profiles()
    if not profiles:
        console.print(f"[yellow]{t('no_profiles_create')}[/yellow]")
    else:
        _show_table(profiles)
    console.print()
    _pause()

def create_action() -> None:
    _header()
    profiles = profile_manager.load_profiles()
    existing_names = {p["name"] for p in profiles.values()}

    def _validate_name(v: str):
        v = v.strip()
        if v and v in existing_names:
            return t("create.name.taken")
        return True

    name = questionary.text(
        t("create.name"), validate=_validate_name, style=MENU_STYLE,
    ).ask()
    if not name or not name.strip():
        return
    name = name.strip()

    use_proxy = questionary.confirm(
        t("create.use_proxy"), default=False, style=MENU_STYLE
    ).ask()
    proxy = None
    if use_proxy:
        proxy = _ask_proxy()
        if proxy is None:
            return

    geo_info = _maybe_attach_geo(proxy)

    available = _available_extensions()
    extensions: list[str] = []
    if available:
        load_ext = questionary.confirm(
            t("create.ext_load", n=len(available)),
            default=False,
            style=MENU_STYLE,
        ).ask()
        if load_ext:
            extensions = questionary.checkbox(
                t("create.ext_pick"),
                choices=available,
                style=MENU_STYLE,
            ).ask() or []
    else:
        console.print(f"[dim]{t('create.ext_empty')}[/dim]")

    try:
        profile_id, profile = profile_manager.create_profile(
            name,
            proxy=proxy,
            extensions=extensions,
            timezone=geo_info.get("timezone"),
            locale=geo_info.get("locale"),
            geolocation=geo_info.get("geolocation"),
        )
    except ValueError as e:
        console.print(f"[red]{t('create.error')}[/red] {e}")
        _pause()
        return

    console.print(
        f"\n[green]{t('ok')}[/green] {t('create.created')} [bold]{profile_id}[/bold] ({profile['name']})"
    )
    console.print(f"  UA: {profile['user_agent']}")
    console.print(f"  proxy: {profile['proxy'] or '—'}")
    console.print(f"  ext: {', '.join(profile['extensions']) or '—'}")
    if profile.get("timezone"):
        console.print(f"  TZ: {profile['timezone']}  ·  locale: {profile.get('locale') or '—'}")
    _pause()

def _bulk_run_action() -> None:
    import subprocess
    import sys as _sys

    _header()
    profiles = profile_manager.load_profiles()
    if not profiles:
        console.print(f"[yellow]{t('no_profiles')}[/yellow]")
        _pause()
        return

    choices = [
        Choice(
            title=f"{pid}  ·  {p['name']}  ·  proxy: {p.get('proxy') or '—'}",
            value=pid,
        )
        for pid, p in profiles.items()
    ]
    picked = questionary.checkbox(
        t("bulk.choose"),
        choices=choices,
        style=MENU_STYLE,
    ).ask()
    if not picked:
        return

    main_py = str(BASE_DIR.parent / "main.py")
    flags = 0
    if _sys.platform == "win32":
        flags = subprocess.CREATE_NEW_CONSOLE
    started = 0
    for pid in picked:
        try:
            subprocess.Popen(
                [_sys.executable, main_py, pid],
                cwd=str(BASE_DIR.parent),
                creationflags=flags,
            )
            started += 1
        except Exception as e:
            console.print(f"[red]{pid}:[/red] {e}")
    console.print(f"[green]{t('ok')}[/green] {t('bulk.started')} {started}/{len(picked)}")
    _pause()

def run_action() -> None:
    _header()
    profiles = profile_manager.load_profiles()
    if not profiles:
        console.print(f"[yellow]{t('no_profiles')}[/yellow]")
        _pause()
        return

    pid_w = max(len(pid) for pid in profiles.keys())
    name_w = max(len(p["name"]) for p in profiles.values())

    choices: list = []
    choices.append(Choice(
        title=t("pick.run.bulk"),
        value="__bulk",
    ))
    choices.append(Separator(" "))
    for pid, p in profiles.items():
        proxy = p.get("proxy") or "—"
        ext_count = len(p.get("extensions") or [])
        locked, _ = profile_manager.is_locked(pid)
        marker = " [LOCK]" if locked else ""
        title = (
            f"{pid:<{pid_w}}  │  "
            f"{p['name']:<{name_w}}  │  "
            f"proxy: {proxy}  │  "
            f"ext: {ext_count}{marker}"
        )
        choices.append(Choice(title=title, value=pid))
    choices.append(Choice(title=t("profiles.back"), value=BACK))

    pid = questionary.select(
        t("pick.run"),
        choices=choices,
        style=MENU_STYLE,
    ).ask()
    if not pid or pid == BACK:
        return
    if pid == "__bulk":
        _bulk_run_action()
        return

    _, profile = profile_manager.get_profile(pid)
    console.print("\n" + t("run.starting", name=profile["name"], id=pid))
    try:
        browser_launcher.launch_profile(pid, profile, BASE_DIR)
    except Exception as e:
        console.print(f"[red]{t('run.error')}[/red] {e}")
    _pause()

def delete_action() -> None:
    _header()
    pid = _pick_profile(t("pick.delete"))
    if not pid:
        return
    _, profile = profile_manager.get_profile(pid)
    confirm = questionary.confirm(
        t("delete.confirm", name=profile["name"], id=pid),
        default=False,
        style=MENU_STYLE,
    ).ask()
    if not confirm:
        return
    profile_manager.delete_profile(pid)
    console.print(f"[green]{t('ok')}[/green] {t('delete.done')} {pid}")
    _pause()

def clone_action() -> None:
    _header()
    pid = _pick_profile(t("pick.clone"))
    if not pid:
        return

    profiles = profile_manager.load_profiles()
    existing_names = {p["name"] for p in profiles.values()}
    _, src = profile_manager.get_profile(pid)

    def _validate_name(v: str):
        v = v.strip()
        if v and v in existing_names:
            return t("create.name.taken")
        return True

    new_name = questionary.text(
        t("clone.name"),
        default=f"{src['name']}_copy",
        validate=_validate_name,
        style=MENU_STYLE,
    ).ask()
    if not new_name or not new_name.strip():
        return

    copy_session = questionary.confirm(
        t("clone.copy_session"),
        default=True,
        style=MENU_STYLE,
    ).ask()

    try:
        new_id, new_profile = profile_manager.clone_profile(
            pid, new_name.strip(), copy_session=copy_session
        )
    except ValueError as e:
        console.print(f"[red]{t('create.error')}[/red] {e}")
        _pause()
        return

    console.print(
        f"[green]{t('ok')}[/green] "
        + t("clone.done", src=pid, dst=new_id, name=new_profile["name"])
    )
    _pause()

def edit_action() -> None:
    _header()
    pid = _pick_profile(t("pick.edit"))
    if not pid:
        return

    while True:
        _, profile = profile_manager.get_profile(pid)
        console.print(Panel.fit(
            Text.from_markup(
                f"[bold]{profile['name']}[/bold] ({pid})\n"
                f"proxy: {profile.get('proxy') or '—'}\n"
                f"TZ: {profile.get('timezone') or '—'}   locale: {profile.get('locale') or '—'}\n"
                f"start_url: {profile.get('start_url') or '—'}\n"
                f"extensions: {', '.join(profile.get('extensions') or []) or '—'}\n"
                f"notes: {profile.get('notes') or '—'}"
            ),
            border_style="cyan",
            title=t("edit.title"),
        ))

        choice = questionary.select(
            t("edit.what"),
            choices=[
                Choice(title=t("edit.name"), value="name"),
                Choice(title=t("edit.proxy"), value="proxy"),
                Choice(title=t("edit.ua"), value="ua"),
                Choice(title=t("edit.start_url"), value="start_url"),
                Choice(title=t("edit.notes"), value="notes"),
                Choice(title=t("edit.extensions"), value="extensions"),
                Choice(title=t("edit.geo"), value="geo"),
                Choice(title=t("edit.toggles"), value="toggles"),
                Choice(title=t("edit.back"), value=BACK),
            ],
            style=MENU_STYLE,
        ).ask()
        if choice is None or choice == BACK:
            return

        try:
            if choice == "name":
                profiles = profile_manager.load_profiles()
                existing = {p["name"] for k, p in profiles.items() if k != pid}

                def _vn(v: str):
                    v = v.strip()
                    if v and v in existing:
                        return t("create.name.taken")
                    return True

                v = questionary.text(
                    t("edit.new_name"), default=profile["name"], validate=_vn, style=MENU_STYLE
                ).ask()
                if v and v.strip():
                    profile_manager.update_profile(pid, {"name": v.strip()})

            elif choice == "proxy":
                kill = questionary.confirm(
                    t("edit.kill_proxy"), default=False, style=MENU_STYLE
                ).ask()
                if kill:
                    profile_manager.update_profile(pid, {"proxy": None})
                else:
                    v = _ask_proxy(profile.get("proxy"))
                    if v is not None:
                        profile_manager.update_profile(pid, {"proxy": v})

            elif choice == "ua":
                if questionary.confirm(
                    t("edit.regen_ua"),
                    default=True, style=MENU_STYLE,
                ).ask():
                    preset = profile_manager.random_fingerprint_preset()
                    profile_manager.update_profile(pid, {
                        "user_agent": preset["user_agent"],
                        "fingerprint_preset": preset,
                    })
                    console.print(
                        f"[green]{t('edit.new_fp')}[/green] {preset['os']}  ·  "
                        f"{preset['screen_width']}×{preset['screen_height']}"
                    )
                    console.print(f"[dim]{preset['user_agent']}[/dim]")

            elif choice == "start_url":
                v = questionary.text(
                    t("edit.start_url_prompt"),
                    default=profile.get("start_url") or "",
                    style=MENU_STYLE,
                ).ask()
                if v is not None:
                    profile_manager.update_profile(pid, {"start_url": v.strip() or None})

            elif choice == "notes":
                v = questionary.text(
                    t("edit.notes_prompt"),
                    default=profile.get("notes") or "",
                    style=MENU_STYLE,
                ).ask()
                if v is not None:
                    profile_manager.update_profile(pid, {"notes": v or ""})

            elif choice == "extensions":
                available = _available_extensions()
                if not available:
                    console.print(f"[yellow]{t('edit.no_extensions_dir')}[/yellow]")
                else:
                    current = set(profile.get("extensions") or [])
                    picked = questionary.checkbox(
                        t("edit.choose_ext"),
                        choices=[
                            Choice(title=e, value=e, checked=(e in current))
                            for e in available
                        ],
                        style=MENU_STYLE,
                    ).ask()
                    if picked is not None:
                        profile_manager.update_profile(pid, {"extensions": picked})

            elif choice == "geo":
                geo = _maybe_attach_geo(profile.get("proxy"))
                if geo:
                    profile_manager.update_profile(pid, geo)
                else:
                    clear = questionary.confirm(
                        t("edit.clear_geo"),
                        default=False, style=MENU_STYLE,
                    ).ask()
                    if clear:
                        profile_manager.update_profile(pid, {
                            "timezone": None, "locale": None, "geolocation": None,
                        })

            elif choice == "toggles":
                _edit_profile_toggles(pid)

        except (ValueError, KeyError) as e:
            console.print(f"[red]{t('edit.error')}[/red] {e}")
        _pause()

def _edit_profile_toggles(pid: str) -> None:
    keys = (
        "webrtc_protection",
        "fingerprint_noise",
        "spoof_hardware",
        "hide_webdriver",
        "block_notifications",
    )
    last_value = None

    while True:
        _header()
        _, profile = profile_manager.get_profile(pid)
        eff = app_settings.effective_for_profile(profile)

        console.print(Panel.fit(
            Text.from_markup(
                f"[bold]{profile['name']}[/bold]  ({pid})\n"
                f"[dim]{t('ptog.help')}[/dim]"
            ),
            border_style="cyan",
            title=t("ptog.title"),
        ))

        choices: list = []
        for k in keys:
            on = bool(eff.get(k))
            origin = t("ptog.origin.profile") if profile.get(k) is not None else t("ptog.origin.global")
            mark = f"[{t('toggle.on')}]" if on else f"[{t('toggle.off')}]"
            choices.append(Choice(
                title=f" {mark}  ({origin})  {i18n.toggle_label(k)}",
                value=("toggle", k),
            ))
        choices.append(Separator(" "))
        choices.append(Choice(title=t("ptog.reset"), value=("reset", None)))
        choices.append(Choice(title=t("done"), value=("back", None)))

        default = None
        if last_value is not None:
            for c in choices:
                if isinstance(c, Choice) and c.value == last_value:
                    default = c.value
                    break

        choice = questionary.select(
            t("ptog.toggle"),
            choices=choices,
            default=default,
            style=MENU_STYLE,
            use_indicator=False,
            qmark="›",
        ).ask()
        if choice is None:
            return

        kind, key = choice
        if kind == "back":
            return
        last_value = choice
        if kind == "toggle":
            new_v = not bool(eff.get(key))
            profile_manager.update_profile(pid, {key: new_v})
        elif kind == "reset":
            profile_manager.update_profile(pid, {k: None for k in keys})

def export_action() -> None:
    _header()
    pid = _pick_profile(t("pick.export"))
    if not pid:
        return

    default_dir = str(BASE_DIR / "exports")
    (BASE_DIR / "exports").mkdir(exist_ok=True)
    path_str = questionary.text(
        t("export.where"),
        default=default_dir,
        style=MENU_STYLE,
    ).ask()
    if not path_str or not path_str.strip():
        return
    try:
        dest = profile_manager.export_profile(pid, Path(path_str))
        console.print(f"[green]{t('ok')}[/green] {t('export.done')} [bold]{dest}[/bold]")
    except Exception as e:
        console.print(f"[red]{t('export.error')}[/red] {e}")
    _pause()

def import_action() -> None:
    _header()
    path_str = questionary.text(
        t("import.zip_path"),
        style=MENU_STYLE,
    ).ask()
    if not path_str or not path_str.strip():
        return
    path = Path(path_str.strip().strip('"'))
    if not path.exists():
        console.print(f"[red]{t('import.not_found')}[/red] {path}")
        _pause()
        return

    rename = questionary.text(
        t("import.new_name"),
        style=MENU_STYLE,
    ).ask()
    try:
        new_id, prof = profile_manager.import_profile(path, override_name=rename or None)
        console.print(
            f"[green]{t('ok')}[/green] {t('import.done')} [bold]{new_id}[/bold] ({prof['name']})"
        )
    except Exception as e:
        console.print(f"[red]{t('import.error')}[/red] {e}")
    _pause()

def _toggle_title(on: bool, label: str) -> str:
    mark = f"[{t('toggle.on')}]" if on else f"[{t('toggle.off')}]"
    return f" {mark}  {label}"

def settings_action() -> None:
    last_value = None
    while True:
        _header()
        s = app_settings.load_settings()

        lang_label = dict(app_settings.LANGUAGES).get(s.get("language"), "English")
        browser_label = dict(app_settings.BROWSERS).get(s.get("browser_type"), "Firefox")

        choices: list = []
        choices.append(Choice(
            title=f"  {t('settings.language')}: {lang_label}",
            value=("lang", None),
        ))
        choices.append(Choice(
            title=f"  {t('settings.browser')}: {browser_label}",
            value=("browser", None),
        ))
        choices.append(Separator(" "))
        for k in app_settings.TOGGLEABLE_KEYS:
            choices.append(Choice(
                title=_toggle_title(bool(s.get(k)), i18n.toggle_label(k)),
                value=("toggle", k),
            ))
        choices.append(Separator(" "))
        choices.append(Choice(
            title=t("settings.window_size", w=s.get("viewport_width"), h=s.get("viewport_height")),
            value=("size", None),
        ))
        choices.append(Choice(
            title=t("settings.lookup_timeout", s=s.get("lookup_timeout_seconds")),
            value=("int", "lookup_timeout_seconds"),
        ))
        choices.append(Separator(" "))
        choices.append(Choice(title=t("settings.clear_locks"), value=("action", "clear_locks")))
        choices.append(Choice(title=t("profiles.back"), value=("back", None)))

        default = None
        if last_value is not None:
            for c in choices:
                if isinstance(c, Choice) and c.value == last_value:
                    default = c.value
                    break

        choice = questionary.select(
            t("settings.title"),
            choices=choices,
            default=default,
            style=MENU_STYLE,
            use_indicator=False,
            qmark="›",
        ).ask()
        if choice is None:
            return

        kind, key = choice
        if kind == "back":
            return
        last_value = choice
        if kind == "toggle":
            app_settings.set_value(key, not s.get(key))
        elif kind == "lang":
            picked = questionary.select(
                t("settings.lang_picker"),
                choices=[Choice(title=label, value=code) for code, label in app_settings.LANGUAGES],
                default=s.get("language") or "en",
                style=MENU_STYLE,
                use_indicator=False,
                qmark="›",
            ).ask()
            if picked is not None:
                app_settings.set_value("language", picked)
        elif kind == "browser":
            picked = questionary.select(
                t("settings.browser_picker"),
                choices=[Choice(title=label, value=code) for code, label in app_settings.BROWSERS],
                default=s.get("browser_type") or "firefox",
                style=MENU_STYLE,
                use_indicator=False,
                qmark="›",
            ).ask()
            if picked is not None:
                app_settings.set_value("browser_type", picked)
        elif kind == "size":
            def _vi(v: str):
                if not v.strip():
                    return True
                try:
                    n = int(v)
                    return True if n > 0 else t("settings.must_positive")
                except ValueError:
                    return t("settings.must_number")
            w = questionary.text(
                t("settings.width"), default=str(s.get("viewport_width")),
                validate=_vi, style=MENU_STYLE,
            ).ask()
            if not w or not w.strip():
                continue
            h = questionary.text(
                t("settings.height"), default=str(s.get("viewport_height")),
                validate=_vi, style=MENU_STYLE,
            ).ask()
            if not h or not h.strip():
                continue
            app_settings.set_value("viewport_width", int(w))
            app_settings.set_value("viewport_height", int(h))
        elif kind == "int":
            def _vi(v: str):
                if not v.strip():
                    return True
                try:
                    int(v)
                    return True
                except ValueError:
                    return t("settings.must_number")
            v = questionary.text(
                f"{key}:", default=str(s.get(key) or 0),
                validate=_vi, style=MENU_STYLE,
            ).ask()
            if v and v.strip():
                app_settings.set_value(key, int(v))
        elif kind == "action" and key == "clear_locks":
            cleared = profile_manager.clear_stale_locks()
            console.print(f"[green]{t('ok')}[/green] {t('settings.cleared')} {len(cleared)}")
            _pause()

def profiles_menu() -> None:
    actions = {
        "list": list_action,
        "create": create_action,
        "edit": edit_action,
        "clone": clone_action,
        "import": import_action,
        "export": export_action,
        "delete": delete_action,
    }
    while True:
        _header()
        choice = questionary.select(
            t("profiles.title"),
            choices=[
                Choice(title=t("profiles.list"), value="list"),
                Choice(title=t("profiles.create"), value="create"),
                Choice(title=t("profiles.edit"), value="edit"),
                Choice(title=t("profiles.clone"), value="clone"),
                Separator(" "),
                Choice(title=t("profiles.import"), value="import"),
                Choice(title=t("profiles.export"), value="export"),
                Separator(" "),
                Choice(title=t("profiles.delete"), value="delete"),
                Choice(title=t("profiles.back"), value=BACK),
            ],
            style=MENU_STYLE,
            use_indicator=False,
            qmark="›",
        ).ask()
        if choice is None or choice == BACK:
            return
        try:
            actions[choice]()
        except KeyboardInterrupt:
            continue

def run() -> None:
    _hard_clear()
    s = app_settings.load_settings()
    if s.get("auto_clear_stale_locks"):
        cleared = profile_manager.clear_stale_locks()
        if cleared:
            console.print(f"[dim]{t('stale_lock_cleared')} {', '.join(cleared)}[/dim]")

    while True:
        _header()
        choice = questionary.select(
            t("menu.title"),
            choices=[
                Choice(title=t("menu.run"), value="run"),
                Choice(title=t("menu.profiles"), value="profiles"),
                Choice(title=t("menu.settings"), value="settings"),
                Separator(" "),
                Choice(title=t("menu.exit"), value="__exit__"),
            ],
            style=MENU_STYLE,
            use_indicator=False,
            qmark="›",
        ).ask()
        if choice is None or choice == "__exit__":
            console.print(f"[dim]{t('menu.bye')}[/dim]")
            return
        try:
            if choice == "run":
                run_action()
            elif choice == "profiles":
                profiles_menu()
            elif choice == "settings":
                settings_action()
        except KeyboardInterrupt:
            continue
