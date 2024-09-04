'use client';

import { useState, useEffect, useRef } from 'react';
import Image from 'next/image';
import { Button } from "@/components/ui/button";

interface Article {
  id: string;
  title: string;
  date: string;
  audio_file: string;
  image_url?: string;
  source_name: string;
  source_logo_url?: string;
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

  const audioRef = useRef<HTMLAudioElement | null>(null);

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
    // Stop any currently playing audio
    if (audioRef.current) {
      audioRef.current.pause();
    }
    
    // Create and play new audio
    audioRef.current = new Audio(article.audio_file);
    audioRef.current.play().catch(error => {
      console.error('Error playing audio:', error);
    });

    // Call the onSelectArticle prop to update the parent component
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
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
          {articles.map((article) => (
            <div key={article.id} className="border rounded-md overflow-hidden shadow-md cursor-pointer" onClick={() => handleSelectArticle(article)}>
              <div className="relative h-40">
                <Image
                  src={article.image_url || '/placeholder-image.jpg'}
                  alt={article.title}
                  layout="fill"
                  objectFit="cover"
                />
              </div>
              <div className="p-4">
                <h3 className="text-lg font-semibold line-clamp-2">{article.title}</h3>
                <div className="mt-2 flex items-center">
                  {article.source_logo_url ? (
                    <Image
                      src={article.source_logo_url}
                      alt={article.source_name}
                      width={20}
                      height={20}
                      className="mr-2"
                    />
                  ) : (
                    <span className="mr-2 font-bold">{article.source_name}</span>
                  )}
                  <span className="text-sm text-gray-500">{article.date}</span>
                </div>
              </div>
            </div>
          ))}
        </div>
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