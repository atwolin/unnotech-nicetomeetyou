import scrapy


class UdnNewsItem(scrapy.Item):
    story_id = scrapy.Field()
    title = scrapy.Field()
    focus_title = scrapy.Field()  # title as shown in focus_body on the index page (may differ from detail page title)
    body = (
        scrapy.Field()
    )  # ordered list of typed blocks: text, image, tweet, video, livescore, player_card
    summary = scrapy.Field()
    url = scrapy.Field()
    image_url = scrapy.Field()
    author = scrapy.Field()
    category_id = scrapy.Field()
    category_name = scrapy.Field()
    published_at = scrapy.Field()
    modified_at = scrapy.Field()
    keywords = scrapy.Field()
