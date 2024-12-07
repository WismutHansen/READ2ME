'use client';

import { forwardRef, useEffect, useState, useImperativeHandle } from "react";
import { getSettings } from "@/lib/settings";
import {
  ContextMenu,
  ContextMenuContent,
  ContextMenuItem,
  ContextMenuTrigger,
} from "@/components/ui/context-menu"
import { toast } from "sonner"

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
  const [searchQuery, setSearchQuery] = useState<string>('');

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

  const handleDelete = async (article: Article, e: Event) => {
    e.preventDefault();
    e.stopPropagation();

    try {
      const settings = getSettings();
      const response = await fetch(`${settings.serverUrl}/v1/audio`, {
        method: 'DELETE',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          items: [{
            content_type: article.content_type,
            id: article.id
          }]
        }),
        credentials: 'include',
      });

      if (!response.ok) {
        throw new Error(`Failed to delete article: ${response.statusText}`);
      }

      const result = await response.json();

      if (result.errors && result.errors.length > 0) {
        throw new Error(result.errors[0].error);
      }

      toast.success("Audio file deleted successfully");
      await fetchArticles(); // Refresh the list
    } catch (err) {
      console.error('Error deleting article:', err);
      toast.error(err instanceof Error ? err.message : 'Failed to delete audio file');
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

  // Function to filter articles based on search query
  const getFilteredArticles = () => {
    if (!searchQuery) return articles;
    const lowerQuery = searchQuery.toLowerCase();
    return articles.filter(article =>
      (article.title && article.title.toLowerCase().includes(lowerQuery)) ||
      (article.source && article.source.toLowerCase().includes(lowerQuery))
    );
  };

  if (error) {
    return <div className="text-red-500">{error}</div>;
  }

  return (
    <div className="space-y-4">
      <div className="flex justify-end mb-4">
        <div className="md:w-56">
          <input
            type="text"
            placeholder="Search articles..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="px-6 py-2 border rounded-lg focus:outline-none focus:border-slate-200"
          />
        </div>
      </div>

      {isLoading ? (
        <div className="text-gray-500">Loading...</div>
      ) : (
        <div className="grid grid-cols-2 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {getFilteredArticles().map((article) => (
            <ContextMenu key={article.id}>
              <ContextMenuTrigger>
                <div
                  onClick={() => handleArticleClick(article)}
                  className="relative h-[150px] md:min-h-32 md:gap-2 md:h-auto md:aspect-[21/9] cursor-pointer group overflow-hidden rounded-lg border"
                >
                  <div className="absolute inset-0 bg-gray-200 dark:bg-gray-800" />

                  <div className="absolute inset-0 bg-black bg-opacity-40 p-4 flex flex-col">
                    <div className="flex-1 min-h-0">
                      <h3 className="text-white font-bold text-lg line-clamp-2 mb-auto text-pretty">{article.title || 'Untitled'}</h3>
                    </div>
                    <div className="flex items-start justify-between mt-2 text-white text-sm">
                      <div className="flex cols-1">
                        <div className="min-w-0">
                          <div className="whitespace-wrap">{formatDate(article.date_published || article.date_added)}</div>
                          {article.url && (
                            <div className="opacity-75 truncate">{getSourceDomain(article.url)}</div>
                          )}
                        </div>
                      </div>
                      <div className="bg-black bg-opacity-50 px-2 py-1 rounded flex-shrink-0">
                        {article.content_type}
                      </div>
                    </div>
                  </div>
                </div>
              </ContextMenuTrigger>
              <ContextMenuContent>
                <ContextMenuItem
                  className="text-destructive focus:text-destructive"
                  onSelect={(e) => handleDelete(article, e)}
                >
                  Delete Audio
                </ContextMenuItem>
              </ContextMenuContent>
            </ContextMenu>
          ))}
        </div>
      )}

      {getFilteredArticles().length === 0 && !isLoading && (
        <div className="text-center py-8">No articles found</div>
      )}
    </div>
  );
});

ArticleList.displayName = 'ArticleList';

export default ArticleList;
