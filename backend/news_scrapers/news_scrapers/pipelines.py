from django.db import DatabaseError
from django.utils.dateparse import parse_datetime

from news.models import Article, Category
from scrapy.exceptions import DropItem
from twisted.internet.threads import deferToThread


class NewsScrapersPipeline:
    """Persists scraped items to the Django database.

    On spider open, pre-loads all existing ``story_id`` values into
    ``spider.existing_story_ids`` so the spider can skip detail-page
    requests for articles that are already in the database.

    All Django ORM calls are run via ``deferToThread`` to avoid
    ``SynchronousOnlyOperation`` errors from Twisted's async event loop.
    """

    def open_spider(self, spider):
        return deferToThread(self._load_existing_ids, spider)

    def _load_existing_ids(self, spider):
        try:
            spider.existing_story_ids = set(
                Article.objects.values_list("story_id", flat=True)
            )
            spider.logger.info(
                f"NewsScrapersPipeline: {len(spider.existing_story_ids)} articles already in DB"
            )
        except DatabaseError as exc:
            # DB unreachable at startup — spider continues with an empty set,
            # meaning all focus articles will be re-fetched this run.
            spider.logger.error(f"Failed to load existing story IDs from DB: {exc}")

    def process_item(self, item, spider):
        return deferToThread(self._save_item, item)

    def _save_item(self, item):
        try:
            category = None
            if item.get("category_id"):
                category, _ = Category.objects.get_or_create(
                    category_id=item["category_id"],
                    defaults={"name": item.get("category_name", "")},
                )

            Article.objects.update_or_create(
                story_id=item["story_id"],
                defaults={
                    "url": item.get("url", ""),
                    "title": item.get("title", ""),
                    "focus_title": item.get("focus_title", ""),
                    "summary": item.get("summary", ""),
                    "author": item.get("author", ""),
                    "keywords": item.get("keywords", ""),
                    "image_url": item.get("image_url", ""),
                    "category": category,
                    "published_at": parse_datetime(item.get("published_at") or ""),
                    "modified_at": parse_datetime(item.get("modified_at") or ""),
                    "body": item.get("body", []),
                },
            )
        except DatabaseError as exc:
            raise DropItem(f"DB error saving story_id={item.get('story_id')}: {exc}")

        return item
