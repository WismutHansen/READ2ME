from sqlalchemy import Column, String, Date, Table, ForeignKey
from .database import Base
from datetime import date
from sqlalchemy.orm import relationship
from .crud import generate_hash


article_author_association = Table(
    "article_author",
    Base.metadata,
    Column("article_id", String, ForeignKey("articles.id")),
    Column("author_id", String, ForeignKey("authors.id")),
)


class Article(Base):
    __tablename__ = "articles"

    id = Column(String, primary_key=True, index=True)
    url = Column(String)
    title = Column(String)
    date_published = Column(Date, nullable=True)
    date_added = Column(Date, default=date.today)
    authors = relationship(
        "Author", secondary=article_author_association, back_populates="articles"
    )
    language = Column(String)
    plain_text = Column(String)
    markdown_text = Column(String)
    tl_dr = Column(String)
    audio_file = Column(String)
    markdown_file = Column(String)
    vtt_file = Column(String)

    def __init__(self, url, title, text, date_published=None, date_added=None, authors=None, language=None, plain_text=None, markdown_text=None, tl_dr=None, audio_file=None, markdown_file=None, vtt_file=None):
        self.id = generate_hash(url)
        self.url = url
        self.title = title
        self.text = text
        self.date_published = date_published
        self.date_added = date_added
        self.authors = authors
        self.language = language
        self.plain_text = plain_text
        self.markdown_text = markdown_text
        self.tl_dr = tl_dr
        self.audio_file = audio_file
        self.markdown_file = markdown_file
        self.vtt_file = vtt_file



class Author(Base):
    __tablename__ = "authors"
    id = Column(String, primary_key=True)
    name = Column(String, unique=True)
    articles = relationship(
        "Article", secondary=article_author_association, back_populates="authors"
    )

    def __init__(self, name):
        self.id = generate_hash(name)
        self.name = name


class Plaintext(Base):
    __tablename__ = "texts"

    id = Column(String, primary_key=True, index=True)
    text = Column(String)
    date_added = Column(Date)
    language = Column(String)
    plain_text = Column(String)


class Book(Base):
    __tablename__ = "books"

    id = Column(String, primary_key=True, index=True)
    title = String
    text = Column(String)
    chapters = Column(String)
    date_added = Column(Date)
    language = Column(String)
    epub_file = Column(String)
