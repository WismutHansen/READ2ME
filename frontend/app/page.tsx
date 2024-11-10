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
  type: string;
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

  const handleSelectArticle = (article: Article) => {
    console.log("Selected article:", article);
    console.log("Selected Article ID:", selectedArticleId);
    console.log("Selected Article Type:", currentArticle?.type);
    setCurrentArticle(article);
    setSelectedArticleId(article.id);
  };

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

  useEffect(() => {
    const { serverUrl } = getSettings();
    async function fetchFeedEntries() {
      try {
        const response = await fetch(`${serverUrl}/v1/feeds/get_todays_articles`);
        const data = await response.json();

        // Ensure data is an array before setting it
        if (Array.isArray(data)) {
          setFeedEntries(data);
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

  return (
    <main className="container mx-auto px-4 py-8 mb-24">
      <div className="flex justify-between items-center mb-8">
        <div className="h-8 relative">
          <a
            href="https://github.com/WismutHansen/READ2ME"
            target="_blank"
            rel="noopener noreferrer"
            className="h-8 relative"
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
        </div>
        <div className="flex items-center gap-4">
          <TaskQueueStatus refreshArticles={refreshArticles} />
          <Button
            variant="outline"
            onClick={() => setSourceManagerOpen(true)}
          >
            Manage Sources
          </Button>
          <Button
            variant="outline"
            onClick={() => setArticleAdderOpen(true)}
          >
            Add Content
          </Button>
          <SettingsManager variant="outline" />
          <ModeToggle />
        </div>
      </div>

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

      {/* Pass handleSelectArticle to ArticleList */}
      <ArticleList ref={articleListRef} onSelectArticle={handleSelectArticle} />

      {/* Display Today's Feed Entries */}
      <TodayFeedList feedEntries={feedEntries} />

      {/* Conditionally render the BottomBar based on the selectedArticleId */}
      {selectedArticleId && currentArticle && (
        <BottomBar articleId={selectedArticleId} type={currentArticle.type} key={selectedArticleId} />
      )}
    </main>
  );
}
