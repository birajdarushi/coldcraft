from __future__ import annotations

import hashlib
import json
import re
import urllib.error
import urllib.request
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse

from ...domain.errors import ScraperError
from ...domain.models import NormalizedJob


def stable_job_id(url: str) -> str:
    return hashlib.sha256(url.strip().lower().encode()).hexdigest()[:32]


def _validate_url_scheme(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise ScraperError(f"Unsupported URL scheme: {parsed.scheme or '(none)'}")
    return url


def _fetch_json(url: str, timeout: int = 20) -> object:
    _validate_url_scheme(url)
    req = urllib.request.Request(url, headers={"User-Agent": "ColdcraftScraper/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, json.JSONDecodeError, TimeoutError) as exc:
        raise ScraperError(f"Failed to fetch JSON from {url}: {exc}") from exc


def _fetch_html(url: str, timeout: int = 20) -> str:
    _validate_url_scheme(url)
    req = urllib.request.Request(url, headers={"User-Agent": "ColdcraftScraper/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except (urllib.error.URLError, TimeoutError) as exc:
        raise ScraperError(f"Failed to fetch HTML from {url}: {exc}") from exc


def _greenhouse_board(url: str) -> str | None:
    parsed = urlparse(url)
    host = parsed.netloc.lower()
    if "greenhouse.io" not in host:
        return None
    parts = [p for p in parsed.path.split("/") if p]
    if not parts:
        return None
    return parts[0]


def _lever_board(url: str) -> str | None:
    parsed = urlparse(url)
    host = parsed.netloc.lower()
    if host not in {"jobs.lever.co", "www.lever.co"}:
        return None
    parts = [p for p in parsed.path.split("/") if p]
    if not parts:
        return None
    return parts[0]


class _JsonLdParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._in_script = False
        self._buffer = ""
        self.payloads: list[object] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag != "script":
            return
        attrs_dict = dict(attrs)
        if attrs_dict.get("type") == "application/ld+json":
            self._in_script = True
            self._buffer = ""

    def handle_endtag(self, tag: str) -> None:
        if tag == "script" and self._in_script:
            self._in_script = False
            try:
                self.payloads.append(json.loads(self._buffer))
            except json.JSONDecodeError:
                pass
            self._buffer = ""

    def handle_data(self, data: str) -> None:
        if self._in_script:
            self._buffer += data


def _collect_job_postings(node: object) -> list[dict]:
    found: list[dict] = []
    if isinstance(node, list):
        for item in node:
            found.extend(_collect_job_postings(item))
    elif isinstance(node, dict):
        node_type = node.get("@type")
        if node_type == "JobPosting" or (
            isinstance(node_type, list) and "JobPosting" in node_type
        ):
            found.append(node)
        graph = node.get("@graph")
        if graph:
            found.extend(_collect_job_postings(graph))
    return found


def _normalize_json_ld(posting: dict, source_url: str, source: str) -> NormalizedJob | None:
    title = posting.get("title")
    if not title:
        return None
    job_url = posting.get("url") or posting.get("identifier") or source_url
    if isinstance(job_url, dict):
        job_url = job_url.get("@id") or source_url
    job_url = str(job_url)
    company = None
    hiring = posting.get("hiringOrganization")
    if isinstance(hiring, dict):
        company = hiring.get("name")
    location = None
    job_location = posting.get("jobLocation")
    if isinstance(job_location, dict):
        address = job_location.get("address")
        if isinstance(address, dict):
            location = address.get("addressLocality") or address.get("addressRegion")
        elif isinstance(job_location.get("name"), str):
            location = job_location["name"]
    description = posting.get("description")
    if isinstance(description, str):
        description = re.sub(r"<[^>]+>", " ", description)
        description = re.sub(r"\s+", " ", description).strip()[:4000]
    return NormalizedJob(
        id=stable_job_id(job_url),
        title=str(title).strip(),
        company=str(company).strip() if company else None,
        url=job_url,
        location=str(location).strip() if location else None,
        description=description,
        source=source,
    )


class CareersPageScraper:
    """Scrape normalized jobs from public career pages (Greenhouse, Lever, JSON-LD)."""

    def scrape(self, url: str, source: str = "careers_page") -> list[NormalizedJob]:
        board = _greenhouse_board(url)
        if board:
            return self._scrape_greenhouse(board, source)
        board = _lever_board(url)
        if board:
            return self._scrape_lever(board, source)
        return self._scrape_html(url, source)

    def _scrape_greenhouse(self, board: str, source: str) -> list[NormalizedJob]:
        api_url = f"https://boards-api.greenhouse.io/v1/boards/{board}/jobs?content=true"
        payload = _fetch_json(api_url)
        if not isinstance(payload, dict):
            raise ScraperError(f"Unexpected Greenhouse response for board {board}")
        jobs = payload.get("jobs") or []
        normalized: list[NormalizedJob] = []
        for job in jobs:
            if not isinstance(job, dict):
                continue
            title = job.get("title")
            absolute_url = job.get("absolute_url")
            if not title or not absolute_url:
                continue
            location = None
            locs = job.get("location") or {}
            if isinstance(locs, dict):
                location = locs.get("name")
            content = job.get("content")
            description = None
            if isinstance(content, str):
                description = re.sub(r"<[^>]+>", " ", content)
                description = re.sub(r"\s+", " ", description).strip()[:4000]
            normalized.append(
                NormalizedJob(
                    id=stable_job_id(absolute_url),
                    title=str(title).strip(),
                    company=board.replace("-", " ").title(),
                    url=absolute_url,
                    location=str(location).strip() if location else None,
                    description=description,
                    source=source,
                )
            )
        if not normalized:
            raise ScraperError(f"No jobs found on Greenhouse board {board}")
        return normalized

    def _scrape_lever(self, board: str, source: str) -> list[NormalizedJob]:
        api_url = f"https://api.lever.co/v0/postings/{board}?mode=json"
        payload = _fetch_json(api_url)
        if not isinstance(payload, list):
            raise ScraperError(f"Unexpected Lever response for board {board}")
        normalized: list[NormalizedJob] = []
        for job in payload:
            if not isinstance(job, dict):
                continue
            title = job.get("text")
            hosted = job.get("hostedUrl") or job.get("applyUrl")
            if not title or not hosted:
                continue
            categories = job.get("categories") or {}
            location = categories.get("location") if isinstance(categories, dict) else None
            description = job.get("descriptionPlain") or job.get("description")
            if isinstance(description, str):
                description = re.sub(r"<[^>]+>", " ", description)
                description = re.sub(r"\s+", " ", description).strip()[:4000]
            normalized.append(
                NormalizedJob(
                    id=stable_job_id(hosted),
                    title=str(title).strip(),
                    company=board.replace("-", " ").title(),
                    url=hosted,
                    location=str(location).strip() if location else None,
                    description=description,
                    source=source,
                )
            )
        if not normalized:
            raise ScraperError(f"No jobs found on Lever board {board}")
        return normalized

    def _scrape_html(self, url: str, source: str) -> list[NormalizedJob]:
        html = _fetch_html(url)
        parser = _JsonLdParser()
        parser.feed(html)
        normalized: list[NormalizedJob] = []
        for payload in parser.payloads:
            for posting in _collect_job_postings(payload):
                job = _normalize_json_ld(posting, url, source)
                if job:
                    normalized.append(job)
        if normalized:
            return normalized

        # Fallback: extract obvious job links from generic career pages.
        link_pattern = re.compile(
            r'href=["\']([^"\']*(?:/jobs?/|/careers?/|/position/)[^"\']*)["\']',
            re.IGNORECASE,
        )
        seen: set[str] = set()
        for match in link_pattern.finditer(html):
            href = urljoin(url, match.group(1))
            if href in seen:
                continue
            seen.add(href)
            slug = href.rstrip("/").split("/")[-1].replace("-", " ").title()
            if len(slug) < 4:
                continue
            normalized.append(
                NormalizedJob(
                    id=stable_job_id(href),
                    title=slug,
                    company=urlparse(url).netloc.replace("www.", "").split(".")[0].title(),
                    url=href,
                    location=None,
                    description=None,
                    source=source,
                )
            )
        if not normalized:
            raise ScraperError(f"No jobs found at {url}")
        return normalized