import subprocess
import sys

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Run the UDN news spider to scrape the latest articles."

    def add_arguments(self, parser):
        parser.add_argument(
            "--spider",
            type=str,
            default="udn_news",
            help="Name of the spider to run (default: udn_news)",
        )
        parser.add_argument(
            "--timeout",
            type=int,
            default=300,
            help="Maximum seconds to allow the crawl to run (default: 300)",
        )

    def handle(self, *args, **options):
        spider_name = options["spider"]
        timeout = options["timeout"]

        # Running from this directory ensures "from news_scrapers.items import ..."
        # in spiders resolves to the inner Scrapy package, not the outer Django app.
        scrapers_dir = str(settings.BASE_DIR / "news_scrapers")

        self.stdout.write(f"Starting spider '{spider_name}' ...")
        try:
            result = subprocess.run(
                [sys.executable, "-m", "scrapy", "crawl", spider_name],
                cwd=scrapers_dir,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
        except subprocess.TimeoutExpired:
            raise CommandError(f"Spider '{spider_name}' timed out after {timeout}s.")

        if result.stdout:
            self.stdout.write(result.stdout)
        if result.stderr:
            self.stderr.write(result.stderr)

        if result.returncode != 0:
            raise CommandError(
                f"Spider '{spider_name}' exited with code {result.returncode}."
            )

        self.stdout.write(
            self.style.SUCCESS(f"Spider '{spider_name}' completed successfully.")
        )
