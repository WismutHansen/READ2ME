'use client';

import { useState } from 'react';
import ArticleList from '@/components/ArticleList';
import BottomBar from '@/components/BottomBar';
import { ModeToggle } from '@/components/ModeToggle';
import { Switch } from './ui/switch';

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
        <h1 className="text-3xl font-bold">READ2ME Webapp</h1>
        <ModeToggle />
      </div>
      <ArticleList onSelectArticle={handleSelectArticle} />
      <div className="mt-8 p-4 bg-gray-100 rounded">
        <h2 className="text-xl font-semibold mb-2">Debug Info:</h2>
        <p>Current Article: {currentArticle ? JSON.stringify(currentArticle) : 'None'}</p>
      </div>
      <BottomBar currentArticle={currentArticle} />
    </main>
  );
}