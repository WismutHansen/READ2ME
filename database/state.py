from typing import Optional
from .crud import ArticleData, TextData, PodcastData

# Global variable to store the current article instance
_current_article: Optional[ArticleData] = None
_current_text: Optional[TextData] = None
_current_podcast: Optional[PodcastData] = None


def set_current_article(article: ArticleData):
    global _current_article
    _current_article = article


def get_current_article() -> Optional[ArticleData]:
    return _current_article


def clear_current_article():
    global _current_article
    _current_article = None


def set_current_text(text: TextData):
    global _current_text
    _current_text = text


def get_current_text() -> Optional[TextData]:
    return _current_text


def clear_current_text():
    global _current_text
    _current_text = None


def set_current_podcast(podcast: PodcastData):
    global _current_podcast
    _current_podcast = podcast


def get_current_podcast() -> Optional[PodcastData]:
    return _current_podcast


def clear_current_podcast():
    global _current_podcast
    _current_podcast = None
