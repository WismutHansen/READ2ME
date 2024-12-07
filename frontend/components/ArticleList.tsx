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
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

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
  const [activeType, setActiveType] = useState<string>("all");

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

  // Function to filter articles based on search query and type
  const getFilteredArticles = () => {
    let filtered = articles;

    // Filter by type first
    if (activeType !== "all") {
      filtered = filtered.filter(article => article.content_type === activeType);
    }

    // Then apply search filter
    if (searchQuery) {
      const lowerQuery = searchQuery.toLowerCase();
      filtered = filtered.filter(article =>
        (article.title && article.title.toLowerCase().includes(lowerQuery)) ||
        (article.source && article.source.toLowerCase().includes(lowerQuery))
      );
    }

    return filtered;
  };

  if (error) {
    return <div className="text-red-500">{error}</div>;
  }

  return (
    <div className="space-y-2 mt-2">
      <div className="flex flex-col md:flex-row items-center justify-between mb-2">
        <Tabs defaultValue="all" value={activeType} onValueChange={setActiveType} className="w-full">
          <div className="flex flex-col md:flex-row items-center justify-between mb-2">
            <TabsList className="grid w-full grid-cols-3 md:flex md:flex-row md:grow gap-1 h-auto">
              <TabsTrigger
                value="all"
                className="capitalize flex-shrink-0 data-[state=active]:bg-slate-900 data-[state=active]:text-slate-100"
              >
                All
              </TabsTrigger>
              <TabsTrigger
                value="article"
                className="capitalize flex-shrink-0 data-[state=active]:bg-slate-900 data-[state=active]:text-slate-100"
              >
                Article
              </TabsTrigger>
              <TabsTrigger
                value="podcast"
                className="capitalize flex-shrink-0 data-[state=active]:bg-slate-900 data-[state=active]:text-slate-100"
              >
                Podcast
              </TabsTrigger>
              <TabsTrigger
                value="text"
                className="capitalize flex-shrink-0 data-[state=active]:bg-slate-900 data-[state=active]:text-slate-100"
              >
                Text
              </TabsTrigger>
            </TabsList>
            <div className="w-full md:w-auto mt-2 md:mt-0">
              <input
                type="text"
                placeholder="Search in library..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full md:ml-1.5 gap-2 px-6 py-2  rounded-lg focus:outline-none focus:border-slate-200"
              />
            </div>
          </div>

          <TabsContent value={activeType} className="mt-0">
            {isLoading ? (
              <div className="text-gray-500">Loading...</div>
            ) : (
              <div className="flex flex-col space-y-2">
                {getFilteredArticles().map((article) => (
                  <ContextMenu key={article.id}>
                    <ContextMenuTrigger>
                      <div
                        onClick={() => handleArticleClick(article)}
                        className="flex items-center p-2 bg-slate-200 dark:bg-slate-800 bg-card rounded-lg shadow-sm"
                      >
                        <div className="flex-1 min-w-0 mr-4">
                          <h3 className="text-sm font-medium truncate">
                            {article.title || "Untitled"}
                          </h3>
                          <p className="text-xs text-muted-foreground">
                            {getSourceDomain(article.url)} • {formatDate(article.date_published || article.date_added)}
                          </p>
                        </div>
                        <div className="flex flex-col md:flex-row md:max-w-52 gap-2">
                          <span className="text-xs px-2 py-1 bg-slate-300 dark:bg-slate-700 rounded">
                            {article.content_type}
                          </span>
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
          </TabsContent>
        </Tabs>

        {getFilteredArticles().length === 0 && !isLoading && (
          <div className="text-center py-8">No articles found</div>
        )}
      </div>
    </div>
  );
});

ArticleList.displayName = 'ArticleList';

export default ArticleList;
