'use client';

import { forwardRef, useImperativeHandle, useState, useEffect, useRef } from 'react';
import Image from 'next/image';
import { Button } from "@/components/ui/button";
import getSettings from "@/lib/settings";

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
  onSelectArticle?: (article: Article) => void;
}

export interface ArticleListRef {
  refresh: () => Promise<void>;
}

const ArticleList = forwardRef<ArticleListRef, ArticleListProps>(({ onSelectArticle }, ref) => {
  const [articles, setArticles] = useState<Article[]>([]);
  const [page, setPage] = useState(1);
  const [hasMore, setHasMore] = useState(true);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  const fetchArticles = async (pageNum: number) => {
    setIsLoading(true);
    setError(null);
    try {
      const { serverUrl } = getSettings();
      const LIMIT = 20;
      const response = await fetch(`${serverUrl}/v1/articles?page=${pageNum}&limit=${LIMIT}`);

      if (!response.ok) {
        throw new Error('Failed to fetch articles');
      }

      const data = await response.json();

      const newArticles = data.articles || [];

      setArticles(prevArticles => {
        // Replace previous articles only if pageNum is 1, otherwise append
        return pageNum === 1 ? newArticles : [...prevArticles, ...newArticles];
      });

      // Set hasMore based on whether more articles exist
      setHasMore(newArticles.length === LIMIT);

    } catch (error) {
      console.error('Error fetching articles:', error);
      setError('Failed to load articles. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  // Ensure articles are fetched correctly on page change
  useEffect(() => {
    fetchArticles(page);
  }, [page]);

  const loadMore = () => {
    if (hasMore && !isLoading) {
      setPage((prevPage) => prevPage + 1);
    }
  };

  const handleSelectArticle = (article: Article) => {
    if (audioRef.current) {
      audioRef.current.pause();
    }

    audioRef.current = new Audio(article.audio_file);
    audioRef.current.play().catch(error => {
      console.error('Error playing audio:', error);
    });

    onSelectArticle?.(article);
  };

  if (error) {
    return <div className="text-red-500">{error}</div>;
  }

  return (
    <>
      {/* Articles list */}
      <div className="grid grid-cols-2 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4">
        {articles.map((article) => (
          <div
            key={article.id}
            className="border rounded-lg overflow-hidden shadow-sm cursor-pointer hover:bg-accent"
            onClick={() => handleSelectArticle(article)}
          >
            {/* Article image */}
            <div className="relative aspect-square">
              <Image
                src={article.image_url || '/placeholder-image.jpg'}
                alt={article.title}
                fill
                className="object-cover"
                sizes="(max-width: 768px) 100vw, (max-width: 1200px) 50vw, 33vw"
              />
            </div>
            {/* Article details */}
            <div className="p-4">
              <div className="flex items-center gap-2 mb-2">
                {article.source_logo_url && (
                  <div className="relative w-4 h-4">
                    <Image
                      src={article.source_logo_url}
                      alt={article.source_name}
                      fill
                      className="object-contain"
                      sizes="16px"
                    />
                  </div>
                )}
                <span className="text-sm text-muted-foreground">{article.source_name}</span>
              </div>
              <h3 className="font-medium line-clamp-2">{article.title}</h3>
              <p className="text-sm text-muted-foreground mt-1">{article.date}</p>
            </div>
          </div>
        ))}
      </div>

      {/* Load More button */}
      {hasMore && (
        <div className="mt-8 flex justify-center">
          <Button onClick={loadMore} variant="outline" disabled={isLoading}>
            {isLoading ? 'Loading...' : 'Load More Articles'}
          </Button>
        </div>
      )}
    </>
  );
});

ArticleList.displayName = 'ArticleList';

export default ArticleList;
