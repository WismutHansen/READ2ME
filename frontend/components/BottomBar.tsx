'use client';

import { useState, useEffect } from 'react';
import AudioPlayer from './AudioPlayer';
import MarkdownRenderer from './MarkdownRenderer';
import { Button } from './ui/button';
import MarkdownPreview from '@uiw/react-markdown-preview';

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
    <div className={`fixed bottom-0 left-0 right-0 transition-all duration-300 ${isExpanded ? 'h-5/6' : 'h-20'} bg-white dark:bg-black text-black dark:text-white`}>
      <div className="container mx-auto p-4 h-full flex flex-col">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-semibold flex-1 break-words text-left mr-4">
            {currentArticle.title}
          </h3>
          <div className="absolute left-1/2 transform -translate-x-1/2">
            <AudioPlayer audioUrl={`http://localhost:7777${currentArticle.audio_file}`} />
          </div>
          <Button
            onClick={() => setIsExpanded(!isExpanded)}
            className="ml-auto"
          >
            {isExpanded ? 'Collapse' : 'Expand'}
          </Button>
        </div>
        {isExpanded && (
          <div className="mt-4 overflow-y-auto flex-1">
            <MarkdownPreview source={articleText} />
          </div>
        )}
      </div>
    </div>
  );
}
