'use client';
import { useState } from 'react';
import Image from 'next/image';
import ArticleList from '@/components/ArticleList';
import BottomBar from '@/components/BottomBar';
import { ModeToggle } from '@/components/ModeToggle';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import SourceManager from '@/components/SourceManager';
import ArticleAdder from '@/components/ArticleAdder';

interface Article {
  id: string;
  title: string;
  date: string;
  audio_file: string;
}

export default function Home() {
  const [currentArticle, setCurrentArticle] = useState<Article | null>(null);
  const [sourceManagerOpen, setSourceManagerOpen] = useState(false);
  const [articleAdderOpen, setArticleAdderOpen] = useState(false);

  const handleSelectArticle = (article: Article) => {
    console.log('Setting current article:', article);
    setCurrentArticle(article);
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
            height={16}
            priority
          />
          <Image
            src="/White.svg"
            alt="READ2ME Logo"
            className="hidden dark:block"
            width={60}
            height={16}
            priority
          /> 
        </a>
        </div>
        <div className="flex items-center gap-4">
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

      <div className="space-y-8">
        <ArticleList onSelectArticle={handleSelectArticle} />
      </div>
      <BottomBar currentArticle={currentArticle} />
    </main>
  );
}
