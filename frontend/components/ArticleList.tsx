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
  date_added: string;
  date_published?: string;
  audio_file: string;
  content_type: string;
  url?: string;
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
        headers: {
          'Content-Type': 'application/json',
        }
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      console.log('Fetched articles:', data); // Log all fetched articles
      // Sort articles by date (most recent first)
      const sortedArticles = data.sort((a: Article, b: Article) => {
        const dateA = new Date(a.date_published || a.date_added);
        const dateB = new Date(b.date_published || b.date_added);
        return dateB.getTime() - dateA.getTime();
      });
      setArticles(sortedArticles);
    } catch (error: any) {
      console.error('Error fetching articles:', error.message);
      setError(`Failed to load articles: ${error.message}`);
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
    console.log('Article clicked:', article);

    try {
      const settings = getSettings();
      let endpoint;

      if (article.content_type === 'article') {
        endpoint = `${settings.serverUrl}/v1/article/${article.id}`;
      } else if (article.content_type === 'podcast') {
        endpoint = `${settings.serverUrl}/v1/podcast/${article.id}`;
      } else if (article.content_type === 'text') {
        endpoint = `${settings.serverUrl}/v1/text/${article.id}`;
      } else {
        console.warn(`Unknown type for article with ID ${article.id}:`, article.content_type || 'undefined');
        throw new Error(`Unknown article type: ${article.content_type || 'undefined'}`);
      }

      const response = await fetch(endpoint, {
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
        }
      });

      if (!response.ok) {
        throw new Error(`Failed to fetch data for type ${article.content_type}`);
      }

      const articleData = await response.json();
      articleData.type = article.content_type; // Ensure type is added to the fetched data
      onSelectArticle(articleData);
    } catch (error: any) {
      console.error('Error fetching article data:', error.message);
      setError(`Failed to load data for type ${article.content_type || 'unknown'}: ${error.message}`);
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
            className="relative h-[150px] md:h-auto md:aspect-video cursor-pointer group overflow-hidden rounded-lg border"
          >
            <div className="absolute inset-0 bg-gray-200 dark:bg-gray-800" />

            <div className="absolute inset-0 bg-black bg-opacity-40 p-4 flex flex-col">
              <div className="flex-1 min-h-0">
                <h3 className="text-white font-bold text-lg line-clamp-3">{article.title || 'Untitled'}</h3>
              </div>
              <div className="flex justify-between items-end mt-2">
                <span className="text-white text-sm">
                  {formatDate(article.date_published || article.date_added)}
                  {article.url && (
                    <span className="ml-2 opacity-75">| {getSourceDomain(article.url)}</span>
                  )}
                </span>
                <span className="text-white text-sm bg-black bg-opacity-50 px-2 py-1 rounded">
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
