'use client';

import { useState, useEffect } from 'react';
import AudioPlayer from './AudioPlayer';
import { getSettings } from '@/lib/settings';
import { Button } from '@/components/ui/button';
import { ChevronDown, ChevronUp } from 'lucide-react';
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";

interface Article {
  id: string;
  title: string;
  date: string;
  audio_file: string;
  content?: string;
  tldr?: string;
  type?: string;
}

interface BottomBarProps {
  articleId: string;
  type: string;
}

export default function BottomBar({ articleId, type }: BottomBarProps) {
  const [article, setArticle] = useState<Article | null>(null);
  const [isExpanded, setIsExpanded] = useState(false);
  const [showTldr, setShowTldr] = useState(false);

  const toggleExpanded = () => {
    setIsExpanded((prev) => !prev);
  };

  useEffect(() => {
    async function fetchArticle() {
      if (!articleId || !type) return;

      try {
        const settings = getSettings();
        let endpoint;
        if (type === 'article') {
          endpoint = `${settings.serverUrl}/v1/article/${articleId}`;
        } else if (type === 'podcast') {
          endpoint = `${settings.serverUrl}/v1/podcast/${articleId}`;
        } else if (type === 'text') {
          endpoint = `${settings.serverUrl}/v1/text/${articleId}`;
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
        console.log('Article type:', type);
        console.log('Has TLDR:', !!data.tldr);
        setArticle({ ...data, type });
      } catch (error) {
        console.error('Error fetching article:', error);
      }
    }

    fetchArticle();
  }, [articleId, type]);

  if (!article) return null;

  const shouldShowToggle = (type === 'article' || type === 'text') && article.tldr;
  const content = showTldr && article.tldr ? article.tldr : article.content;

  // Construct the full audio URL
  const audioUrl = article.audio_file.startsWith('http') 
    ? article.audio_file 
    : `${getSettings().serverUrl}/${article.audio_file}`;

  console.log('Should show toggle:', shouldShowToggle);
  console.log('Audio URL:', audioUrl);

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

            {/* Center - Controls */}
            <div className="flex items-center gap-4">
              {/* Audio Player */}
              {article.audio_file && (
                <AudioPlayer
                  audioUrl={audioUrl}
                />
              )}
              
              {/* TL;DR Toggle */}
              {shouldShowToggle && (
                <div className="flex items-center space-x-2 bg-muted p-2 rounded-lg">
                  <Label htmlFor="tldr-mode" className="text-sm">
                    TL;DR
                  </Label>
                  <Switch
                    id="tldr-mode"
                    checked={showTldr}
                    onCheckedChange={setShowTldr}
                  />
                </div>
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
              {content}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
