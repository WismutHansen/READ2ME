"use client";
import { useState, useRef } from "react";
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
import { Cog } from "lucide-react";
import SourceManager from "@/components/SourceManager";
import ArticleAdder from "@/components/ArticleAdder";
import SettingsManager from "@/components/SettingsManager";
import { Loader2, RefreshCw } from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import type { ArticleListRef } from "@/components/ArticleList";

interface Article {
  id: string;
  title: string;
  date_added: string;
  date_published?: string;
  audio_file: string;
  type: string;
  // ... other fields if needed
}

export default function Home() {
  const [currentArticle, setCurrentArticle] = useState<Article | null>(null);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [sourceManagerOpen, setSourceManagerOpen] = useState(false);
  const [articleAdderOpen, setArticleAdderOpen] = useState(false);
  const { toast } = useToast();
  const articleListRef = useRef<ArticleListRef>(null);
  const [selectedArticleId, setSelectedArticleId] = useState<string | null>(null);

  const handleSelectArticle = (article: Article) => {
    console.log('Selected article:', article);
    setCurrentArticle(article);
    setSelectedArticleId(article.id);
  };

  const handleRefresh = async () => {
    setIsRefreshing(true);
    try {
      await articleListRef.current?.refresh();
      toast({
        title: "Articles refreshed",
      });
    } catch (error) {
      toast({
        variant: "destructive",
        title: "Failed to refresh articles",
      });
    } finally {
      setIsRefreshing(false);
    }
  };

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
          <Button
            onClick={handleRefresh}
            variant="outline"
            size="sm"
            disabled={isRefreshing}
          >
            {isRefreshing ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Refreshing
              </>
            ) : (
              <>
                <RefreshCw className="mr-2 h-4 w-4" />
                Refresh
              </>
            )}
          </Button>
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


      <ArticleList ref={articleListRef} onSelectArticle={handleSelectArticle} />

      {console.log('Selected ID:', selectedArticleId)}

      {selectedArticleId && (
        <BottomBar
          articleId={selectedArticleId}
          key={selectedArticleId}
        />
      )}
    </main>
  );
}
