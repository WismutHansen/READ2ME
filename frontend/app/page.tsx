"use client";
import { useState, useRef, useEffect } from "react";
import Image from "next/image";
import ArticleList from "@/components/ArticleList";
import BottomBar from "@/components/BottomBar";
import { ModeToggle } from "@/components/ModeToggle";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import SourceManager from "@/components/SourceManager";
import ArticleAdder from "@/components/ArticleAdder";
import SettingsManager from "@/components/SettingsManager";
import { useToast } from "@/hooks/use-toast";
import type { ArticleListRef } from "@/components/ArticleList";
import TaskQueueStatus from "@/components/TaskQueueStatus";
import TodayFeedList from "@/components/TodayFeedList";
import { getSettings } from "@/lib/settings";

interface Article {
  id: string;
  title: string;
  date_added: string;
  date_published?: string;
  audio_file: string;
  content?: string;
  content_type: string;
}

interface FeedEntry {
  title: string;
  link: string;
  published: string;
  category: string;
}

export default function Home() {
  const [currentArticle, setCurrentArticle] = useState<Article | null>(null); // State for the currently selected article
  const [sourceManagerOpen, setSourceManagerOpen] = useState(false);
  const [articleAdderOpen, setArticleAdderOpen] = useState(false);
  const { toast } = useToast();
  const articleListRef = useRef<ArticleListRef>(null);
  const [selectedArticleId, setSelectedArticleId] = useState<string | null>(null); // Stores the ID of the selected article
  const [feedEntries, setFeedEntries] = useState<FeedEntry[]>([]);
  const [articles, setArticles] = useState<Article[]>([]);
  const [hasContent, setHasContent] = useState(true); // Track content state
  const [tabValue, setTabValue] = useState("articles");

  // Function to refresh articles list via ArticleListRef
  const refreshArticles = async () => {
    try {
      await articleListRef.current?.refresh(); // Call the refresh function on the ArticleList ref
      toast({
        title: "Articles refreshed",
      });
    } catch (error) {
      toast({
        variant: "destructive",
        title: "Failed to refresh articles",
      });
    }
  };

  // Update content state when ArticleList updates
  const handleContentStateChange = (hasArticles: boolean) => {
    setHasContent(hasArticles);
  };

  // Fetch articles
  useEffect(() => {
    const fetchArticles = async () => {
      try {
        const { serverUrl } = getSettings();
        const response = await fetch(`${serverUrl}/v1/available-media`, {
          credentials: 'include'
        });

        if (!response.ok) {
          throw new Error('Failed to fetch articles');
        }

        const data = await response.json();
        setArticles(data);
      } catch (error) {
        console.error('Error fetching articles:', error);
      }
    };
    fetchArticles();
  }, []);

  useEffect(() => {
    const { serverUrl } = getSettings();
    async function fetchFeedEntries() {
      try {
        const response = await fetch(`${serverUrl}/v1/feeds/get_todays_articles`, {
          credentials: 'include'
        });

        if (!response.ok) {
          throw new Error('Failed to fetch feed entries');
        }

        const data = await response.json();
        if (data.articles) {
          setFeedEntries(data.articles);
        } else {
          console.error("Unexpected data format:", data);
          setFeedEntries([]);
        }
      } catch (error) {
        console.error("Failed to fetch feed entries:", error);
      }
    }
    fetchFeedEntries();
  }, []);

  const handleSelectArticle = (article: Article) => {
    console.log("Selected article:", article);
    setCurrentArticle(article);
    setSelectedArticleId(article.id);
  };

  return (
    <main className="flex min-h-screen flex-col">
      <div className="container mx-auto px-4 flex-grow">
        <div className="flex justify-between items-center py-4">
          <div className="flex items-center gap-2">
            <a
              href="https://github.com/WismutHansen/READ2ME"
              target="_blank"
              rel="noopener noreferrer"
              className="h-8 relative block"
            >
              <Image
                src="/Black.svg"
                alt="READ2ME Logo"
                className="block dark:hidden"
                width={60}
                height={32}
                priority
              />
              <Image
                src="/White.svg"
                alt="READ2ME Logo"
                className="hidden dark:block"
                width={60}
                height={32}
                priority
              />
            </a>
            <h1 className="text-2xl font-bold">READ2ME</h1>
          </div>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              onClick={() => setArticleAdderOpen(true)}
              className={!hasContent ? 'animate-breathing-outline' : ''}
            >
              Add Content
            </Button>
            <Button
              variant="outline"
              onClick={() => setSourceManagerOpen(true)}
            >
              Manage Sources
            </Button>
            <SettingsManager variant="outline" />
            <ModeToggle />
          </div>
        </div>

        <Tabs value={tabValue} onValueChange={setTabValue} className="w-full">
          <TabsList className="grid w-full grid-cols-2 mb-8 mt-8">
            <TabsTrigger value="articles">Your Articles</TabsTrigger>
            <TabsTrigger value="feeds">Today's Feeds</TabsTrigger>
          </TabsList>

          <TabsContent value="articles" className="mt-0">
            <ArticleList
              ref={articleListRef}
              onSelectArticle={handleSelectArticle}
              onContentStateChange={handleContentStateChange}
            />
          </TabsContent>

          <TabsContent value="feeds" className="mt-0">
            <TodayFeedList
              onSelectArticle={handleSelectArticle}
              feedEntries={feedEntries}
            />
          </TabsContent>
        </Tabs>

        <Dialog open={sourceManagerOpen} onOpenChange={setSourceManagerOpen}>
          <DialogContent className="sm:max-w-[800px]">
            <DialogHeader>
              <DialogTitle>Manage Sources</DialogTitle>
            </DialogHeader>
            <SourceManager />
          </DialogContent>
        </Dialog>

        <Dialog open={articleAdderOpen} onOpenChange={setArticleAdderOpen}>
          <DialogContent className="sm:max-w-[800px]">
            <DialogHeader>
              <DialogTitle>Add Content</DialogTitle>
            </DialogHeader>
            <ArticleAdder />
          </DialogContent>
        </Dialog>

        {selectedArticleId && currentArticle && (
          <BottomBar
            articleId={selectedArticleId}
            type={currentArticle.content_type || 'article'}
            audioFile={currentArticle.audio_file}
            key={selectedArticleId}
          />
        )}
      </div>
    </main>
  );
}
