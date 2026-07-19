"""Concurrent asyncio/aiohttp website crawler."""
from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Callable
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import aiohttp
import validators

from src.analyzer.seo_analyzer import SEOAnalyzer
from src.models.crawl_models import PageResult
from src.parser.html_parser import HTMLParser

LOGGER = logging.getLogger(__name__)
ProgressCallback = Callable[[PageResult], None]
StatusCallback = Callable[[str], None]


class AsyncCrawler:
    """Production-oriented crawler with pause, resume, stop, retry, and limits."""

    def __init__(self, on_page: ProgressCallback, on_status: StatusCallback) -> None:
        self.on_page = on_page
        self.on_status = on_status
        self.parser = HTMLParser()
        self.analyzer = SEOAnalyzer()
        self.visited: set[str] = set()
        self.running = False
        self.paused = False
        self._stop_event = asyncio.Event()
        self._pause_event = asyncio.Event()
        self._pause_event.set()
        self.robots: RobotFileParser | None = None

    async def crawl(self, start_url: str, max_depth: int, max_pages: int, concurrency: int, timeout: int, user_agent: str, respect_robots: bool) -> None:
        if not validators.url(start_url):
            self.on_status("Invalid start URL.")
            return
        self.running = True
        self._stop_event.clear()
        self.visited.clear()
        queue: asyncio.Queue[tuple[str, int]] = asyncio.Queue()
        await queue.put((start_url, 0))
        connector = aiohttp.TCPConnector(limit=max(1, concurrency), ssl=False)
        client_timeout = aiohttp.ClientTimeout(total=max(1, timeout))
        headers = {"User-Agent": user_agent or "SEO Inspector Pro/1.0"}
        if respect_robots:
            await self._load_robots(start_url, user_agent)
        async with aiohttp.ClientSession(connector=connector, timeout=client_timeout, headers=headers) as session:
            workers = [asyncio.create_task(self._worker(queue, session, start_url, max_depth, max_pages, user_agent)) for _ in range(max(1, concurrency))]
            await queue.join()
            for worker in workers:
                worker.cancel()
            await asyncio.gather(*workers, return_exceptions=True)
        self.running = False
        self.on_status("Crawl stopped." if self._stop_event.is_set() else "Crawl complete.")

    def pause(self) -> None:
        self.paused = True
        self._pause_event.clear()
        self.on_status("Crawl paused.")

    def resume(self) -> None:
        self.paused = False
        self._pause_event.set()
        self.on_status("Crawl resumed.")

    def stop(self) -> None:
        self._stop_event.set()
        self._pause_event.set()
        self.on_status("Stopping crawler...")

    async def _worker(self, queue: asyncio.Queue[tuple[str, int]], session: aiohttp.ClientSession, start_url: str, max_depth: int, max_pages: int, user_agent: str) -> None:
        while not self._stop_event.is_set():
            url, depth = await queue.get()
            try:
                await self._pause_event.wait()
                if url in self.visited or len(self.visited) >= max_pages or depth > max_depth:
                    continue
                if self.robots and not self.robots.can_fetch(user_agent, url):
                    LOGGER.info("Blocked by robots.txt: %s", url)
                    continue
                self.visited.add(url)
                page = await self._fetch(session, url, depth)
                self.on_page(page)
                if page.status_code < 400 and "text/html" in page.content_type and depth < max_depth:
                    for link in page.links:
                        child = link["url"]
                        if link["type"] == "internal" and child not in self.visited and len(self.visited) + queue.qsize() < max_pages:
                            await queue.put((child, depth + 1))
            except Exception as exc:
                LOGGER.exception("Crawler worker error for %s", url)
                self.on_page(PageResult(url=url, depth=depth, error=str(exc)))
            finally:
                queue.task_done()

    async def _fetch(self, session: aiohttp.ClientSession, url: str, depth: int) -> PageResult:
        started = time.perf_counter()
        for attempt in range(3):
            try:
                async with session.get(url, allow_redirects=True) as response:
                    body = await response.text(errors="ignore")
                    elapsed = time.perf_counter() - started
                    page = PageResult(url=str(response.url), status_code=response.status, depth=depth, response_time=elapsed, content_type=response.headers.get("Content-Type", ""), security_headers=dict(response.headers))
                    if "text/html" in page.content_type:
                        for key, value in self.parser.parse(body, str(response.url)).items():
                            setattr(page, key, value)
                    return self.analyzer.analyze(page)
            except (aiohttp.ClientError, asyncio.TimeoutError) as exc:
                LOGGER.warning("Fetch failed (%s/%s) for %s: %s", attempt + 1, 3, url, exc)
                await asyncio.sleep(0.4 * (attempt + 1))
        return PageResult(url=url, depth=depth, response_time=time.perf_counter() - started, error="Failed after retries")

    async def _load_robots(self, start_url: str, user_agent: str) -> None:
        parsed = urlparse(start_url)
        robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
        self.robots = RobotFileParser(robots_url)
        try:
            self.robots.read()
            self.on_status(f"Loaded robots.txt for {parsed.netloc}.")
        except Exception as exc:
            LOGGER.warning("Could not read robots.txt: %s", exc)
            self.robots = None
