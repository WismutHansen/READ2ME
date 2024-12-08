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
  const [searchQuery, setSearchQuery] = useState<string>(''); // Added state for search query
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
    try {
      const links = Array.from(selectedArticles);
      const { serverUrl, ttsEngine } = getSettings();
      const response = await fetch(`${serverUrl}/v1/articles/batch`, {
        method: 'POST',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          urls: links,
          mode: mode,
          tts_engine: ttsEngine,
        })
      });

      if (!response.ok) {
        throw new Error('Failed to process articles');
      }

      toast({
        title: "Success",
        description: `Added ${links.length} articles to task list`,
        variant: "default",
      });

      // Refresh the feed entries after successful additions
      fetchFeedEntries();

      // Clear selections after processing
      setSelectedArticles(new Set());
    } catch (error) {
      console.error('Error processing articles:', error);
      toast({
        title: "Error",
        description: "Failed to process articles",
        variant: "destructive",
      });
    }
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

  // Function to filter feed entries based on search query
  const filterFeedEntries = (entries: FeedEntry[], query: string) => {
    if (!query) return entries;
    const lowerQuery = query.toLowerCase();
    return entries.filter(entry =>
      (entry.title && entry.title.toLowerCase().includes(lowerQuery)) ||
      (entry.source && entry.source.toLowerCase().includes(lowerQuery))
    );
  };

  // Filter entries based on active category and search query
  const getFilteredEntries = () => {
    let filtered = feedEntries;
    if (activeCategory !== "all") {
      filtered = filtered.filter(entry => entry.category === activeCategory);
    }
    return filterFeedEntries(filtered, searchQuery);
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
    <div className="space-y-2">
      <div className="flex flex-col md:flex-row mb-2">
      </div>
      {Object.keys(groupedFeedEntries).length === 0 ? (
        <div className="text-gray-500">
          {isLoading ? "Fetching today's entries..." : "No entries for today"}
        </div>
      ) : (
        <Tabs defaultValue="all" value={activeCategory} onValueChange={setActiveCategory}>
          <div className="flex flex-col md:flex-row items-center justify-center mb-2">
            <div>
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <div className="fixed top-4 left-8 sm:left-24 md:left-48 2xl:left-80">
                    {selectedArticles.size > 0 && (
                      <Button variant="secondary">
                        Add {selectedArticles.size} Selected
                      </Button>
                    )}</div>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="start" className="w-[280px]">
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
            </div>
            <TabsList className="grid w-full grid-cols-3 md:flex md:flex-row md:grow gap-1 h-auto">
              {categories.map((category) => (
                <TabsTrigger
                  key={category}
                  value={category}
                  className="capitalize flex-shrink-0 data-[state=active]:bg-slate-900 data-[state=active]:text-slate-100"
                >
                  {category}
                </TabsTrigger>
              ))}
            </TabsList>
            <div className="w-full md:ml-1.5 md:w-auto mt-2 md:mt-0">
              <input
                type="text"
                placeholder="Search Feeds..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full px-6 py-2 rounded-lg focus:outline-none focus:border-slate-200"
              />
            </div>
          </div>

          <TabsContent value={activeCategory} className="mt-2">
            <div className="space-y-2">
              {getFilteredEntries().map((entry, index) => (
                <div
                  key={index}
                  className="flex items-center p-2 bg-slate-200 dark:bg-slate-800 bg-card rounded-lg shadow-sm"
                >
                  <Checkbox
                    id={`article-${index}`}
                    checked={selectedArticles.has(entry.link)}
                    onCheckedChange={() => toggleArticleSelection(entry.link)}
                    className="mr-4"
                  />
                  <div className="flex-1 min-w-0 mr-4">
                    <h3 className="text-wrap text-sm font-medium">
                      {entry.title || "Untitled"}
                    </h3>
                    <p className="text-xs text-muted-foreground">
                      {entry.source} • {new Date(entry.published).toLocaleString()}
                    </p>
                  </div>
                  <div className="flex flex-col md:flex-row md:max-w-52 gap-0.5">
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <Button className="w-20 text-xs text-xs px-2 py-1 bg-slate-300 dark:bg-slate-700 rounded" variant="outline" size="sm">
                          read2me
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
                      className="w-20 text-xs text-xs px-2 py-1 bg-slate-300 dark:bg-slate-700 rounded"
                      variant="outline"
                      size="sm"
                      onClick={() => window.open(entry.link, '_blank')}
                    >
                      source
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
