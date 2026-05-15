import hashlib
import json as _json

WEBDRIVER_HIDE_JS = """
(() => {
  try {
    Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
  } catch (e) {}
  try {
    if (navigator.__proto__ && 'webdriver' in navigator.__proto__) {
      delete navigator.__proto__.webdriver;
    }
  } catch (e) {}
  try {
    Object.defineProperty(navigator, 'plugins', {
      get: () => [
        { name: 'PDF Viewer' },
        { name: 'Chrome PDF Viewer' },
        { name: 'Chromium PDF Viewer' },
        { name: 'Microsoft Edge PDF Viewer' },
        { name: 'WebKit built-in PDF' }
      ]
    });
  } catch (e) {}
})();
"""

CANVAS_NOISE_JS = """
(() => {
  let s = __SEED__;
  const rand = () => {
    s = (s * 1103515245 + 12345) & 0x7fffffff;
    return s / 0x7fffffff;
  };
  const noise = (imageData) => {
    const d = imageData.data;
    for (let i = 0; i < d.length; i += 4) {
      if (rand() < 0.005) {
        d[i]   = d[i]   ^ 1;
        d[i+1] = d[i+1] ^ 1;
        d[i+2] = d[i+2] ^ 1;
      }
    }
    return imageData;
  };
  const origToDataURL = HTMLCanvasElement.prototype.toDataURL;
  const origGetImageData = CanvasRenderingContext2D.prototype.getImageData;
  HTMLCanvasElement.prototype.toDataURL = function () {
    try {
      const ctx = this.getContext('2d');
      if (ctx) {
        const w = this.width, h = this.height;
        if (w && h && w * h <= 2000000) {
          const data = origGetImageData.call(ctx, 0, 0, w, h);
          noise(data);
          ctx.putImageData(data, 0, 0);
        }
      }
    } catch (e) {}
    return origToDataURL.apply(this, arguments);
  };
  CanvasRenderingContext2D.prototype.getImageData = function () {
    const data = origGetImageData.apply(this, arguments);
    return noise(data);
  };
})();
"""

WEBGL_NOISE_JS = """
(() => {
  const seed = __SEED__;
  const vendors = ['Intel Inc.', 'NVIDIA Corporation', 'ATI Technologies Inc.', 'Google Inc.'];
  const renderers = [
    'Intel Iris OpenGL Engine',
    'ANGLE (NVIDIA, NVIDIA GeForce GTX 1060 Direct3D11 vs_5_0 ps_5_0)',
    'ANGLE (Intel, Intel(R) UHD Graphics 620 Direct3D11 vs_5_0 ps_5_0)',
    'ANGLE (AMD, AMD Radeon RX 580 Direct3D11 vs_5_0 ps_5_0)'
  ];
  const vendor = vendors[seed % vendors.length];
  const renderer = renderers[seed % renderers.length];
  const patch = (proto) => {
    const orig = proto.getParameter;
    proto.getParameter = function (param) {
      if (param === 37445) return vendor;
      if (param === 37446) return renderer;
      return orig.apply(this, arguments);
    };
  };
  if (window.WebGLRenderingContext) patch(WebGLRenderingContext.prototype);
  if (window.WebGL2RenderingContext) patch(WebGL2RenderingContext.prototype);
})();
"""

HARDWARE_SPOOF_JS = """
(() => {
  const seed = __SEED__;
  const cores = [4, 6, 8, 12, 16][seed % 5];
  const memory = [4, 8, 16][seed % 3];
  try { Object.defineProperty(navigator, 'hardwareConcurrency', { get: () => cores }); } catch (e) {}
  try { Object.defineProperty(navigator, 'deviceMemory', { get: () => memory }); } catch (e) {}
})();
"""

WEBRTC_GUARD_JS = """
(() => {
  if (!window.RTCPeerConnection) return;
  const orig = window.RTCPeerConnection;
  const Wrapped = function (...args) {
    const pc = new orig(...args);
    const origAdd = pc.addIceCandidate.bind(pc);
    pc.addIceCandidate = (cand, ...rest) => {
      if (cand && typeof cand.candidate === 'string') {
        if (cand.candidate.includes(' host ') || cand.candidate.includes(' srflx ')) {
          return Promise.resolve();
        }
      }
      return origAdd(cand, ...rest);
    };
    return pc;
  };
  Wrapped.prototype = orig.prototype;
  window.RTCPeerConnection = Wrapped;
  if (window.webkitRTCPeerConnection) window.webkitRTCPeerConnection = Wrapped;
})();
"""

LANGUAGES_JS = """
(() => {
  try {
    const langs = __LANGS__;
    Object.defineProperty(navigator, 'languages', { get: () => langs });
    Object.defineProperty(navigator, 'language', { get: () => langs[0] });
  } catch (e) {}
})();
"""

