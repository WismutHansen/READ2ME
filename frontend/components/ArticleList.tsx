'use client';

import { forwardRef, useEffect, useState, useImperativeHandle } from "react";
import { getSettings } from "@/lib/settings";

interface Article {
  id: string;
  title: string;
  date_added: string;
  date_published?: string;
  audio_file: string;
  type: string;
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
      setArticles(data);
    } catch (error) {
      console.error('Error fetching articles:', error);
      setError('Failed to load articles. Please try again.');
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

  const handleArticleClick = (article: Article) => {
    console.log('Article clicked:', article);
    onSelectArticle(article);
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
            className="relative aspect-video cursor-pointer group overflow-hidden rounded-lg border"
          >
            {/* Default background color */}
            <div className="absolute inset-0 bg-gray-200 dark:bg-gray-800" />
            
            {/* Content overlay */}
            <div className="absolute inset-0 bg-black bg-opacity-40 p-4 flex flex-col justify-between">
              <div>
                <h3 className="text-white font-bold text-lg">{article.title}</h3>
              </div>
              <div className="flex justify-between items-end">
                <span className="text-white text-sm">
                  {article.date_published || article.date_added}
                </span>
                <span className="text-white text-sm bg-black bg-opacity-50 px-2 py-1 rounded">
                  {article.type}
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
