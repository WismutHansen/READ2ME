import { useState } from 'react';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { AlertCircle } from 'lucide-react';
import { Alert, AlertDescription } from '@/components/ui/alert';

export default function SourceManager() {
  const [url, setUrl] = useState('');
  const [keywords, setKeywords] = useState('');
  const [urlError, setUrlError] = useState('');

  const validateUrl = (url: string): boolean => {
    try {
      // First, try to construct a URL object (this checks basic URL format)
      const urlObject = new URL(url);
      
      // Check if protocol is http or https
      if (!['http:', 'https:'].includes(urlObject.protocol)) {
        setUrlError('URL must start with http:// or https://');
        return false;
      }

      // Check if URL has a valid domain
      if (!urlObject.hostname.includes('.')) {
        setUrlError('URL must contain a valid domain');
        return false;
      }

      // Clear any previous errors if validation passes
      setUrlError('');
      return true;
    } catch (err) {
      setUrlError('Please enter a valid URL');
      return false;
    }
  };

  const handleUrlChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newUrl = e.target.value;
    setUrl(newUrl);
    if (newUrl) {
      validateUrl(newUrl);
    } else {
      setUrlError('');
    }
  };

  const handleAddSource = async () => {
    // Validate URL before proceeding
    if (!url) {
      setUrlError('URL is required');
      return;
    }

    if (!validateUrl(url)) {
      return;
    }

    try {
      const response = await fetch('http://localhost:7777/v1/sources/add', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          sources: [{ 
            url, 
            keywords: keywords.split(',')
              .map(k => k.trim())
              .filter(k => k.length > 0) 
          }]
        }),
      });
      
      if (!response.ok) throw new Error('Failed to add source');
      
      // Reset form and show success message
      setUrl('');
      setKeywords('');
      setUrlError('');
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
      <div className="flex flex-col space-y-4">
        <div className="space-y-2">
          <Input
            type="text"
            placeholder="Source URL"
            value={url}
            onChange={handleUrlChange}
            className={urlError ? 'border-red-500' : ''}
          />
          {urlError && (
            <Alert variant="destructive" className="py-2">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>{urlError}</AlertDescription>
            </Alert>
          )}
        </div>
        <Input
          type="text"
          placeholder="Keywords (comma-separated)"
          value={keywords}
          onChange={(e) => setKeywords(e.target.value)}
        />
        <div className="flex space-x-2">
          <Button 
            onClick={handleAddSource} 
            className="flex-1"
            disabled={!!urlError}
          >
            Add Source
          </Button>
          <Button 
            onClick={handleFetchArticles}
            variant="secondary"
            className="flex-1"
          >
            Fetch New Articles
          </Button>
        </div>
      </div>
    </div>
  );
}
