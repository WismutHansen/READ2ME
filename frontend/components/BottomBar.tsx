'use client';

import { useState, useEffect } from 'react';
import AudioPlayer from './AudioPlayer';
import { getSettings } from '@/lib/settings';
import { Button } from '@/components/ui/button';
import { ChevronDown, ChevronUp } from 'lucide-react';

interface Article {
  id: string;
  title: string;
  date: string;
  audio_file: string;
  content?: string;
}

interface BottomBarProps {
  articleId: string;
  type: string; // Add type to props
}

export default function BottomBar({ articleId, type }: BottomBarProps) {
  const [article, setArticle] = useState<Article | null>(null);
  const [isExpanded, setIsExpanded] = useState(false);

  const toggleExpanded = () => {
    setIsExpanded((prev) => !prev);
  };

  useEffect(() => {
    async function fetchArticle() {
      if (!articleId || !type) return;

      try {
        // Determine the endpoint based on the type
        let endpoint;
        if (type === 'article') {
          endpoint = `${process.env.NEXT_PUBLIC_API_URL}/v1/article/${articleId}`;
        } else if (type === 'podcast') {
          endpoint = `${process.env.NEXT_PUBLIC_API_URL}/v1/podcast/${articleId}`;
        } else if (type === 'text') {
          endpoint = `${process.env.NEXT_PUBLIC_API_URL}/v1/texts/${articleId}`;
        } else {
          console.warn(`Unknown type: ${type}`);
          throw new Error(`Unknown type: ${type}`);
        }

        const response = await fetch(endpoint);
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();
        console.log('Fetched article data:', data);
        setArticle(data);
      } catch (error) {
        console.error('Error fetching article:', error);
      }
    }

    fetchArticle();
  }, [articleId, type]);

  if (!article) return null;

  return (
    <div className={`fixed bottom-0 left-0 right-0 bg-background border-t z-50 ${isExpanded ? 'h-[80vh] overflow-y-auto' : ''}`}>
      <div className="container mx-auto px-4">
        {/* Header section with controls */}
        <div className="sticky top-0 bg-background py-4">
          <div className="flex items-center justify-between">
            {/* Left side - Title and Date */}
            <div className="flex-1 min-w-0 mr-4">
              <h3 className="text-lg font-semibold truncate">{article.title}</h3>
              {article.date && (
                <p className="text-sm text-muted-foreground">
                  {new Date(article.date).toLocaleDateString()}
                </p>
              )}
            </div>

            {/* Center - Audio Player */}
            <div className="flex-shrink-0">
              {article.audio_file && (
                <>
                  {console.log('Audio file path:', article.audio_file)}
                  <AudioPlayer
                    audioUrl={`${process.env.NEXT_PUBLIC_API_URL}/${article.audio_file}`}
                  />
                </>
              )}
            </div>

            {/* Right side - Expand/Collapse Button */}
            <div className="flex-shrink-0 ml-4">
              <Button
                variant="ghost"
                size="icon"
                onClick={toggleExpanded}
                className="hover:bg-accent hover:text-accent-foreground"
              >
                {isExpanded ? (
                  <ChevronDown className="h-4 w-4" />
                ) : (
                  <ChevronUp className="h-4 w-4" />
                )}
              </Button>
            </div>
          </div>
        </div>

        {/* Expanded Content */}
        {isExpanded && (
          <div className="py-4">
            <div className="prose dark:prose-invert max-w-none">
              {article.content}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