STEALTH_EXTRA_JS = """
(() => {
  try {
    if (!window.chrome) {
      window.chrome = {
        runtime: {},
        loadTimes: function () { return {}; },
        csi: function () { return {}; },
        app: { isInstalled: false },
      };
    }
  } catch (e) {}

  try {
    const origQuery = navigator.permissions && navigator.permissions.query;
    if (origQuery) {
      navigator.permissions.query = function (params) {
        if (params && params.name === 'notifications') {
          return Promise.resolve({ state: Notification.permission, onchange: null });
        }
        return origQuery.call(this, params);
      };
    }
  } catch (e) {}

  try {
    if (!navigator.getBattery) {
      navigator.getBattery = function () {
        return Promise.resolve({
          charging: true,
          chargingTime: 0,
          dischargingTime: Infinity,
          level: 1,
          onchargingchange: null,
          onchargingtimechange: null,
          ondischargingtimechange: null,
          onlevelchange: null,
          addEventListener: function () {},
          removeEventListener: function () {},
          dispatchEvent: function () { return true; },
        });
      };
    }
  } catch (e) {}

  try {
    const AC = window.AudioContext || window.webkitAudioContext;
    if (AC) {
      const origGetChannelData = AudioBuffer.prototype.getChannelData;
      AudioBuffer.prototype.getChannelData = function () {
        const data = origGetChannelData.apply(this, arguments);
        for (let i = 0; i < data.length; i += 100) {
          data[i] = data[i] + (Math.random() - 0.5) * 1e-7;
        }
        return data;
      };
    }
  } catch (e) {}

  try {
    if (window.console && typeof window.console.debug === 'function') {
      const origDebug = window.console.debug;
      window.console.debug = function () {
        try { return origDebug.apply(this, arguments); } catch (e) { return undefined; }
      };
    }
  } catch (e) {}
})();
"""

PLATFORM_SPOOF_JS = """
(() => {
  const preset = __PRESET__;
  try {
    Object.defineProperty(navigator, 'platform', { get: () => preset.platform });
  } catch (e) {}
  try {
    Object.defineProperty(navigator, 'oscpu', { get: () => preset.platform });
  } catch (e) {}
  try {
    Object.defineProperty(navigator, 'appVersion', {
      get: () => '5.0 (' + preset.platform + ')'
    });
  } catch (e) {}

  try {
    const newUAData = {
      brands: preset.ua_brands,
      mobile: preset.ua_mobile,
      platform: preset.ua_platform,
      toJSON: function () {
        return {
          brands: preset.ua_brands,
          mobile: preset.ua_mobile,
          platform: preset.ua_platform,
        };
      },
      getHighEntropyValues: function (hints) {
        return Promise.resolve({
          brands: preset.ua_brands,
          mobile: preset.ua_mobile,
          platform: preset.ua_platform,
          architecture: preset.architecture || 'x86',
          bitness: preset.bitness || '64',
          model: '',
          platformVersion: preset.platform_version || '',
          uaFullVersion: preset.ua_full_version || '',
          fullVersionList: preset.ua_brands,
          wow64: false,
        });
      },
    };
    Object.defineProperty(navigator, 'userAgentData', { get: () => newUAData });
  } catch (e) {}

  try {
    const w = preset.screen_width;
    const h = preset.screen_height;
    Object.defineProperty(screen, 'width', { get: () => w });
    Object.defineProperty(screen, 'height', { get: () => h });
    Object.defineProperty(screen, 'availWidth', { get: () => w });
    Object.defineProperty(screen, 'availHeight', { get: () => h - 40 });
    Object.defineProperty(screen, 'colorDepth', { get: () => 24 });
    Object.defineProperty(screen, 'pixelDepth', { get: () => 24 });
  } catch (e) {}
})();
"""

def _seed(profile_id: str) -> int:
    return int(hashlib.md5(profile_id.encode()).hexdigest()[:8], 16)

def build_init_script(
    profile_id: str,
    settings: dict,
    languages: list[str] | None = None,
    preset: dict | None = None,
    browser_type: str = "chromium",
) -> str:
    seed = _seed(profile_id)
    parts: list[str] = []
    is_chromium = browser_type == "chromium"
    if preset and is_chromium:
        parts.append(PLATFORM_SPOOF_JS.replace("__PRESET__", _json.dumps(preset)))
    if settings.get("hide_webdriver"):
        parts.append(WEBDRIVER_HIDE_JS)
        if is_chromium:
            parts.append(STEALTH_EXTRA_JS)
    if settings.get("fingerprint_noise"):
        parts.append(CANVAS_NOISE_JS.replace("__SEED__", str(seed)))
        parts.append(WEBGL_NOISE_JS.replace("__SEED__", str(seed)))
    if settings.get("spoof_hardware"):
        parts.append(HARDWARE_SPOOF_JS.replace("__SEED__", str(seed)))
    if settings.get("webrtc_protection"):
        parts.append(WEBRTC_GUARD_JS)
    if languages:
        parts.append(LANGUAGES_JS.replace("__LANGS__", _json.dumps(languages)))
    return "\n".join(parts)

def build_chromium_args(settings: dict) -> list[str]:
    args: list[str] = []
    if settings.get("webrtc_protection"):
        args.append("--force-webrtc-ip-handling-policy=disable_non_proxied_udp")
        args.append("--webrtc-ip-handling-policy=disable_non_proxied_udp")
    if settings.get("hide_webdriver"):
        args.append("--disable-blink-features=AutomationControlled")
    if settings.get("block_notifications"):
        args.append("--disable-notifications")
    return args
