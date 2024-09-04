'use client';

import { useState } from 'react';
import ArticleList from '@/components/ArticleList';
import BottomBar from '@/components/BottomBar';
import { ModeToggle } from '@/components/ModeToggle';
import { Switch } from './ui/switch';
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

  const handleSelectArticle = (article: Article) => {
    console.log('Setting current article:', article);
    setCurrentArticle(article);
  };

  return (
    <main className="container mx-auto px-4 py-8 mb-24">
      <div className="flex justify-between items-center mb-8">
        <h1 className="text-3xl font-bold">READ2ME</h1>
        <ModeToggle />
      </div>
      <div className="space-y-8">
        <SourceManager />
        <ArticleAdder />
        <ArticleList onSelectArticle={handleSelectArticle} />
      </div>
      <BottomBar currentArticle={currentArticle} />
    </main>
  );
}
