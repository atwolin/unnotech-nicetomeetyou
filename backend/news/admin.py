from django.contrib import admin

from .models import Article, Category


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "category_id")
    search_fields = ("name", "category_id")


@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    list_display = ("title", "author", "category", "published_at", "scraped_at")
    list_filter = ("category",)
    search_fields = ("title", "focus_title", "summary", "author")
    readonly_fields = ("story_id", "url", "scraped_at", "updated_at")
    date_hierarchy = "published_at"
