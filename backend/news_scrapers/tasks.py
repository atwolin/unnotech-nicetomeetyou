import logging
import re
import subprocess
import sys

from celery import shared_task
from django.conf import settings

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    name="news_scrapers.scrape_udn_news",
    soft_time_limit=15 * 60,
    time_limit=20 * 60,
    max_retries=3,
    acks_late=True,
    autoretry_for=(Exception,),
    retry_backoff=3 * 60,
    retry_backoff_max=10 * 60,
    retry_jitter=True,
)
def scrape_udn_news(self):
    """Run the UDN news spider as a subprocess.

    Timeout is managed by Celery: soft_time_limit raises SoftTimeLimitExceeded
    (triggering autoretry), while time_limit sends SIGKILL to the worker process
    and its child subprocess.
    """
    logger.info("Starting scheduled UDN news scrape (task_id=%s)", self.request.id)

    scrapers_dir = str(settings.BASE_DIR / "news_scrapers")

    result = subprocess.run(
        [sys.executable, "-m", "scrapy", "crawl", "udn_news"],
        cwd=scrapers_dir,
        capture_output=True,
        text=True,
    )

    if result.stderr:
        logger.info("Spider output (task_id=%s):\n%s", self.request.id, result.stderr)

    if result.returncode != 0:
        raise RuntimeError(f"Spider exited with code {result.returncode}")

    stderr = result.stderr or ""
    skipped_match = re.search(r"Skipped (\d+) already-scraped article", stderr)
    scraped_match = re.search(r"'item_scraped_count': (\d+)", stderr)
    skipped = int(skipped_match.group(1)) if skipped_match else 0
    scraped = int(scraped_match.group(1)) if scraped_match else 0

    logger.info(
        "Scrape completed (task_id=%s): scraped=%d, skipped=%d",
        self.request.id,
        scraped,
        skipped,
    )
    return {"status": "success", "scraped": scraped, "skipped": skipped}
