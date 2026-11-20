"""pywebview asosidagi oddiy brauzer avtomatlashtirish.

pywebview'ning GUI sikli asosiy oqimda ishlashi shart (`webview.start()` bloklaydi),
shuning uchun foydalanuvchi skripti alohida oqimda bajariladi. Qarang: `run()`.
"""

from __future__ import annotations

import json
import re
import sys
import threading
import time
from contextlib import contextmanager, nullcontext, suppress
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterator
from urllib.parse import urlsplit

import webview

SESSION_DIR = Path.cwd() / ".session"
ALLOWED_SCHEMES = {"http", "https"}
BLANK_PAGE = "<!doctype html><title></title>"
START_TIMEOUT = 20.0


class BrowserError(Exception):
    """Barcha brauzer xatolarining umumiy asosi."""


class NavigationError(BrowserError):
    """Sahifa ochilmadi (tarmoq xatosi, noto'g'ri manzil va h.k.)."""


class ElementNotFound(BrowserError, LookupError):
    """CSS selektor bo'yicha element topilmadi."""


class BrowserTimeout(BrowserError, TimeoutError):
    """Kutilgan voqea belgilangan vaqtda sodir bo'lmadi."""


@dataclass(frozen=True)
class Page:
    url: str
    title: str


class Browser:
    """pywebview oynasini boshqaradigan qulay interfeys."""

    def __init__(self, window: webview.Window, loaded: threading.Event) -> None:
        self._window = window
        self._loaded = loaded

    # ------------------------------------------------------------------ ichki

    def js(self, script: str) -> Any:
        """Sahifada JavaScript bajaradi va natijani qaytaradi."""
        return self._window.evaluate_js(script)

    def _call(self, fn: str, *args: Any) -> Any:
        """JS funksiyasini argumentlar bilan chaqiradi (argumentlar JSON bo'lib xavfsiz uzatiladi)."""
        return self.js(f"({fn})(...{json.dumps(args)})")

    def _on(self, selector: str, fn: str, *args: Any) -> Any:
        """`fn(element, *args)` ni elementda ishlatadi; element yo'q bo'lsa ElementNotFound."""
        result = self._call(
            "(sel, ...args) => {"
            "  const el = document.querySelector(sel);"
            f"  return el ? [({fn})(el, ...args)] : null;"
            "}",
            selector,
            *args,
        )
        if result is None:
            raise ElementNotFound(f"Topilmadi: {selector}")
        return result[0]

    @contextmanager
    def _navigation(self, timeout: float) -> Iterator[None]:
        """Ichidagi amal sahifa yuklanishiga olib kelsa, yuklanishni kutadi."""
        self._loaded.clear()
        yield
        if not self._loaded.wait(timeout):
            raise BrowserTimeout(f"Sahifa {timeout:g}s ichida yuklanmadi")

    # ---------------------------------------------------------------- sahifa

    @property
    def url(self) -> str:
        return self.js("location.href") or ""

    @property
    def title(self) -> str:
        return self.js("document.title") or ""

    @property
    def text(self) -> str:
        return self.js("document.body ? document.body.innerText : ''") or ""

    @property
    def html(self) -> str:
        return self.js("document.documentElement.outerHTML") or ""

    def links(self) -> list[dict[str, str]]:
        return self.js(
            "Array.from(document.links, a => ({text: a.innerText.trim(), href: a.href}))"
        ) or []

    # ------------------------------------------------------------ navigatsiya

    def open(self, url: str, *, wait_for: str | None = None, timeout: float = 30.0) -> Page:
        """Manzilni ochadi. `wait_for` — sahifada paydo bo'lishi kutiladigan CSS selektor."""
        if "://" not in url:
            url = "https://" + url
        if urlsplit(url).scheme not in ALLOWED_SCHEMES:
            raise ValueError("Faqat http:// va https:// ruxsat etiladi")

        if self.url != url:
            with self._navigation(timeout):
                self._window.load_url(url)
        # Yuklanish xatosida brauzer xato sahifasini ochadi (http/https emas).
        current = self.url
        if urlsplit(current).scheme not in ALLOWED_SCHEMES:
            raise NavigationError(f"Sahifa ochilmadi: {url} (hozir: {current})")

        if wait_for:
            self.wait_for(wait_for, timeout)
        return Page(current, self.title)
    

    def back(self, timeout: float = 10.0) -> None:
        with self._navigation(timeout):
            self.js("history.back()")

    def forward(self, timeout: float = 10.0) -> None:
        with self._navigation(timeout):
            self.js("history.forward()")

    def reload(self, timeout: float = 30.0) -> None:
        with self._navigation(timeout):
            self._window.load_url(self.url)

    # --------------------------------------------------------------- elementlar

    def exists(self, selector: str) -> bool:
        return bool(self._call("(sel) => !!document.querySelector(sel)", selector))

    def wait_for(self, selector: str, timeout: float = 10.0, interval: float = 0.2) -> None:
        deadline = time.monotonic() + timeout
        while True:
            # Sahifa almashayotganda JS vaqtincha ishlamasligi mumkin — keyingi urinishda qayta tekshiramiz.
            with suppress(Exception):
                if self.exists(selector):
                    return
            if time.monotonic() >= deadline:
                raise BrowserTimeout(f"Element chiqmadi: {selector}")
            time.sleep(interval)

    def get_text(self, selector: str) -> str:
        return re.sub(r'\s+', ' ', self._on(selector, "el => el.innerText")).strip()

    def get_html(self, selector: str) -> str:
        return re.sub(r'\s+', ' ', self._on(selector, "el => el.innerHTML")).strip()
    

    def get_attr(self, selector: str, name: str) -> str | None:
        return self._on(selector, "(el, name) => el.getAttribute(name)", name)

    # ------------------------------------------------------------------ amallar

    def click(self, selector: str, *, navigates: bool = False, timeout: float = 30.0) -> None:
        """Elementni bosadi. Bosish yangi sahifaga olib borsa `navigates=True` bering."""
        with self._navigation(timeout) if navigates else nullcontext():
            self._on(selector, "el => { el.scrollIntoView({block: 'center'}); el.click(); }")

    def type(self, selector: str, text: str, *, clear: bool = True) -> None:
        # Qiymat native setter orqali beriladi — React/Vue kabi freymvorklar o'zgarishni ko'radi.
        self._on(
            selector,
            """(el, text, clear) => {
                el.focus();
                const proto = el instanceof HTMLTextAreaElement
                    ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype;
                const setValue = Object.getOwnPropertyDescriptor(proto, 'value').set;
                setValue.call(el, (clear ? '' : el.value) + text);
                el.dispatchEvent(new Event('input', {bubbles: true}));
                el.dispatchEvent(new Event('change', {bubbles: true}));
            }""",
            text,
            clear,
        )

    def submit(self, selector: str, *, navigates: bool = False, timeout: float = 30.0) -> None:
        """Forma (yoki forma ichidagi element) ni yuboradi."""
        with self._navigation(timeout) if navigates else nullcontext():
            in_form = self._on(
                selector,
                """el => {
                    const form = el.tagName === 'FORM' ? el : el.form || el.closest('form');
                    if (!form) return false;
                    form.requestSubmit ? form.requestSubmit() : form.submit();
                    return true;
                }""",
            )
        if not in_form:
            raise ValueError(f"Element formaga tegishli emas: {selector}")

    def scroll_bottom(self) -> None:
        self.js("window.scrollTo(0, document.body.scrollHeight)")


