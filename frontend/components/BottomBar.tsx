'use client';

import { useState, useEffect } from 'react';
import AudioPlayer from './AudioPlayer';
import { getSettings } from '@/lib/settings';
import { Button } from '@/components/ui/button';
import { ChevronDown, ChevronUp } from 'lucide-react';
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import MarkdownRenderer from '@/components/MarkdownRenderer';

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
  audioFile?: string;
}

export default function BottomBar({ articleId, type, audioFile }: BottomBarProps) {
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
        // Get the text content
        const response = await fetch(`${settings.serverUrl}/v1/${type}/${encodeURIComponent(articleId)}`, {
          credentials: 'include',
        });

        if (!response.ok) {
          throw new Error('Failed to fetch article');
        }

        const data = await response.json();
        setArticle({
          ...data,
          id: articleId,
          audio_file: audioFile
            ? `${settings.serverUrl}/v1/audio/${encodeURIComponent(audioFile)}`
            : `${settings.serverUrl}/v1/audio/${encodeURIComponent(data.audio_file)}`,
          type: type
        });
      } catch (error) {
        console.error('Error fetching article:', error);
      }
    }

    fetchArticle();
  }, [articleId, type, audioFile]);

  if (!article) {
    return null;
  }

  return (
    <div className={`fixed bottom-0 left-0 right-0 bg-background border-t transition-all duration-300 ${isExpanded ? 'h-[80vh]' : 'h-24'}`}>
      <div className="container mx-auto p-4 h-full">
        <div className="flex items-center justify-between mb-4">
          <div className="flex-1">
            <h2 className="text-lg font-semibold">{article.title}</h2>
          </div>
          <div className="flex items-center gap-4">
            <AudioPlayer audioUrl={article.audio_file} />
            <div className="flex items-center space-x-2">
              {/* <Switch */}
              {/*   id="tldr-mode" */}
              {/*   checked={showTldr} */}
              {/*   onCheckedChange={setShowTldr} */}
              {/* /> */}
              {/* <Label htmlFor="tldr-mode">TL;DR</Label> */}
            </div>
            <Button
              variant="ghost"
              size="icon"
              onClick={toggleExpanded}
              className="flex-shrink-0"
            >
              {isExpanded ? <ChevronDown className="h-4 w-4" /> : <ChevronUp className="h-4 w-4" />}
            </Button>
          </div>
        </div>

          <div className="flex gap-4 items-start h-[calc(100%-4rem)] overflow-hidden">
            <div className="w-full overflow-y-auto pr-4">
              <MarkdownRenderer content={showTldr && article.tldr ? article.tldr : (article.content || '')} />
            </div>
          </div>

        <div className="absolute bottom-4 left-4">
        </div>
      </div>
    </div>
  );
}
