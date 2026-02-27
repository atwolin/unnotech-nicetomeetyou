from django.db import models


class Category(models.Model):
    """UDN category (e.g. 運動, NBA)."""

    category_id = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=100)

    class Meta:
        verbose_name_plural = "categories"

    def __str__(self):
        return f"{self.name} ({self.category_id})"


class Article(models.Model):
    """A news article scraped from UDN.

    Body blocks (``body`` field) are stored as an ordered JSON array.
    Each element is a dict with a ``type`` key and type-specific fields:

    - ``{"type": "text",        "value": str}``
    - ``{"type": "image",       "url": str, "caption": str}``
    - ``{"type": "tweet",       "url": str}``
    - ``{"type": "video",       "url": str}``
    - ``{"type": "livescore",   "data": dict}``
    - ``{"type": "player_card", "name": str, "url": str}``
    """

    # UDN identifiers
    story_id = models.CharField(max_length=20, unique=True)
    url = models.URLField(max_length=500, unique=True)

    # Titles
    title = models.CharField(max_length=500)
    focus_title = models.CharField(
        max_length=500,
        blank=True,
        help_text="Title as shown in the index page focus block; may differ from the article page title.",
    )

    # Metadata
    summary = models.TextField(blank=True)
    author = models.CharField(max_length=200, blank=True)
    keywords = models.CharField(max_length=500, blank=True)
    image_url = models.URLField(max_length=500, blank=True)
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="articles",
    )

    # Timestamps (sourced from UDN JSON-LD)
    published_at = models.DateTimeField(null=True, blank=True)
    modified_at = models.DateTimeField(null=True, blank=True)

    # Article body as an ordered list of typed content blocks
    body = models.JSONField(default=list)

    # Internal tracking
    scraped_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-published_at"]
        indexes = [
            models.Index(fields=["-published_at"]),
            models.Index(fields=["category"]),
        ]

    def __str__(self):
        return self.title
