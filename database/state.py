from typing import Optional
from crud import ArticleData

# Global variable to store the current article instance
_current_article: Optional[ArticleData] = None


def set_current_article(article: ArticleData):
    global _current_article
    _current_article = article


def get_current_article() -> Optional[ArticleData]:
    return _current_article


def clear_current_article():
    global _current_article
    _current_article = None
