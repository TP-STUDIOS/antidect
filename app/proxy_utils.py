import socket
import urllib.request
from typing import Optional
from urllib.parse import urlparse

def normalize_proxy_string(raw: Optional[str], default_scheme: str = "http") -> Optional[str]:
    if not raw:
        return None
    raw = raw.strip()
    if not raw:
        return None

    if "://" in raw:
        return raw

    if "@" in raw:
        creds, _, host_port = raw.rpartition("@")
        if ":" not in host_port or ":" not in creds:
            raise ValueError(
                "Прокси с @ должен быть в формате user:pass@host:port"
            )
        host, port = host_port.rsplit(":", 1)
        user, _, password = creds.partition(":")
        return f"{default_scheme}://{user}:{password}@{host}:{port}"

    parts = raw.split(":")
    if len(parts) == 4:
        ip, port, user, password = parts
        return f"{default_scheme}://{user}:{password}@{ip}:{port}"
    if len(parts) == 2:
        ip, port = parts
        return f"{default_scheme}://{ip}:{port}"
    raise ValueError(
        "Прокси должен быть в формате host:port, host:port:user:pass, user:pass@host:port или полный URL"
    )

def to_playwright_proxy(raw: Optional[str]) -> Optional[dict]:
    normalized = normalize_proxy_string(raw)
    if not normalized:
        return None

    parsed = urlparse(normalized)
    if not parsed.hostname or not parsed.port:
        raise ValueError(f"Не удалось разобрать прокси: {raw}")

    out: dict = {"server": f"{parsed.scheme}://{parsed.hostname}:{parsed.port}"}
    if parsed.username:
        out["username"] = parsed.username
    if parsed.password:
        out["password"] = parsed.password
    return out

def _parse_components(raw: str):
    raw = raw.strip()
    if "://" in raw:
        parsed = urlparse(raw)
        return parsed.scheme, parsed.hostname, parsed.port, parsed.username, parsed.password
    if "@" in raw:
        creds, _, host_port = raw.rpartition("@")
        host, port = host_port.rsplit(":", 1)
        user, _, password = creds.partition(":")
        return None, host, int(port), user, password
    parts = raw.split(":")
    if len(parts) == 4:
        return None, parts[0], int(parts[1]), parts[2], parts[3]
    if len(parts) == 2:
        return None, parts[0], int(parts[1]), None, None
    raise ValueError("bad proxy format")

def _http_alive(host: str, port: int, user, password, timeout: float) -> bool:
    if user and password:
        proxy_url = f"http://{user}:{password}@{host}:{port}"
    else:
        proxy_url = f"http://{host}:{port}"
    for target in (
        "https://www.gstatic.com/generate_204",
        "https://www.google.com/generate_204",
        "http://ip-api.com/json/?fields=status",
    ):
        try:
            handler = urllib.request.ProxyHandler({"http": proxy_url, "https": proxy_url})
            opener = urllib.request.build_opener(handler)
            req = urllib.request.Request(
                target, headers={"User-Agent": "mini-antidetect/1.0"}
            )
            with opener.open(req, timeout=timeout) as resp:
                if getattr(resp, "status", 200) < 500:
                    return True
        except Exception:
            continue
    return False

def _socks5_alive(host: str, port: int, user, password, timeout: float) -> bool:
    try:
        s = socket.create_connection((host, int(port)), timeout=timeout)
    except Exception:
        return False
    try:
        s.settimeout(timeout)
        if user and password:
            s.sendall(b"\x05\x02\x00\x02")
        else:
            s.sendall(b"\x05\x01\x00")
        resp = s.recv(2)
        if len(resp) < 2 or resp[0] != 0x05:
            return False
        method = resp[1]
        if method == 0xff:
            return False
        if method == 0x02:
            if not user or not password:
                return False
            ub = user.encode("utf-8")
            pb = password.encode("utf-8")
            if len(ub) > 255 or len(pb) > 255:
                return False
            s.sendall(b"\x01" + bytes([len(ub)]) + ub + bytes([len(pb)]) + pb)
            auth_resp = s.recv(2)
            if len(auth_resp) < 2 or auth_resp[1] != 0x00:
                return False
        elif method != 0x00:
            return False
        return True
    except Exception:
        return False
    finally:
        try:
            s.close()
        except Exception:
            pass

def check_alive(raw: Optional[str], timeout: float = 4.0) -> tuple[bool, Optional[str]]:
    if not raw:
        return True, None
    try:
        scheme, host, port, user, password = _parse_components(raw)
    except Exception:
        return False, None
    if not host or not port:
        return False, None

    if scheme in ("socks5", "socks5h"):
        ok = _socks5_alive(host, port, user, password, timeout)
        return ok, ("socks5" if ok else None)

    if scheme in ("http", "https"):
        ok = _http_alive(host, port, user, password, timeout)
        return ok, ("http" if ok else None)

    if _http_alive(host, port, user, password, timeout):
        return True, "http"
    if _socks5_alive(host, port, user, password, timeout):
        return True, "socks5"
    return False, None
