import { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { useToast } from "@/hooks/use-toast";
import { getSettings } from '@/lib/settings';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import { useAddHandlers } from '@/components/addHandlers';
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Checkbox } from "@/components/ui/checkbox";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

interface FeedEntry {
  title: string | null;
  link: string;
  published: string;
  category: string;
  source: string;
}

interface TodayFeedListProps {
  onSelectArticle?: (article: any) => void;
}

export default function TodayFeedList({ onSelectArticle }: TodayFeedListProps) {
  const { toast } = useToast();
  const { serverUrl } = getSettings();
  const today = new Date().toISOString().split('T')[0];
  const [feedEntries, setFeedEntries] = useState<FeedEntry[]>([]);
  const [selectedEntry, setSelectedEntry] = useState<FeedEntry | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [activeCategory, setActiveCategory] = useState("all");
  const [selectedArticles, setSelectedArticles] = useState<Set<string>>(new Set());
  const { handleAddUrl } = useAddHandlers();

  // Custom handler for URL actions
  const handleUrlAction = async (link: string, mode?: string) => {
    try {
      // Map the mode to the correct endpoint
      let endpoint;
      switch (mode) {
        case 'summary':
          endpoint = 'url/summary';
          break;
        case 'podcast':
          endpoint = 'url/podcast';
          break;
        default:
          endpoint = 'url/full';
      }

      await handleAddUrl(link, endpoint, fetchFeedEntries);

      toast({
        title: "Success",
        description: "Article added to processing queue",
      });
    } catch (error) {
      console.error('Error:', error);
      toast({
        title: "Error",
        description: "Failed to add article",
        variant: "destructive",
      });
    }
  };

  // Process all selected articles
  const processSelectedArticles = async (mode: 'full' | 'summary' | 'podcast') => {
    const endpoint = mode === 'full' ? 'articles/add' : `articles/${mode}`;
    let successCount = 0;
    let failCount = 0;

    for (const link of selectedArticles) {
      try {
        await handleAddUrl(link, endpoint, () => {});
        successCount++;
      } catch (error) {
        console.error('Error processing article:', error);
        failCount++;
      }
    }

    // Show result toast
    if (successCount > 0) {
      toast({
        title: "Success",
        description: `Added ${successCount} articles to task list${failCount > 0 ? ` (${failCount} failed)` : ''}`,
        variant: "default",
      });

      // Refresh the feed entries after successful additions
      fetchFeedEntries();
    }

    // Clear selections after processing
    setSelectedArticles(new Set());
  };

  // Fetch feed entries
  const fetchFeedEntries = async () => {
    setIsLoading(true);
    try {
      const response = await fetch(`${serverUrl}/v1/feeds/get_todays_articles`, {
        credentials: 'include'
      });
      
      if (!response.ok) {
        throw new Error('Failed to fetch feed entries');
      }
      
      const data = await response.json();
      setFeedEntries(data.articles || []);
    } catch (error) {
      console.error('Error fetching feed entries:', error);
      toast({
        title: "Error",
        description: "Failed to fetch feed entries",
        variant: "destructive",
      });
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchFeedEntries();
    // Refresh every 5 minutes
    const interval = setInterval(fetchFeedEntries, 5 * 60 * 1000);
    return () => clearInterval(interval);
  }, []);

  // Group feed entries by category
  const groupedFeedEntries = feedEntries.reduce((groups, entry) => {
    const category = entry.category || "Uncategorized";
    if (!groups[category]) {
      groups[category] = [];
    }
    groups[category].push(entry);
    return groups;
  }, {} as Record<string, FeedEntry[]>);

  // Get all unique categories
  const categories = ["all", ...Object.keys(groupedFeedEntries)].filter(
    (category) => category !== "Uncategorized"
  );

  // Filter entries based on active category
  const getFilteredEntries = () => {
    if (activeCategory === "all") {
      return feedEntries;
    }
    return feedEntries.filter(entry => entry.category === activeCategory);
  };

  // Handle checkbox selection
  const toggleArticleSelection = (link: string) => {
    const newSelected = new Set(selectedArticles);
    if (newSelected.has(link)) {
      newSelected.delete(link);
    } else {
      newSelected.add(link);
    }
    setSelectedArticles(newSelected);
  };

  return (
    <div className="space-y-4 pt-8 pl-2">
      <div className="flex justify-between items-center">
        <h2 className="text-xl font-bold">Today's News</h2>
        {selectedArticles.size > 0 && (
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="outline">
                Add {selectedArticles.size} Selected
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-[280px]">
              <DropdownMenuItem
                onClick={() => processSelectedArticles('full')}
                className="flex flex-col items-start py-2"
              >
                <span className="font-semibold">Full Text</span>
                <span className="text-xs text-muted-foreground">Turn complete text into speech</span>
              </DropdownMenuItem>
              <DropdownMenuItem
                onClick={() => processSelectedArticles('summary')}
                className="flex flex-col items-start py-2"
              >
                <span className="font-semibold">TL;DR</span>
                <span className="text-xs text-muted-foreground">Generate a summary and turn it into speech</span>
              </DropdownMenuItem>
              <DropdownMenuItem
                onClick={() => processSelectedArticles('podcast')}
                className="flex flex-col items-start py-2"
              >
                <span className="font-semibold">Podcast</span>
                <span className="text-xs text-muted-foreground">Turn the article into a podcast</span>
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        )}
      </div>
      {Object.keys(groupedFeedEntries).length === 0 ? (
        <div className="text-gray-500">
          {isLoading ? "Fetching today's entries..." : "No entries for today"}
        </div>
      ) : (
        <Tabs defaultValue="all" value={activeCategory} onValueChange={setActiveCategory}>
          <TabsList className="mb-4">
            {categories.map((category) => (
              <TabsTrigger
                key={category}
                value={category}
                className="capitalize"
              >
                {category}
              </TabsTrigger>
            ))}
          </TabsList>

          <TabsContent value={activeCategory} className="mt-0">
            <div className="space-y-4">
              {getFilteredEntries().map((entry, index) => (
                <div
                  key={index}
                  className="flex items-center p-4 bg-card rounded-lg shadow-sm"
                >
                  <Checkbox
                    id={`article-${index}`}
                    checked={selectedArticles.has(entry.link)}
                    onCheckedChange={() => toggleArticleSelection(entry.link)}
                    className="mr-4"
                  />
                  <div className="flex-1 min-w-0 mr-4">
                    <h3 className="text-sm font-medium truncate">
                      {entry.title || "Untitled"}
                    </h3>
                    <p className="text-xs text-muted-foreground">
                      {entry.source} • {new Date(entry.published).toLocaleString()}
                    </p>
                  </div>
                  <div className="flex gap-2">
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <Button variant="outline" size="sm">
                          Add to Tasks
                        </Button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end" className="w-[280px]">
                        <DropdownMenuItem
                          onClick={() => handleUrlAction(entry.link)}
                          className="flex flex-col items-start py-2"
                        >
                          <span className="font-semibold">Full Text</span>
                          <span className="text-xs text-muted-foreground">Turn complete text into speech</span>
                        </DropdownMenuItem>
                        <DropdownMenuItem
                          onClick={() => handleUrlAction(entry.link, 'summary')}
                          className="flex flex-col items-start py-2"
                        >
                          <span className="font-semibold">TL;DR</span>
                          <span className="text-xs text-muted-foreground">Generate a summary and turn it into speech</span>
                        </DropdownMenuItem>
                        <DropdownMenuItem
                          onClick={() => handleUrlAction(entry.link, 'podcast')}
                          className="flex flex-col items-start py-2"
                        >
                          <span className="font-semibold">Podcast</span>
                          <span className="text-xs text-muted-foreground">Turn the article into a podcast</span>
                        </DropdownMenuItem>
                      </DropdownMenuContent>
                    </DropdownMenu>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => window.open(entry.link, '_blank')}
                    >
                      View Source
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          </TabsContent>
        </Tabs>
      )}
    </div>
  );
}
