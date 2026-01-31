import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse, urldefrag
from collections import deque

"""
Парсер.

Есть один момент он прасит только русские номера(

Request:
    url — слылка на сайт с http
    mx — Максимум страниц (default=150)

Returns:
    dict: {
        "url": str — стартовый URL,
        "email": set[str] — найденные email-адреса,
        "phone": set[str] — найденные номера телефонов
    }
"""


class Parser:
    def __init__(self, url: str, mx: int = 150) -> None:
        self.url = url
        self.base_domain = urlparse(self.url).netloc
        self.mx = mx

        self.visit = set()
        self.queue = deque([self.url])

        self.email = set()
        self.phone = set()

        self.session = requests.Session()
        self.session.headers.update(
            {"User-Agent": "Mozilla/5.0 (compatible; Parser/1.0)"}
        )

        self.another_files = (
            ".jpg",
            ".jpeg",
            ".png",
            ".gif",
            ".pdf",
            ".zip",
            ".rar",
            ".exe",
            ".svg",
            ".mp4",
            ".mp3",
            ".avi",
            ".doc",
            ".docx",
            ".xls",
            ".xlsx",
            ".ppt",
            ".pptx",
        )

    def run(self) -> dict:
        while self.queue and len(self.visit) < self.mx:
            url = self.queue.popleft()
            if url in self.visit:
                continue

            self.visit.add(url)

            html = self.fetch(url)
            if not html:
                continue

            soup = BeautifulSoup(html, "html.parser")
            self.extract_contacts(soup)
            self.enqueue_links(soup, url)

        return {
            "url": self.url,
            "email": self.email,
            "phone": self.phone,
        }

    def fetch(self, url: str) -> str | None:
        try:
            resp = self.session.get(url, timeout=10)
            if resp.status_code != 200:
                return None
            if "text/html" not in resp.headers.get("Content-Type", ""):
                return None
            return resp.text
        except Exception:
            return None

    def enqueue_links(self, soup: BeautifulSoup, current_url: str):
        for i in soup(href=True):
            href = i["href"].strip()

            if href.startswith(("javascript:", "mailto:", "tel:")):
                continue

            abs_url = urljoin(current_url, href)
            abs_url, _ = urldefrag(abs_url)

            parsed = urlparse(abs_url)

            if parsed.scheme not in ("http", "https"):
                continue

            if parsed.netloc != self.base_domain:
                continue

            if parsed.path.lower().endswith(self.another_files):
                continue

            if abs_url not in self.visit:
                self.queue.append(abs_url)

    def extract_contacts(self, soup: BeautifulSoup):
        text = soup.get_text(" ", strip=True)

        self.email.update(self.find_email(text))
        self.phone.update(self.find_phone(text))

        for i in soup(href=True):
            href = i["href"]
            if href.startswith("mailto:"):
                email = href.split("mailto:")[1].split("?")[0]
                if email:
                    self.email.add(email.lower())

        for i in soup(href=True):
            href = i["href"]
            if href.startswith("tel:"):
                phone = href.split("tel:")[1]
                normalized = self.normalize_phone(phone)
                if normalized:
                    self.phone.add(normalized)

    @staticmethod
    def find_email(text: str) -> set:
        out = set()
        email_pattern = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
        for email in email_pattern.findall(text):
            out.add(email.lower())
        return out

    @staticmethod
    def find_phone(text: str) -> set:
        out = set()
        phone_pattern = re.compile(r"\+\d{7,}\d")
        for phone in phone_pattern.findall(text):
            out.add(phone)
        return out

    def normalize_phone(self, phone: str) -> str | None:
        digits = re.sub(r"[^\d+]", "", phone)
        if len(digits) < 8:
            return None
        return digits


def main():
    # https://spb.hh.ru/
    url = input()
    out = Parser(url).run()
    print(f"URL: {out.get("url")}")
    print(f"EMAIL: {out.get("email")}")
    print(f"phone: {out.get("phone")}")


if __name__ == "__main__":
    main()
