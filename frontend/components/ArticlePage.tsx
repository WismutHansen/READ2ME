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
  tldr?: string;
  audio_file: string;
  type: string;
  content_type?: string;
}

export default function ArticlePage({ params }: { params: { id: string; type: string } }) {
  const [article, setArticle] = useState<Article | null>(null);
  const [showTldr, setShowTldr] = useState(false);

  useEffect(() => {
    fetchArticle();
  }, [params.id, params.type]);

  const fetchArticle = async () => {
    try {
      // Determine the URL based on the content type
      const endpoint = params.type === 'podcast'
        ? `/api/article/${params.id}`
        : `/api/texts/${params.id}`;

      const response = await fetch(endpoint);
      if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);

      const data = await response.json();
      console.log('Fetched article data:', data); // Debug log
      setArticle(data); // Ensure type is set
    } catch (error) {
      console.error('Error fetching article:', error);
    }
  };

  if (!article) {
    return <div>Loading...</div>;
  }

  const shouldShowToggle = (article.type === 'article' || article.type === 'text') && article.tldr;
  const content = showTldr && article.tldr ? article.tldr : article.content;

  console.log('Article:', article); // Debug log
  console.log('Should show toggle:', shouldShowToggle); // Debug log

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
                  onCheckedChange={setShowTldr}
                />
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
