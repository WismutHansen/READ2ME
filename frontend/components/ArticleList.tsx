'use client';

import { useState, useEffect } from 'react';
import { Button } from "@/components/ui/button";

interface Article {
  id: string;
  title: string;
  date: string;
  audio_file: string;
}

interface ArticleListProps {
  onSelectArticle: (article: Article) => void;
}

export default function ArticleList({ onSelectArticle }: ArticleListProps) {
  const [articles, setArticles] = useState<Article[]>([]);
  const [page, setPage] = useState(1);
  const [hasMore, setHasMore] = useState(true);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchArticles();
  }, []);

  const fetchArticles = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await fetch(`http://localhost:7777/v1/articles?page=${page}&limit=20`);
      if (!response.ok) {
        throw new Error('Failed to fetch articles');
      }
      const data = await response.json();
      if (data.articles.length === 0) {
        setHasMore(false);
      } else {
        setArticles(prevArticles => [...prevArticles, ...data.articles]);
        setPage(prevPage => prevPage + 1);
      }
    } catch (error) {
      console.error('Error fetching articles:', error);
      setError('Failed to load articles. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleSelectArticle = (article: Article) => {
    console.log('Article selected:', article);
    onSelectArticle(article);
  };

  if (error) {
    return <div className="text-red-500">{error}</div>;
  }

  return (
    <div>
      {articles.length === 0 && !isLoading ? (
        <div>No articles found.</div>
      ) : (
        <ul className="space-y-4">
          {articles.map((article) => (
            <li key={article.id} className="border p-4 rounded-md">
              <h3 className="text-lg font-semibold">{article.title}</h3>
              <p className="text-sm text-gray-500">Date: {article.date}</p>
              <Button onClick={() => handleSelectArticle(article)} className="mt-2">
                Play Article
              </Button>
            </li>
          ))}
        </ul>
      )}
      {isLoading && <div>Loading...</div>}
      {hasMore && (
        <Button onClick={fetchArticles} className="mt-4" disabled={isLoading}>
          {isLoading ? 'Loading...' : 'Load More'}
        </Button>
      )}
    </div>
  );
}