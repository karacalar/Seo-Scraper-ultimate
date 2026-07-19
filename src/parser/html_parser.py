"""HTML extraction utilities."""
from __future__ import annotations

import re
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

EMAIL_PATTERN = re.compile(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", re.IGNORECASE)
SOCIAL_DOMAINS = {
    "Facebook": "facebook.com", "Instagram": "instagram.com", "X (Twitter)": "twitter.com",
    "LinkedIn": "linkedin.com", "TikTok": "tiktok.com", "YouTube": "youtube.com",
    "Discord": "discord.gg", "Telegram": "t.me",
}


class HTMLParser:
    """Extracts SEO, link, media, resource, email, and social data from HTML."""

    def parse(self, html: str, base_url: str) -> dict[str, object]:
        soup = BeautifulSoup(html, "lxml")
        text = soup.get_text(" ", strip=True)
        title = soup.title.string.strip() if soup.title and soup.title.string else ""
        meta_description = self._meta(soup, "description")
        parsed_base = urlparse(base_url)
        internal_host = parsed_base.netloc.lower()
        links = []
        resources = []
        for tag in soup.find_all("a", href=True):
            absolute = urljoin(base_url, tag["href"]).split("#", 1)[0]
            if absolute.startswith(("http://", "https://")):
                link_host = urlparse(absolute).netloc.lower()
                links.append({"url": absolute, "anchor": tag.get_text(" ", strip=True), "type": "internal" if link_host == internal_host else "external", "status": "unknown"})
        for selector, kind, attr in [("link[rel='stylesheet']", "CSS", "href"), ("script[src]", "JavaScript", "src"), ("video[src]", "Videos", "src"), ("a[href$='.pdf']", "Documents", "href")]:
            for tag in soup.select(selector):
                value = tag.get(attr)
                if value:
                    resources.append({"type": kind, "url": urljoin(base_url, value)})
        for tag in soup.select("link[href*='.woff'], link[href*='.ttf'], link[href*='fonts']"):
            resources.append({"type": "Fonts", "url": urljoin(base_url, tag.get("href", ""))})
        images = []
        for img in soup.find_all("img"):
            src = img.get("src", "")
            if src:
                alt = img.get("alt", "")
                images.append({"url": urljoin(base_url, src), "alt": alt, "missing_alt": not alt.strip(), "width": img.get("width", ""), "height": img.get("height", ""), "size": ""})
        social_links: dict[str, set[str]] = {name: set() for name in SOCIAL_DOMAINS}
        for link in links:
            for name, domain in SOCIAL_DOMAINS.items():
                if domain in link["url"]:
                    social_links[name].add(link["url"])
        return {
            "title": title,
            "meta_description": meta_description,
            "h1": [h.get_text(" ", strip=True) for h in soup.find_all("h1")],
            "h2": [h.get_text(" ", strip=True) for h in soup.find_all("h2")],
            "canonical": self._canonical(soup, base_url),
            "meta_robots": self._meta(soup, "robots"),
            "open_graph": {m.get("property", ""): m.get("content", "") for m in soup.select("meta[property^='og:']")},
            "twitter_cards": {m.get("name", ""): m.get("content", "") for m in soup.select("meta[name^='twitter:']")},
            "structured_data": [s.get_text(strip=True) for s in soup.select("script[type='application/ld+json']")],
            "word_count": len(text.split()),
            "links": links,
            "images": images,
            "resources": resources,
            "emails": set(EMAIL_PATTERN.findall(html)),
            "social_links": social_links,
        }

    @staticmethod
    def _meta(soup: BeautifulSoup, name: str) -> str:
        tag = soup.find("meta", attrs={"name": re.compile(f"^{name}$", re.I)})
        return tag.get("content", "").strip() if tag else ""

    @staticmethod
    def _canonical(soup: BeautifulSoup, base_url: str) -> str:
        tag = soup.find("link", rel=re.compile("canonical", re.I))
        return urljoin(base_url, tag.get("href", "")) if tag and tag.get("href") else ""