def run(task: Callable[[Browser], Any],*,show: bool = False,session: bool = False,debug: bool = False) -> Any:
    """Oynani ochadi va `task(browser)` ni alohida oqimda bajaradi.

    show          — oynani ko'rsatish (standart: yashirin).
    session       — cookie va seansni SESSION_DIR (`./.browser`) da saqlash (standart: saqlanmaydi).

    `task` natijasini qaytaradi; `task` xato bergan bo'lsa, xatoni shu yerda qayta ko'taradi.
    """
    window = webview.create_window("Browser", html=BLANK_PAGE, width=1100, height=750, hidden=not show)
    loaded = threading.Event()
    window.events.loaded += loaded.set

    outcome: dict[str, Any] = {}

    def worker() -> None:
        try:
            if not loaded.wait(START_TIMEOUT):
                raise BrowserTimeout("Boshlang'ich sahifa yuklanmadi")
            outcome["result"] = task(Browser(window, loaded))
        except Exception as exc:  # asosiy oqimda qayta ko'tariladi
            outcome["error"] = exc
        finally:
            with suppress(Exception):  # foydalanuvchi oynani o'zi yopgan bo'lishi mumkin
                window.destroy()

    options: dict[str, Any] = {"debug": debug, "private_mode": not session}
    if session:
        SESSION_DIR.mkdir(parents=True, exist_ok=True)
        options["storage_path"] = str(SESSION_DIR)
    if sys.platform == "win32":
        options["gui"] = "edgechromium"

    # daemon=True: oyna qo'lda yopilsa, osilib qolgan skript dasturni to'xtatib turmaydi.
    threading.Thread(target=worker, daemon=True).start()
    webview.start(**options)

    if "error" in outcome:
        raise outcome["error"]
    return outcome.get("result")