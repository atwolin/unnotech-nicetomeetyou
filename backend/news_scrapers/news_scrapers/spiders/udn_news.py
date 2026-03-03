import difflib
import json
import re
from urllib.parse import urlparse

import scrapy
from scrapy.spidermiddlewares.httperror import HttpError

from news_scrapers.items import UdnNewsItem


class UdnNewsSpider(scrapy.Spider):
    name = "udn_news"
    allowed_domains = ["tw-nba.udn.com"]
    start_urls = ["https://tw-nba.udn.com/nba/index"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Populated by DjangoPipeline.open_spider; fallback to empty set so the
        # spider still works when the pipeline is disabled (e.g. during testing).
        self.existing_story_ids: set[str] = set()

    def parse(self, response):
        """Phase 1: Parse the index page and extract focus news article URLs.

        story_id is embedded in every article URL path
        (/nba/story/{category_id}/{story_id}), so we can skip already-scraped
        articles here — before making any detail-page HTTP requests.

        Some focus_body links have broken href values (e.g. '_blank', 'N', '?')
        due to a CMS bug on the UDN side.  When a link is invalid we fall back to
        fuzzy-matching the focus title against the title→URL map built from all
        other valid story links on the same page.
        """
        seen_urls: set[str] = set()
        skipped = 0

        # Build a page-wide title → URL map from every valid story link.
        title_url_map = self._build_title_url_map(response)

        for a in response.css(".focus_body a"):
            link = a.attrib.get("href", "")

            # Prefer the anchor's title attribute; fall back to inner text.
            raw_title = (a.attrib.get("title") or "").strip()
            if not raw_title:
                raw_title = " ".join(
                    t.strip() for t in a.css("::text").getall() if t.strip()
                )

            # Try to use the href directly if it already points to a story page.
            clean_url = self._clean_url(link)
            path = urlparse(clean_url).path if clean_url else ""
            if not re.search(r"/nba/story/\d+/\d+", path):
                # href is broken → look up the correct URL by fuzzy title match.
                clean_url = self._fuzzy_find_url(raw_title, title_url_map)
                if not clean_url:
                    self.logger.warning(
                        f"No story URL found for focus item: {raw_title!r}"
                    )
                    continue

            if clean_url in seen_urls:
                continue
            seen_urls.add(clean_url)

            # Extract story_id directly from the URL path
            path = urlparse(clean_url).path
            m = re.search(r"/nba/story/\d+/(\d+)", path)
            story_id = m.group(1) if m else None

            if story_id and story_id in self.existing_story_ids:
                skipped += 1
                continue

            yield scrapy.Request(
                url=clean_url,
                callback=self.parse_article,
                errback=self.handle_http_error,
                meta={"focus_title": raw_title},
            )

        if not seen_urls:
            self.logger.warning("No focus news links found on the index page.")
        elif skipped:
            self.logger.info(f"Skipped {skipped} already-scraped article(s).")

    def parse_article(self, response):
        """Phase 2: Parse an individual article page and extract all fields."""
        item = UdnNewsItem()

        # Extract story_id and category_id from URL path
        # URL pattern: /nba/story/{category_id}/{story_id}
        path = urlparse(response.url).path
        path_match = re.search(r"/nba/story/(\d+)/(\d+)", path)
        if path_match:
            item["category_id"] = path_match.group(1)
            item["story_id"] = path_match.group(2)
        else:
            item["category_id"] = response.css("#story_body::attr(data-sub)").get("")
            item["story_id"] = response.css("#story_body::attr(data-article)").get("")

        if not item.get("story_id"):
            self.logger.warning(f"Could not extract story_id from {response.url}")
            return

        item["url"] = self._clean_url(response.url)
        item["focus_title"] = response.meta.get("focus_title", "")

        # Try JSON-LD first (most reliable), fall back to HTML selectors
        json_ld = self._extract_json_ld(response)

        if json_ld:
            self._populate_from_json_ld(item, json_ld)
        else:
            self.logger.warning(
                f"No JSON-LD found for {response.url}, using HTML fallback"
            )
            self._populate_from_html(item, response)

        # Extract article body content (always from HTML)
        item["body"] = self._extract_body(response)

        yield item

    def handle_http_error(self, failure):
        """Errback for article detail requests.

        Logs the failure and discards the request so one bad URL cannot
        interrupt the rest of the crawl.
        """
        if failure.check(HttpError):
            response = failure.value.response
            self.logger.error(
                f"HTTP {response.status} fetching article: {response.url}"
            )
        else:
            self.logger.error(
                f"Request failed ({failure.type.__name__}): "
                f"{failure.getErrorMessage()} — {failure.request.url}"
            )

    def _populate_from_json_ld(self, item, json_ld):
        """Populate item fields from JSON-LD structured data."""
        item["title"] = json_ld.get("headline", "")
        item["summary"] = json_ld.get("description", "")
        item["published_at"] = json_ld.get("datePublished", "")
        item["modified_at"] = json_ld.get("dateModified", "")
        item["keywords"] = json_ld.get("keywords", "")
        item["category_name"] = json_ld.get("articleSection", "")

        author = json_ld.get("author", {})
        item["author"] = author.get("name", "") if isinstance(author, dict) else ""

        image = json_ld.get("image", {})
        if isinstance(image, dict):
            item["image_url"] = image.get("contentUrl", image.get("url", ""))
        elif isinstance(image, str):
            item["image_url"] = image
        else:
            item["image_url"] = ""

    def _populate_from_html(self, item, response):
        """Populate item fields from HTML selectors as fallback."""
        item["title"] = response.css("h1.story_art_title::text").get("").strip()
        item["summary"] = ""
        item["image_url"] = ""
        item["author"] = ""
        item["category_name"] = ""
        item["keywords"] = ""
        item["published_at"] = (
            response.css(".shareBar__info--author span::text").get("").strip()
        )
        item["modified_at"] = ""

    def _extract_json_ld(self, response):
        """Extract NewsArticle JSON-LD from the page."""
        for script_text in response.css(
            'script[type="application/ld+json"]::text'
        ).getall():
            try:
                # strict=False allows literal control characters in string values
                # (some UDN articles embed raw newlines inside JSON strings)
                data = json.loads(script_text, strict=False)
                if isinstance(data, dict) and data.get("@type") == "NewsArticle":
                    return data
                if isinstance(data, list):
                    for entry in data:
                        if (
                            isinstance(entry, dict)
                            and entry.get("@type") == "NewsArticle"
                        ):
                            return entry
            except json.JSONDecodeError:
                continue
        return None

    def _extract_body(self, response):
        """Extract article body as an ordered list of typed content blocks.

        Block types:
          {"type": "text",        "value": str}
          {"type": "image",       "url": str, "caption": str}
          {"type": "tweet",       "url": str}
          {"type": "video",       "url": str}
          {"type": "livescore",   "data": dict}
          {"type": "player_card", "name": str, "url": str}
        """
        blocks = []
        container = response.css("#story_body_content")
        if not container:
            return blocks

        # Pre-load livescores so each inline liveupdates widget can reference
        # the corresponding game data in document order.
        livescores = self._extract_livescores(response)
        livescore_idx = 0

        for el in container.xpath(".//figure | .//p[not(ancestor::figure)]"):
            tag = el.root.tag

            if tag == "figure":
                url = el.css("img::attr(src)").get("") or el.css(
                    "img::attr(data-src)"
                ).get("")
                caption = " ".join(
                    t.strip() for t in el.css("figcaption ::text").getall() if t.strip()
                )
                if url:
                    blocks.append({"type": "image", "url": url, "caption": caption})

            elif tag == "p":
                # Livescore widget — consume the next game from the pre-loaded list
                if el.xpath(
                    'self::*[contains(@class,"liveupdates")]'
                    ' | .//*[contains(@class,"liveupdates")]'
                ):
                    if livescore_idx < len(livescores):
                        blocks.append(
                            {"type": "livescore", "data": livescores[livescore_idx]}
                        )
                        livescore_idx += 1
                    continue

                # Player card links — one block per anchor
                player_card_anchors = el.css("a.player_card_link")
                if player_card_anchors:
                    for anchor in player_card_anchors:
                        card_url = anchor.css("::attr(href)").get("")
                        card_name = " ".join(
                            t.strip()
                            for t in anchor.css("::text").getall()
                            if t.strip()
                        )
                        if card_url:
                            blocks.append(
                                {
                                    "type": "player_card",
                                    "name": card_name,
                                    "url": card_url,
                                }
                            )
                    continue

                # Embedded tweet: <p lang="..."> wrapping a tweet blockquote/link
                if el.root.get("lang"):
                    tweet_url = el.css('a[href*="twitter.com"]::attr(href)').get(
                        ""
                    ) or el.css('a[href*="x.com"]::attr(href)').get("")
                    if tweet_url:
                        blocks.append({"type": "tweet", "url": tweet_url})
                    continue

                # Embedded video: <p> containing an <iframe>
                iframe_src = el.css("iframe::attr(src)").get("")
                if iframe_src:
                    blocks.append({"type": "video", "url": iframe_src})
                    continue

                # Skip paragraphs that only contain scripts
                if el.css("script") and not el.xpath(
                    ".//text()[not(ancestor::script)]"
                ):
                    continue

                # Plain text paragraph
                texts = el.xpath(".//text()[not(ancestor::figure)]").getall()
                text = " ".join(t.strip() for t in texts if t.strip())
                if text:
                    blocks.append({"type": "text", "value": text})

        return blocks

    def _extract_livescores(self, response):
        """Extract live score data embedded as window.sGame in inline scripts."""
        for script_text in response.css("script:not([src])::text").getall():
            match = re.search(r"window\.sGame\s*=\s*(\[.*?\]);", script_text, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(1))
                except json.JSONDecodeError:
                    continue
        return []

    def _clean_url(self, url):
        """Remove tracking query params and ensure absolute URL."""
        if not url:
            return None
        if url.startswith("/"):
            url = f"https://tw-nba.udn.com{url}"
        parsed = urlparse(url)
        return f"{parsed.scheme}://{parsed.netloc}{parsed.path}"

    # ------------------------------------------------------------------
    # Focus-news URL recovery helpers
    # ------------------------------------------------------------------

    def _build_title_url_map(self, response) -> dict[str, str]:
        """Scan every valid story link on the page and return a
        normalised-title → clean_url mapping.

        Used as a fallback when a focus_body link has a broken href.
        """
        title_map: dict[str, str] = {}
        for a in response.css('a[href*="/nba/story/"]'):
            href = a.attrib.get("href", "")
            url = self._clean_url(href)
            if not url:
                continue
            title = (a.attrib.get("title") or "").strip()
            if not title:
                title = " ".join(
                    t.strip() for t in a.css("::text").getall() if t.strip()
                )
            if title:
                title_map[self._normalize_title(title)] = url
        return title_map

    def _normalize_title(self, title: str) -> str:
        """Strip category prefixes like 'NBA／' or '世界盃男籃／' and whitespace."""
        return re.sub(r"^[^／]+／", "", title).strip()

    def _fuzzy_find_url(
        self,
        focus_title: str,
        title_url_map: dict[str, str],
        threshold: float = 0.7,
    ) -> str | None:
        """Return the story URL whose normalised title best matches `focus_title`.

        Focus titles are often edited / shortened versions of the full NBA-news
        titles, so we use difflib.SequenceMatcher for similarity scoring rather
        than an exact-match lookup.  Only returns a URL when the best ratio is
        at least `threshold`.
        """
        normalized_focus = self._normalize_title(focus_title)
        best_ratio = 0.0
        best_url: str | None = None
        for title, url in title_url_map.items():
            ratio = difflib.SequenceMatcher(None, normalized_focus, title).ratio()
            if ratio > best_ratio:
                best_ratio = ratio
                best_url = url
        if best_ratio >= threshold:
            self.logger.debug(f"Fuzzy match ({best_ratio:.2f}) for {focus_title!r}")
            return best_url
        return None
