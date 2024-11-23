import { useState } from 'react';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { AlertCircle } from 'lucide-react';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Checkbox } from '@/components/ui/checkbox';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  AlertDialog,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";

const DEFAULT_CATEGORIES = [
  "General",
  "News",
  "Technology",
  "Business",
  "Science",
  "Health",
  "Entertainment",
  "Sports",
  "Custom"
];

export default function SourceManager() {
  const [url, setUrl] = useState('');
  const [keywords, setKeywords] = useState('');
  const [fetchAll, setFetchAll] = useState(false);
  const [category, setCategory] = useState('General');
  const [customCategory, setCustomCategory] = useState('');
  const [urlError, setUrlError] = useState('');
  const [dialogMessage, setDialogMessage] = useState<string | null>(null);
  const [dialogType, setDialogType] = useState<'success' | 'error'>('success');

  const validateUrl = (url: string): boolean => {
    try {
      const urlObject = new URL(url);
      if (!['http:', 'https:'].includes(urlObject.protocol)) {
        setUrlError('URL must start with http:// or https://');
        return false;
      }
      if (!urlObject.hostname.includes('.')) {
        setUrlError('URL must contain a valid domain');
        return false;
      }
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
            keywords: fetchAll ? ["*"] : keywords.split(',')
              .map(k => k.trim())
              .filter(k => k.length > 0),
            category: category === 'Custom' ? customCategory : category
          }]
        }),
      });

      if (!response.ok) throw new Error('Failed to add source');

      setUrl('');
      setKeywords('');
      setFetchAll(false);
      setCategory('General');
      setCustomCategory('');
      setDialogType('success');
      setDialogMessage('Source added successfully');
    } catch (error) {
      console.error('Error adding source:', error);
      setDialogType('error');
      setDialogMessage('Failed to add source');
    }
  };

  const handleFetchArticles = async () => {
    try {
      const response = await fetch('http://localhost:7777/v1/sources/fetch', {
        method: 'POST',
      });
      if (!response.ok) throw new Error('Failed to fetch articles');

      setDialogType('success');
      setDialogMessage('Fetching new articles started');
    } catch (error) {
      console.error('Error fetching articles:', error);
      setDialogType('error');
      setDialogMessage('Failed to fetch articles');
    }
  };

  return (
    <div className="space-y-4">
      <h3 className="text">Add sources by url</h3>
      <div className="opacity-75">You can add a source for automatic fetching of new articles. If an RSS feed is found at the url, the source is also added to the Feed List. Sources are periodically scanned for new content and articles are automatically added to the audio library.</div>
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
        
        <div className="space-y-2">
          <div className="opacity-75">Select a category for this source</div>
          <Select
            value={category}
            onValueChange={(value) => {
              setCategory(value);
              if (value !== 'Custom') {
                setCustomCategory('');
              }
            }}
          >
            <SelectTrigger>
              <SelectValue placeholder="Select a category" />
            </SelectTrigger>
            <SelectContent>
              {DEFAULT_CATEGORIES.map((cat) => (
                <SelectItem key={cat} value={cat}>
                  {cat}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          
          {category === 'Custom' && (
            <Input
              type="text"
              placeholder="Enter custom category"
              value={customCategory}
              onChange={(e) => setCustomCategory(e.target.value)}
            />
          )}
        </div>

        <div className="opacity-75">You can specify keywords that are applied to the source (optional). New articles will then only be added if one or more keywords are found. This does not influence the RSS news feed on the main page.</div>
        <div className="flex items-center space-x-2">
          <Checkbox
            id="fetchAll"
            checked={fetchAll}
            onCheckedChange={(checked) => {
              setFetchAll(checked === true);
              if (checked) {
                setKeywords('');
              }
            }}
          />
          <label
            htmlFor="fetchAll"
            className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70"
          >
            Fetch all articles (ignore keywords)
          </label>
        </div>
        <Input
          type="text"
          placeholder="Keywords (comma-separated)"
          value={keywords}
          onChange={(e) => setKeywords(e.target.value)}
          disabled={fetchAll}
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

      {/* AlertDialog for Success and Error Messages */}
      <AlertDialog open={!!dialogMessage} onOpenChange={() => setDialogMessage(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>
              {dialogType === 'success' ? 'Success' : 'Error'}
            </AlertDialogTitle>
            <AlertDialogDescription>
              {dialogMessage}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel onClick={() => setDialogMessage(null)}>Ok</AlertDialogCancel>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
