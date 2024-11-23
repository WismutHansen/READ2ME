'use client';

import { useState, useEffect } from 'react';
import AudioPlayer from '@/components/AudioPlayer';
import MarkdownRenderer from '@/components/MarkdownRenderer';
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";

interface Article {
  id: string;
  title: string;
  content: string;
  tl_dr?: string;
  audio_file: string;
  type: string;
  content_type?: string;
}

export default function ArticlePage({ params }: { params: { id: string; type: string } }) {
  const [article, setArticle] = useState<Article | null>(null);
  const [showTldr, setShowTldr] = useState(false);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    fetchArticle();
  }, [params.id, params.type]);

  const fetchArticle = async () => {
    try {
      setIsLoading(true);
      // Determine the URL based on the content type
      const endpoint = params.type === 'podcast'
        ? `/api/article/${params.id}`
        : `/api/text/${params.id}`;

      console.log('Fetching from endpoint:', endpoint);
      const response = await fetch(endpoint);
      if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);

      const data = await response.json();
      console.log('Raw API Response:', data);
      console.log('TL;DR content:', data.tl_dr);
      
      // Reset TLDR state when loading new article
      setShowTldr(false);
      setArticle(data);
    } catch (error) {
      console.error('Error fetching article:', error);
    } finally {
      setIsLoading(false);
    }
  };

  if (isLoading) {
    return <div>Loading...</div>;
  }

  if (!article) {
    return <div>Article not found</div>;
  }

  console.log('Current article state:', article);
  console.log('TL;DR available:', Boolean(article.tl_dr));
  console.log('Show TLDR state:', showTldr);

  const shouldShowToggle = (article.type === 'article' || article.type === 'text') && Boolean(article.tl_dr);
  const content = showTldr && article.tl_dr ? article.tl_dr : article.content;

  console.log('Should show toggle:', shouldShowToggle);
  console.log('Content length being displayed:', content?.length);

  return (
    <div className="container mx-auto px-4 py-8 relative min-h-screen pb-24">
      <h1 className="text-3xl font-bold mb-6">{article.title}</h1>
      <div className="mb-24">
        <MarkdownRenderer content={content} />
      </div>
      
      {/* Fixed bottom bar */}
      <div className="fixed bottom-0 left-0 right-0 bg-background border-t">
        <div className="container mx-auto px-4 py-4">
          <div className="flex justify-between items-center">
            <AudioPlayer audioUrl={article.audio_file} />
            {shouldShowToggle && (
              <div className="flex items-center space-x-2 bg-muted p-2 rounded-lg">
                <Label htmlFor="tldr-mode" className="text-sm font-medium px-2">
                  {showTldr ? "TL;DR" : "Full"}
                </Label>
                <Switch
                  id="tldr-mode"
                  checked={showTldr}
                  onCheckedChange={(checked) => {
                    console.log('Switch toggled to:', checked);
                    setShowTldr(checked);
                  }}
                />
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
