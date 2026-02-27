from rest_framework import serializers

from .models import Article, Category


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "category_id", "name"]


class ArticleListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for list endpoints — excludes body."""

    category = CategorySerializer(read_only=True)

    class Meta:
        model = Article
        fields = [
            "id",
            "story_id",
            "url",
            "title",
            "focus_title",
            "summary",
            "author",
            "keywords",
            "image_url",
            "category",
            "published_at",
            "modified_at",
            "scraped_at",
        ]


class ArticleDetailSerializer(serializers.ModelSerializer):
    """Full serializer for detail endpoints — includes body."""

    category = CategorySerializer(read_only=True)

    class Meta:
        model = Article
        fields = [
            "id",
            "story_id",
            "url",
            "title",
            "focus_title",
            "summary",
            "author",
            "keywords",
            "image_url",
            "category",
            "published_at",
            "modified_at",
            "body",
            "scraped_at",
            "updated_at",
        ]
