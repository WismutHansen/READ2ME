from sqlalchemy.orm import Session
from . import models
from datetime import datetime
import hashlib
import base64



def create_article(db: Session, article_data: dict):
    db_article = models.Article(**article_data)
    db.add(db_article)
    db.commit()
    db.refresh(db_article)
    return db_article

def get_articles(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Article).order_by(models.Article.date_added.desc()).offset(skip).limit(limit).all()

def get_article(db: Session, article_id: str):
    return db.query(models.Article).filter(models.Article.id == article_id).first()

def get_total_articles(db: Session):
    return db.query(models.Article).count()


def create_text(db: Session, text_data: dict):
    db_text = models.Text(**text_data)
    db.add(db_text)
    db.commit()
    db.refresh(db_text)
    return db_text

# We calculate unique identifieres for each article using the URL, 
# encode it with base64 and shorten it to 6 characters.
# This way we can check if an article has already been added to the database

def generate_hash(url: str) -> str:
    hash_object = hashlib.sha256(url.encode())
    hash_digest = hash_object.digest()
    return base64.urlsafe_b64encode(hash_digest)[:6].decode('utf-8') 

def article_exists(url):
    article_id = generate_hash(url)
    return session.query(Article).filter_by(id=article_id).first() is not None

if __name__ == "__main__":
    Title = print(Input(Please enter article title: ))
    text = print(Input(Please enter Text))                 
