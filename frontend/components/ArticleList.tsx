'use client';

import { forwardRef, useEffect, useState, useImperativeHandle } from "react";
import { getSettings } from "@/lib/settings";

const formatDate = (dateString: string) => {
  const date = new Date(dateString);
  return date.toLocaleDateString('en-US', {
    month: 'long',
    day: 'numeric',
    year: 'numeric'
  });
};

interface Article {
  id: string;
  title: string | null;
  source: string | null;
  date_added: string;
  date_published?: string;
  audio_file: string;
  content_type: 'article' | 'podcast' | 'text';
  url?: string;
  text?: string;
  date?: string;
  audioUrl?: string;
  tlDr?: string;
}

interface ArticleListProps {
  onSelectArticle: (article: Article) => void;
}

export interface ArticleListRef {
  refresh: () => Promise<void>;
}

const ArticleList = forwardRef<ArticleListRef, ArticleListProps>(({ onSelectArticle }, ref) => {
  const [articles, setArticles] = useState<Article[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchArticles = async () => {
    setIsLoading(true);
    setError(null);

    try {
      const settings = getSettings();
      const response = await fetch(`${settings.serverUrl}/v1/available-media`, {
        credentials: 'include',
      });

      if (!response.ok) {
        throw new Error(`Failed to fetch articles: ${response.statusText}`);
      }

      const data = await response.json();

      // Validate and transform the response data
      const validArticles = data.map((item: any) => {
        if (!item.id || !item.content_type || !['article', 'podcast', 'text'].includes(item.content_type)) {
          console.warn('Invalid article data:', item);
          return null;
        }

        return {
          id: item.id,
          title: item.title,
          source: item.source,
          date_added: item.date_added,
          date_published: item.date_published,
          audio_file: item.audio_file,
          content_type: item.content_type,
          url: item.url
        };
      }).filter(Boolean);

      // Sort articles by date, most recent first
      const sortedArticles = validArticles.sort((a, b) => {
        const dateA = new Date(a.date_published || a.date_added);
        const dateB = new Date(b.date_published || b.date_added);
        return dateB.getTime() - dateA.getTime();
      });

      setArticles(sortedArticles);
    } catch (err) {
      console.error('Error fetching articles:', err);
      setError(err instanceof Error ? err.message : 'Failed to load articles');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchArticles();
  }, []);

  useImperativeHandle(ref, () => ({
    refresh: fetchArticles
  }));

  const handleArticleClick = async (article: Article) => {
    try {
      onSelectArticle(article);
    } catch (err) {
      console.error('Error handling article click:', err);
      setError(err instanceof Error ? err.message : 'Failed to load article');
    }
  };

  const getSourceDomain = (url: string | undefined) => {
    if (!url) return null;
    try {
      const urlObj = new URL(url);
      return urlObj.hostname.replace(/^www\./, '');
    } catch {
      return null;
    }
  };

  if (error) {
    return <div className="text-red-500">{error}</div>;
  }

  return (
    <div>
      {isLoading && <div>Loading...</div>}

      <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-4 gap-4">
        {articles.map((article) => (
          <div
            key={article.id}
            onClick={() => handleArticleClick(article)}
            className="relative h-[150px] md:h-auto md:aspect-[21/9] cursor-pointer group overflow-hidden rounded-lg border"
          >
            <div className="absolute inset-0 bg-gray-200 dark:bg-gray-800" />

            <div className="absolute inset-0 bg-black bg-opacity-40 p-4 flex flex-col">
              <div className="flex-1 min-h-0">
                <h3 className="text-white font-bold text-lg line-clamp-2 mb-auto">{article.title || 'Untitled'}</h3>
              </div>
              <div className="flex items-start justify-between mt-2 text-white text-sm">
                <div className="flex flex-col min-w-0">
                  <span className="whitespace-nowrap">{formatDate(article.date_published || article.date_added)}</span>
                  {article.url && (
                    <span className="opacity-75 truncate">{getSourceDomain(article.url)}</span>
                  )}
                </div>
                <span className="bg-black bg-opacity-50 px-2 py-1 rounded ml-2 flex-shrink-0">
                  {article.content_type}
                </span>
              </div>
            </div>
          </div>
        ))}
      </div>

      {articles.length === 0 && !isLoading && (
        <div className="text-center py-8">No articles found</div>
      )}
    </div>
  );
});

ArticleList.displayName = 'ArticleList';

export default ArticleList;
