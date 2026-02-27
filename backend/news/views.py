from rest_framework import filters, viewsets

from .models import Article, Category
from .serializers import (
    ArticleDetailSerializer,
    ArticleListSerializer,
    CategorySerializer,
)


class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer


class ArticleViewSet(viewsets.ReadOnlyModelViewSet):
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["title", "focus_title", "summary", "author"]
    ordering_fields = ["published_at", "modified_at", "scraped_at"]
    ordering = ["-published_at"]

    def get_queryset(self):
        qs = Article.objects.select_related("category")
        category_id = self.request.query_params.get("category")
        if category_id:
            qs = qs.filter(category__category_id=category_id)
        return qs

    def get_serializer_class(self):
        if self.action == "retrieve":
            return ArticleDetailSerializer
        return ArticleListSerializer
