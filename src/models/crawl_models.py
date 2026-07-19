"""Data models used by the crawler and UI."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class PageResult:
    """Represents a crawled page and extracted audit data."""
    url: str
    status_code: int = 0
    title: str = ""
    depth: int = 0
    response_time: float = 0.0
    content_type: str = ""
    word_count: int = 0
    meta_description: str = ""
    h1: list[str] = field(default_factory=list)
    h2: list[str] = field(default_factory=list)
    canonical: str = ""
    meta_robots: str = ""
    open_graph: dict[str, str] = field(default_factory=dict)
    twitter_cards: dict[str, str] = field(default_factory=dict)
    structured_data: list[str] = field(default_factory=list)
    images: list[dict[str, Any]] = field(default_factory=list)
    links: list[dict[str, str]] = field(default_factory=list)
    resources: list[dict[str, str]] = field(default_factory=list)
    emails: set[str] = field(default_factory=set)
    social_links: dict[str, set[str]] = field(default_factory=dict)
    security_headers: dict[str, str] = field(default_factory=dict)
    issues: list[dict[str, str]] = field(default_factory=list)
    error: str = ""
