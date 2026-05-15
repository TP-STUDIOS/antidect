<img src="banner.jpg" alt="antidect" width="800" />

![Python](https://img.shields.io/badge/python-3.10%2B-3776AB?logo=python&logoColor=white)
![Playwright](https://img.shields.io/badge/playwright-1.40%2B-2EAD33?logo=playwright&logoColor=white)
![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey)
![Status](https://img.shields.io/badge/status-active-success)

**Mini-antidetect CLI · Browser profile manager with isolated sessions, proxies, fingerprints**

CLI для управления изолированными профилями Chromium / Firefox через Playwright.
Подходит для мульти-аккаунтинга — у каждого профиля свои куки, расширения, прокси и отпечаток.

[Русский](#русский) · [English](#english)

</div>

---

## Русский

### Возможности

| | |
|---|---|
| **Профили** | Создание, клонирование, редактирование, импорт / экспорт в zip |
| **Прокси** | HTTP / HTTPS с auth, SOCKS5 (whitelist), валидация alive, авто-определение схемы |
| **Анти-детект** | 21 fingerprint-пресет (Chrome 118-126, Win/Mac/Linux), canvas/WebGL noise, WebRTC guard, webdriver hide, audio noise |
| **Гео-привязка** | Автоматический timezone / locale / координаты по IP прокси (через ip-api.com) |
| **Bulk-режим** | Параллельный запуск нескольких профилей одной командой |
| **UI** | Интерактивное TUI на стрелках, поддержка ESC / Ctrl+C, кириллическая раскладка для Y/N |
| **Языки** | Русский, English (переключение в Settings) |
| **Безопасность** | Lock-файлы с PID-check, атомарная запись JSON, защита от zip-slip при импорте |

### Установка

```bash
git clone https://github.com/TP-STUDIOS/antidect.git
cd antidect
pip install -r requirements.txt
```

Браузер (Firefox или Chromium) скачивается автоматически при первом запуске профиля (~100 MB одноразово).

### Запуск

```bash
python main.py
```

Откроется интерактивное меню — все действия (создание, запуск, редактирование, удаление, импорт/экспорт, настройки) делаются через стрелки и Enter.

### Прокси

Поддерживаемые форматы ввода:

- `host:port`
- `host:port:user:pass`
- `user:pass@host:port`
- `http://user:pass@host:port`
- `socks5://host:port`

**Про SOCKS5 + auth:** Playwright не поддерживает SOCKS5 с авторизацией (ограничение библиотеки). Варианты:

- Использовать HTTP-вариант прокси у провайдера (тот же сервер, обычно другой порт)
- Или включить IP-whitelist у провайдера и использовать SOCKS5 без user:pass

HTTP-прокси с auth работают через встроенный auth-relay в обход Playwright auth-flow.

### Требования

- Python 3.10 или новее
- Windows 10 / 11, macOS, Linux
- ~200 MB на браузер при первом запуске

---

## English

### Features

| | |
|---|---|
| **Profiles** | Create, clone, edit, import / export to zip |
| **Proxies** | HTTP / HTTPS with auth, SOCKS5 (whitelist), liveness check, scheme auto-detect |
| **Anti-detect** | 21 fingerprint presets (Chrome 118-126, Win/Mac/Linux), canvas/WebGL noise, WebRTC guard, webdriver hide, audio noise |
| **Geo binding** | Auto timezone / locale / coords from proxy IP (via ip-api.com) |
| **Bulk mode** | Parallel launch of multiple profiles in one command |
| **UI** | Interactive arrow-key TUI, ESC / Ctrl+C support, Cyrillic-layout Y/N |
| **Languages** | English, Russian (switch in Settings) |
| **Safety** | Lock files with PID check, atomic JSON writes, zip-slip protection on import |

### Install

```bash
git clone https://github.com/TP-STUDIOS/antidect.git
cd antidect
pip install -r requirements.txt
```

Browser (Firefox or Chromium) downloads automatically on first profile launch (~100 MB, one-time).

### Run

```bash
python main.py
```

Opens the interactive menu — all actions (create, run, edit, delete, import/export, settings) are done with arrow keys and Enter.

### Proxies

Supported input formats:

- `host:port`
- `host:port:user:pass`
- `user:pass@host:port`
- `http://user:pass@host:port`
- `socks5://host:port`

**On SOCKS5 + auth:** Playwright doesn't support SOCKS5 with authentication (library limitation). Options:

- Use the HTTP variant of the proxy from your provider (same server, usually different port)
- Or enable IP whitelist at the provider and use SOCKS5 without user:pass

HTTP proxies with auth work through a built-in auth-injection relay, bypassing Playwright's auth flow.

### Requirements

- Python 3.10+
- Windows 10 / 11, macOS, Linux
- ~200 MB for browser on first launch

---

<div align="center">

**TPStudio** · Telegram [@TPStudioDev](https://t.me/TPStudioDev)

</div>
