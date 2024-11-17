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

interface FeedEntry {
  title: string | null;
  link: string;
  published: string;
  category: string;
  source: string;
}

export default function TodayFeedList() {
  const { toast } = useToast();
  const { serverUrl } = getSettings();
  const today = new Date().toISOString().split('T')[0];
  const [feedEntries, setFeedEntries] = useState<FeedEntry[]>([]);
  const [selectedEntry, setSelectedEntry] = useState<FeedEntry | null>(null);
  const [modalOpen, setModalOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const { handleAddUrl } = useAddHandlers();

  // Custom handler for URL actions
  const handleUrlAction = async (link: string, endpoint: string) => {
    try {
      await handleAddUrl(link, endpoint, () => {});

      // Show toast for success
      toast({
        title: "Success",
        description: "Article added successfully",
        variant: "default",
      });

      // Close the modal after successful action
      setModalOpen(false);
    } catch (error) {
      console.error('Error handling URL action:', error);
      toast({
        title: "Error",
        description: "Failed to process the request",
        variant: "destructive",
      });
    }
  };

  useEffect(() => {
    async function fetchFeedEntries() {
      setIsLoading(true);
      try {
        const response = await fetch(`${serverUrl}/v1/feeds/get_todays_articles`);
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();

        if (data && Array.isArray(data.articles)) {
          setFeedEntries(data.articles);
        } else {
          throw new Error("Invalid API response format");
        }
      } catch (error) {
        console.error("Failed to fetch feed entries:", error);
        toast({
          title: "Error fetching articles",
          description: error instanceof Error ? error.message : "An unexpected error occurred",
          variant: "destructive",
        });
        setFeedEntries([]);
      } finally {
        setIsLoading(false);
      }
    }
    fetchFeedEntries();
  }, [serverUrl, toast]);

  // Group feed entries by category
  const groupedFeedEntries = feedEntries.reduce((groups, entry) => {
    const category = entry.category || "Uncategorized";
    if (!groups[category]) {
      groups[category] = [];
    }
    groups[category].push(entry);
    return groups;
  }, {} as Record<string, FeedEntry[]>);

  return (
    <div className="space-y-4 pt-8 pl-2">
      <h2 className="text-xl font-bold">Today's News</h2>
      {Object.keys(groupedFeedEntries).length === 0 ? (
        <div className="text-gray-500">
          {isLoading ? "Fetching today's entries..." : "No entries for today"}
        </div>
      ) : (
        Object.entries(groupedFeedEntries).map(([category, entries]) => (
          <div key={category} className="space-y-2">
            <h3 className="text-lg font-semibold">{category}</h3>
            <ul className="space-y-2">
              {entries
                .filter(entry => {
                  const entryDate = new Date(entry.published)
                    .toISOString()
                    .split('T')[0];
                  return entryDate === today;
                })
                .map((entry, index) => (
                  <li key={index} className="flex justify-between items-center border-b pb-2">
                    <div>
                      <h4 className="text-lg">{entry.title || "Untitled"}</h4>
                      <p className="text-sm text-gray-500">
                        {entry.source || "Unknown Source"} - {
                          new Date(entry.published).toLocaleTimeString(undefined, {
                            hour: '2-digit',
                            minute: '2-digit'
                          })
                        }
                      </p>
                    </div>
                    <Button
                      variant="outline"
                      onClick={() => {
                        setSelectedEntry(entry);
                        setModalOpen(true);
                      }}
                    >
                      Add to Queue
                    </Button>
                  </li>
                ))}
            </ul>
          </div>
        ))
      )}

      <Dialog open={modalOpen} onOpenChange={setModalOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Add "{selectedEntry?.title}" to Queue</DialogTitle>
          </DialogHeader>
          <DialogFooter className="flex justify-around">
            <Button onClick={() => selectedEntry?.link && handleUrlAction(selectedEntry.link, 'url/full')}>
              Full Text
            </Button>
            <Button onClick={() => selectedEntry?.link && handleUrlAction(selectedEntry.link, 'url/summary')}>
              TL;DR
            </Button>
            <Button onClick={() => selectedEntry?.link && handleUrlAction(selectedEntry.link, 'url/podcast')}>
              Podcast
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
