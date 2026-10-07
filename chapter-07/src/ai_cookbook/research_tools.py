import hashlib
import threading
from datetime import datetime, timezone
from html.parser import HTMLParser
from time import monotonic
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, ProxyHandler, build_opener

class PageText(HTMLParser):
    def __init__(self):
        super().__init__()
        self.hidden, self.parts = 0, []

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style"}:
            self.hidden += 1

    def handle_endtag(self, tag):
        if tag in {"script", "style"} and self.hidden:
            self.hidden -= 1

    def handle_data(self, data):
        if not self.hidden and data.strip():
            self.parts.append(data.strip())


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        raise ValueError("Redirect requires a reviewed source entry.")


class Sources:
    def __init__(self, catalog, mode="fixture"):
        if mode not in {"fixture", "live"}:
            raise ValueError("Unknown source mode.")
        for entry in catalog.values():
            url = urlsplit(entry["url"])
            permitted = (url.scheme == "http" and url.netloc == "127.0.0.1:8765"
                         if mode == "fixture" else url.scheme == "https")
            if not permitted or url.username or url.password or url.fragment:
                raise ValueError("Source is outside the configured mode.")
        self.catalog, self.archive = catalog, {}
        self.calls, self.deadline = 0, monotonic() + 90
        self.lock = threading.Lock()

    def take(self):
        with self.lock:
            if self.calls >= 6 or monotonic() >= self.deadline:
                raise RuntimeError("Research tool budget exhausted.")
            self.calls += 1

    def read(self, source_id, rendered=False):
        self.take()
        entry = self.catalog[source_id]
        url = entry["url"]
        if rendered:
            from playwright.sync_api import sync_playwright
            with sync_playwright() as runtime:
                browser = runtime.chromium.launch(headless=True, chromium_sandbox=True)
                try:
                    context = browser.new_context(service_workers="block", accept_downloads=False)
                    context.route("**/*", lambda route: route.continue_()
                                  if route.request.url == url and route.request.method == "GET"
                                  else route.abort())
                    page = context.new_page()
                    response = page.goto(url, wait_until="domcontentloaded", timeout=10000)
                    if response is None or response.status != 200 or page.url != url:
                        raise ValueError("Unexpected page response.")
                    page.wait_for_selector(entry["ready_selector"], timeout=5000)
                    text = page.locator("body").inner_text(timeout=5000)
                finally:
                    browser.close()
        else:
            opener = build_opener(ProxyHandler({}), NoRedirect())
            with opener.open(url, timeout=10) as response:
                if response.status != 200 or response.headers.get_content_type() != "text/html":
                    raise ValueError("Expected an HTML page.")
                raw = response.read(100_001)
                if len(raw) > 100_000:
                    raise ValueError("Page exceeds the intake limit.")
            parser = PageText()
            parser.feed(raw.decode("utf-8"))
            parser.close()
            text = " ".join(parser.parts)
        if not text.strip() or len(text.encode()) > 2000:
            raise ValueError("Page text is empty or too large.")
        digest = hashlib.sha256(text.encode()).hexdigest()
        identity = hashlib.sha256((url + "|" + digest).encode()).hexdigest()[:20]
        record = {"id": identity, "source_id": source_id, "url": url,
                  "title": entry["title"], "text": text, "sha256": digest,
                  "observed_at": datetime.now(timezone.utc).isoformat(),
                  "method": "render" if rendered else "fetch"}
        with self.lock:
            self.archive[identity] = record
        return record

    def tools(self):
        def search(query: str) -> list[dict]:
            """Find relevant entries in the approved source catalog."""
            self.take()
            words = set(query.lower().split())
            ranked = sorted(self.catalog.items(), key=lambda item:
                            -len(words & set(item[1]["title"].lower().split())))
            return [{"source_id": key, "title": value["title"]} for key, value in ranked[:5]]

        def fetch(source_id: str) -> dict:
            """Read an approved page without running its scripts."""
            return self.read(source_id)

        def render(source_id: str) -> dict:
            """Read a script-rendered approved page in a fresh browser."""
            return self.read(source_id, rendered=True)

        return [search, fetch, render]
