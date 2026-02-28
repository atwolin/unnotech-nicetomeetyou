from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from .models import Article, Category
from .serializers import ArticleDetailSerializer, ArticleListSerializer


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_category(category_id="12345", name="NBA"):
    return Category.objects.create(category_id=category_id, name=name)


def make_article(
    story_id="1000001", title="Test Article", category=None, published_at=None, **kwargs
):
    return Article.objects.create(
        story_id=story_id,
        url=f"https://tw-nba.udn.com/nba/story/12345/{story_id}",
        title=title,
        category=category,
        published_at=published_at or timezone.now(),
        **kwargs,
    )


# ---------------------------------------------------------------------------
# Model tests
# ---------------------------------------------------------------------------


class CategoryModelTest(TestCase):
    def test_str_format(self):
        """__str__ should combine name and category_id."""
        cat = make_category(category_id="7002", name="運動")
        self.assertEqual(str(cat), "運動 (7002)")


class ArticleModelTest(TestCase):
    def test_str_returns_title(self):
        """__str__ should return the article title."""
        article = make_article(title="騎士雙塔童話")
        self.assertEqual(str(article), "騎士雙塔童話")

    def test_body_defaults_to_empty_list(self):
        """body field should default to [] when not provided."""
        article = make_article()
        self.assertEqual(article.body, [])

    def test_default_ordering_newest_first(self):
        """Articles should be ordered by published_at descending."""
        older = make_article(
            story_id="1000001",
            published_at=timezone.now() - timedelta(days=1),
        )
        newer = make_article(story_id="1000002", published_at=timezone.now())
        articles = list(Article.objects.all())
        self.assertEqual(articles[0], newer)
        self.assertEqual(articles[1], older)


# ---------------------------------------------------------------------------
# Serializer tests
# ---------------------------------------------------------------------------


class ArticleSerializerTest(TestCase):
    def setUp(self):
        self.category = make_category()
        self.article = make_article(
            category=self.category,
            body=[{"type": "text", "value": "content"}],
        )

    def test_list_serializer_excludes_body(self):
        """List serializer must not expose body to keep responses lightweight."""
        data = ArticleListSerializer(self.article).data
        self.assertNotIn("body", data)

    def test_detail_serializer_includes_body(self):
        """Detail serializer must expose body with the full block list."""
        data = ArticleDetailSerializer(self.article).data
        self.assertIn("body", data)
        self.assertEqual(data["body"], [{"type": "text", "value": "content"}])

    def test_category_serialized_as_nested_object(self):
        """category should be a nested object, not a raw foreign-key integer."""
        data = ArticleDetailSerializer(self.article).data
        self.assertIsInstance(data["category"], dict)
        self.assertEqual(data["category"]["category_id"], self.category.category_id)
        self.assertEqual(data["category"]["name"], self.category.name)


# ---------------------------------------------------------------------------
# API view tests
# ---------------------------------------------------------------------------


class ArticleAPITest(APITestCase):
    def setUp(self):
        self.nba_cat = make_category(category_id="7002", name="NBA")
        self.sport_cat = make_category(category_id="7001", name="運動")
        self.article_nba = make_article(
            story_id="1000001",
            title="騎士文章",
            category=self.nba_cat,
            body=[{"type": "text", "value": "body content"}],
        )
        self.article_sport = make_article(
            story_id="1000002",
            title="湖人文章",
            category=self.sport_cat,
        )

    def test_list_endpoint_omits_body(self):
        """List endpoint must use ArticleListSerializer (no body field)."""
        response = self.client.get(reverse("article-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        for item in response.data["results"]:
            self.assertNotIn("body", item)

    def test_detail_endpoint_includes_body(self):
        """Detail endpoint must use ArticleDetailSerializer (body present)."""
        response = self.client.get(
            reverse("article-detail", args=[self.article_nba.id])
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("body", response.data)

    def test_category_filter_returns_matching_articles_only(self):
        """?category= must filter via our custom get_queryset logic."""
        response = self.client.get(reverse("article-list"), {"category": "7002"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        story_ids = [item["story_id"] for item in response.data["results"]]
        self.assertIn("1000001", story_ids)
        self.assertNotIn("1000002", story_ids)

    def test_category_filter_unknown_id_returns_empty(self):
        """?category= with no matching category_id should return zero results."""
        response = self.client.get(reverse("article-list"), {"category": "9999"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 0)
