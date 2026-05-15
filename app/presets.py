
import random

def _w(os_label: str, chrome_full: str, brands_pattern: str, screen: tuple[int, int], platform_version: str) -> dict:
    major = chrome_full.split(".")[0]
    if brands_pattern == "A":
        brands = [
            {"brand": "Not A(Brand", "version": "99"},
            {"brand": "Google Chrome", "version": major},
            {"brand": "Chromium", "version": major},
        ]
    elif brands_pattern == "B":
        brands = [
            {"brand": "Not_A Brand", "version": "8"},
            {"brand": "Chromium", "version": major},
            {"brand": "Google Chrome", "version": major},
        ]
    else:
        brands = [
            {"brand": "Not.A/Brand", "version": "24"},
            {"brand": "Chromium", "version": major},
            {"brand": "Google Chrome", "version": major},
        ]
    return {
        "os": os_label,
        "user_agent": (
            f"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            f"(KHTML, like Gecko) Chrome/{chrome_full} Safari/537.36"
        ),
        "platform": "Win32",
        "ua_platform": "Windows",
        "ua_full_version": chrome_full,
        "ua_brands": brands,
        "ua_mobile": False,
        "architecture": "x86",
        "bitness": "64",
        "platform_version": platform_version,
        "screen_width": screen[0],
        "screen_height": screen[1],
    }

def _m(os_label: str, chrome_full: str, brands_pattern: str, screen: tuple[int, int], platform_version: str) -> dict:
    major = chrome_full.split(".")[0]
    if brands_pattern == "A":
        brands = [
            {"brand": "Not A(Brand", "version": "99"},
            {"brand": "Google Chrome", "version": major},
            {"brand": "Chromium", "version": major},
        ]
    elif brands_pattern == "B":
        brands = [
            {"brand": "Not_A Brand", "version": "8"},
            {"brand": "Chromium", "version": major},
            {"brand": "Google Chrome", "version": major},
        ]
    else:
        brands = [
            {"brand": "Not.A/Brand", "version": "24"},
            {"brand": "Chromium", "version": major},
            {"brand": "Google Chrome", "version": major},
        ]
    return {
        "os": os_label,
        "user_agent": (
            f"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
            f"(KHTML, like Gecko) Chrome/{chrome_full} Safari/537.36"
        ),
        "platform": "MacIntel",
        "ua_platform": "macOS",
        "ua_full_version": chrome_full,
        "ua_brands": brands,
        "ua_mobile": False,
        "architecture": "x86",
        "bitness": "64",
        "platform_version": platform_version,
        "screen_width": screen[0],
        "screen_height": screen[1],
    }

def _l(chrome_full: str, screen: tuple[int, int]) -> dict:
    major = chrome_full.split(".")[0]
    return {
        "os": "Linux (Ubuntu)",
        "user_agent": (
            f"Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
            f"(KHTML, like Gecko) Chrome/{chrome_full} Safari/537.36"
        ),
        "platform": "Linux x86_64",
        "ua_platform": "Linux",
        "ua_full_version": chrome_full,
        "ua_brands": [
            {"brand": "Not A(Brand", "version": "99"},
            {"brand": "Google Chrome", "version": major},
            {"brand": "Chromium", "version": major},
        ],
        "ua_mobile": False,
        "architecture": "x86",
        "bitness": "64",
        "platform_version": "",
        "screen_width": screen[0],
        "screen_height": screen[1],
    }

PRESETS: list[dict] = [
    _w("Windows 11", "126.0.6478.127", "A", (1920, 1080), "15.0.0"),
    _w("Windows 11", "125.0.6422.142", "A", (2560, 1440), "15.0.0"),
    _w("Windows 11", "124.0.6367.207", "B", (1920, 1080), "15.0.0"),
    _w("Windows 11", "123.0.6312.123", "A", (1536, 864), "15.0.0"),
    _w("Windows 11", "122.0.6261.112", "B", (1920, 1200), "15.0.0"),
    _w("Windows 10", "121.0.6167.140", "A", (1920, 1080), "10.0.0"),
    _w("Windows 10", "120.0.6099.225", "B", (1536, 864), "10.0.0"),
    _w("Windows 10", "119.0.6045.200", "B", (1366, 768), "10.0.0"),
    _w("Windows 10", "118.0.5993.118", "A", (1920, 1080), "10.0.0"),
    _w("Windows 11", "121.0.6167.140", "B", (3840, 2160), "15.0.0"),

    _m("macOS Sonoma", "126.0.6478.127", "A", (1440, 900), "14.5.0"),
    _m("macOS Sonoma", "125.0.6422.142", "B", (2560, 1600), "14.4.1"),
    _m("macOS Sonoma", "124.0.6367.207", "A", (1680, 1050), "14.3.1"),
    _m("macOS Sonoma", "123.0.6312.123", "B", (1440, 900), "14.2.1"),
    _m("macOS Ventura", "121.0.6167.140", "A", (2560, 1600), "13.6.0"),
    _m("macOS Ventura", "120.0.6099.225", "B", (1440, 900), "13.5.0"),
    _m("macOS Ventura", "119.0.6045.200", "B", (1680, 1050), "13.4.0"),
    _m("macOS Monterey", "118.0.5993.118", "A", (1440, 900), "12.7.0"),

    _l("125.0.6422.142", (1920, 1080)),
    _l("122.0.6261.112", (1920, 1200)),
    _l("121.0.6167.140", (2560, 1440)),
]

def pick_random() -> dict:
    return dict(random.choice(PRESETS))
