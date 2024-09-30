'use client';

import { useState, useEffect } from 'react';
import AudioPlayer from './AudioPlayer';
import MarkdownRenderer from './MarkdownRenderer';
import { Button } from './ui/button';


interface Article {
  id: string;
  title: string;
  date: string;
  audio_file: string;
}

interface BottomBarProps {
  currentArticle: Article | null;
}

export default function BottomBar({ currentArticle }: BottomBarProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const [articleText, setArticleText] = useState('');

  useEffect(() => {
    if (currentArticle) {
      fetchArticleText(currentArticle.id);
    }
  }, [currentArticle]);

  const fetchArticleText = async (articleId: string) => {
    try {
      const response = await fetch(`http://localhost:7777/v1/article/${articleId}`);
      if (!response.ok) {
        throw new Error('Failed to fetch article text');
      }
      const data = await response.json();
      setArticleText(data.content);
    } catch (error) {
      console.error('Error fetching article text:', error);
    }
  };

  if (!currentArticle) return null;

  return (
    <div className={`fixed bottom-0 left-0 right-0 bg-background shadow-md transition-all duration-300 ${isExpanded ? 'h-3/4' : 'h-20'}`}>
      <div className="container mx-auto p-4">
        <div className="flex justify-between items-center">
          <h3 className="text-lg font-semibold">{currentArticle.title}</h3>
          <Button 
            onClick={() => setIsExpanded(!isExpanded)}
            // className="bg-primary hover:bg-primary/90 text-primary-foreground font-bold py-2 px-4 rounded"
          >
            {isExpanded ? 'Collapse' : 'Expand'}
          </Button>
        </div>
        <AudioPlayer audioUrl={`http://localhost:7777${currentArticle.audio_file}`} />
        {isExpanded && (
          <div className="mt-4 overflow-y-auto h-[calc(100%-8rem)]">
            <MarkdownRenderer content={articleText} />
          </div>
        )}
      </div>
    </div>
  );
}