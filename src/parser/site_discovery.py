"""Sitemap and robots.txt discovery helpers."""
from __future__ import annotations

from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup


class SiteDiscovery:
    """Downloads and parses robots.txt and sitemap.xml without interrupting crawls."""

    def robots_url(self, start_url: str) -> str:
        parsed = urlparse(start_url)
        return f"{parsed.scheme}://{parsed.netloc}/robots.txt"

    def sitemap_url(self, start_url: str) -> str:
        parsed = urlparse(start_url)
        return f"{parsed.scheme}://{parsed.netloc}/sitemap.xml"

    def fetch_robots(self, start_url: str, timeout: int = 10) -> list[tuple[str, str]]:
        rows: list[tuple[str, str]] = []
        try:
            response = requests.get(self.robots_url(start_url), timeout=timeout, headers={"User-Agent": "SEO Inspector Pro/1.0"})
            rows.append(("Status", str(response.status_code)))
            if response.ok:
                for raw_line in response.text.splitlines():
                    line = raw_line.strip()
                    if not line or line.startswith("#") or ":" not in line:
                        continue
                    directive, value = line.split(":", 1)
                    rows.append((directive.strip(), value.strip()))
        except requests.RequestException as exc:
            rows.append(("Error", str(exc)))
        return rows

    def fetch_sitemaps(self, start_url: str, timeout: int = 10) -> list[tuple[str]]:
        sitemap = self.sitemap_url(start_url)
        urls: list[tuple[str]] = [(sitemap,)]
        try:
            response = requests.get(sitemap, timeout=timeout, headers={"User-Agent": "SEO Inspector Pro/1.0"})
            if response.ok:
                soup = BeautifulSoup(response.text, "xml")
                for loc in soup.find_all("loc"):
                    text = loc.get_text(strip=True)
                    if text:
                        urls.append((urljoin(sitemap, text),))
            else:
                urls.append((f"HTTP {response.status_code}",))
        except requests.RequestException as exc:
            urls.append((f"Error: {exc}",))
        return urls
