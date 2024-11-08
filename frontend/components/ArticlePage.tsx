'use client';

import { useState, useEffect } from 'react';
import AudioPlayer from '@/components/AudioPlayer';
import MarkdownRenderer from '@/components/MarkdownRenderer';

export default function ArticlePage({ params }: { params: { id: string; type: string } }) {
  const [article, setArticle] = useState<any>(null);

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
      setArticle(data);
    } catch (error) {
      console.error('Error fetching article:', error);
    }
  };

  if (!article) {
    return <div>Loading...</div>;
  }

  return (
    <div className="container mx-auto px-4 py-8">
      <h1 className="text-3xl font-bold mb-4">{article.title}</h1>
      <AudioPlayer audioUrl={article.audio_file} />
      <MarkdownRenderer content={article.content} />
    </div>
  );
}
