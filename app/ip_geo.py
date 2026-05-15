import json
import urllib.request
from typing import Optional

COUNTRY_LOCALE = {
    "RU": "ru-RU", "US": "en-US", "GB": "en-GB", "DE": "de-DE",
    "FR": "fr-FR", "ES": "es-ES", "IT": "it-IT", "PL": "pl-PL",
    "UA": "uk-UA", "TR": "tr-TR", "BR": "pt-BR", "JP": "ja-JP",
    "CN": "zh-CN", "KR": "ko-KR", "IN": "en-IN", "NL": "nl-NL",
    "SE": "sv-SE", "FI": "fi-FI", "NO": "nb-NO", "DK": "da-DK",
    "CZ": "cs-CZ", "PT": "pt-PT", "GR": "el-GR", "RO": "ro-RO",
    "HU": "hu-HU", "BG": "bg-BG", "KZ": "ru-KZ", "BY": "ru-BY",
    "CA": "en-CA", "AU": "en-AU", "MX": "es-MX", "AR": "es-AR",
    "CH": "de-CH", "AT": "de-AT", "BE": "nl-BE", "IE": "en-IE",
    "IL": "he-IL", "SA": "ar-SA", "AE": "ar-AE", "TH": "th-TH",
    "VN": "vi-VN", "ID": "id-ID", "PH": "fil-PH", "MY": "ms-MY",
    "SG": "en-SG", "HK": "zh-HK", "TW": "zh-TW", "ZA": "en-ZA",
}

def lookup(proxy_url: Optional[str] = None, timeout: int = 5) -> Optional[dict]:
    url = "http://ip-api.com/json/?fields=status,timezone,lat,lon,countryCode,query"

    if proxy_url:
        handler = urllib.request.ProxyHandler({"http": proxy_url, "https": proxy_url})
        opener = urllib.request.build_opener(handler)
    else:
        opener = urllib.request.build_opener()

    req = urllib.request.Request(url, headers={"User-Agent": "mini-antidetect/1.0"})
    try:
        with opener.open(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        return {"error": str(e)}

    if data.get("status") != "success":
        return {"error": data.get("message", "lookup failed")}

    country = data.get("countryCode") or ""
    return {
        "ip": data.get("query"),
        "timezone": data.get("timezone"),
        "latitude": data.get("lat"),
        "longitude": data.get("lon"),
        "country": country,
        "locale": COUNTRY_LOCALE.get(country, "en-US"),
    }
