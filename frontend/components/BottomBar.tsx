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
  content_type: string;
}

interface BottomBarProps {
  articleId: string;
  content_type: string;
}

export default function BottomBar({ articleId, content_type }: BottomBarProps) {
  const [article, setArticle] = useState<Article | null>(null);
  const [isExpanded, setIsExpanded] = useState(false);
  const [showTldr, setShowTldr] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const toggleExpanded = () => {
    setIsExpanded((prev) => !prev);
  };

  useEffect(() => {
    async function fetchArticle() {
      if (!articleId || !content_type) return;

      try {
        const settings = getSettings();
        const endpoint = `${settings.serverUrl}/v1/${content_type}/${encodeURIComponent(articleId)}`;
        
        console.log('Fetching from endpoint:', endpoint);

        const response = await fetch(endpoint, {
          credentials: 'include',
          headers: {
            'Accept': 'application/json',
            'Content-Type': 'application/json'
          }
        });

        if (!response.ok) {
          const errorText = await response.text();
          throw new Error(`HTTP error! status: ${response.status}, message: ${errorText}`);
        }

        const data = await response.json();
        console.log('Fetched article data:', data);

        // Construct full audio URL with fallback
        const audioUrl = data.audio_file
          ? (data.audio_file.startsWith('http')
            ? data.audio_file
            : `${settings.serverUrl}/${data.audio_file}`)
          : null;

        console.log("Constructed audio URL:", audioUrl);

        setArticle({
          ...data,
          content_type,
          audio_file: audioUrl || '',
          date: data.date || data.date_published || data.date_added,
          tldr: data.tl_dr
        });
        
        setError(null);
      } catch (error) {
        console.error('Error fetching article:', error);
        setError(error instanceof Error ? error.message : 'An unknown error occurred');
      }
    }

    fetchArticle();
  }, [articleId, content_type]);

  // Error handling render
  if (error) {
    return (
      <div className="fixed bottom-0 left-0 right-0 bg-red-100 text-red-800 p-4 z-50">
        <p>Error loading content: {error}</p>
        <p>Article ID: {articleId}</p>
        <p>Content Type: {content_type}</p>
      </div>
    );
  }

  if (!article) return null;

  const shouldShowToggle = (content_type === 'article' || content_type === 'text') && article.tldr;
  const content = showTldr && article.tldr ? article.tldr : article.content;

  return (
    <div className={`fixed bottom-0 left-0 right-0 bg-background border-t z-50 transition-all duration-300 ${isExpanded ? 'h-[80vh] overflow-y-auto' : 'h-24'}`}>
      <div className="container mx-auto px-4 h-full">
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
                  audioUrl={article.audio_file}
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
