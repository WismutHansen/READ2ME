import { useState } from 'react';
import { Button } from './ui/button';
import { Input } from './ui/input';

export default function SourceManager() {
  const [url, setUrl] = useState('');
  const [keywords, setKeywords] = useState('');

  const handleAddSource = async () => {
    try {
      const response = await fetch('http://localhost:7777/v1/sources/add', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          sources: [{ url, keywords: keywords.split(',').map(k => k.trim()) }]
        }),
      });
      if (!response.ok) throw new Error('Failed to add source');
      // Reset form and maybe show a success message
      setUrl('');
      setKeywords('');
      alert('Source added successfully');
    } catch (error) {
      console.error('Error adding source:', error);
      alert('Failed to add source');
    }
  };

  const handleFetchArticles = async () => {
    try {
      const response = await fetch('http://localhost:7777/v1/sources/fetch', {
        method: 'POST',
      });
      if (!response.ok) throw new Error('Failed to fetch articles');
      alert('Fetching new articles started');
    } catch (error) {
      console.error('Error fetching articles:', error);
      alert('Failed to fetch articles');
    }
  };

  return (
    <div className="space-y-4">
      <h2 className="text-2xl font-bold">Manage Sources</h2>
      <div className="flex space-x-2">
        <Input
          type="text"
          placeholder="Source URL"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
        />
        <Input
          type="text"
          placeholder="Keywords (comma-separated)"
          value={keywords}
          onChange={(e) => setKeywords(e.target.value)}
        />
        <Button onClick={handleAddSource}>Add Source</Button>
      </div>
      <Button onClick={handleFetchArticles}>Fetch New Articles</Button>
    </div>
  );
}