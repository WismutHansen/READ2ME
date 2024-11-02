import { useState } from 'react';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Textarea } from './ui/textarea';

const STORAGE_KEYS = {
  SERVER_URL: 'serverUrl',
  TTS_ENGINE: 'ttsEngine',
};

export default function ArticleAdder() {
  const [url, setUrl] = useState('');
  const [text, setText] = useState('');

  const getSettings = () => {
    const serverUrl = localStorage.getItem(STORAGE_KEYS.SERVER_URL) || 'http://localhost:7777';
    const ttsEngine = localStorage.getItem(STORAGE_KEYS.TTS_ENGINE) || 'edge';
    return { serverUrl, ttsEngine };
  };

  const handleAddUrl = async (endpoint: string) => {
    const { serverUrl, ttsEngine } = getSettings();
    try {
      const response = await fetch(`${serverUrl}/v1/${endpoint}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ url, tts_engine: ttsEngine }),
      });
      if (!response.ok) throw new Error(`Failed to add URL to ${endpoint}`);
      setUrl('');
      alert('URL added successfully');
    } catch (error) {
      console.error(`Error adding URL to ${endpoint}:`, error);
      alert(`Failed to add URL to ${endpoint}`);
    }
  };

  const handleAddText = async (endpoint: string) => {
    const { serverUrl, ttsEngine } = getSettings();
    try {
      const response = await fetch(`${serverUrl}/v1/${endpoint}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ text, tts_engine: ttsEngine }),
      });
      if (!response.ok) throw new Error(`Failed to add text to ${endpoint}`);
      setText('');
      alert('Text added successfully');
    } catch (error) {
      console.error(`Error adding text to ${endpoint}:`, error);
      alert(`Failed to add text to ${endpoint}`);
    }
  };

  return (
    <div className="space-y-4">
      <h2 className="text-2xl font-bold">Add Single Article</h2>
      
      {/* URL inputs */}
      <div className="space-y-2">
        <Input
          type="text"
          placeholder="Article URL"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
        />
        <div className="flex flex-wrap gap-2">
          <Button onClick={() => handleAddUrl('url/full')}>Full text</Button>
          <Button onClick={() => handleAddUrl('url/summary')}>Summary</Button>
          <Button onClick={() => handleAddUrl('url/podcast')}>Podcast</Button>
        </div>
      </div>

      {/* Text inputs */}
      <div className="space-y-2">
        <Textarea
          placeholder="Article text"
          value={text}
          onChange={(e) => setText(e.target.value)}
        />
        <div className="flex flex-wrap gap-2">
          <Button onClick={() => handleAddText('text/full')}>Full Text</Button>
          <Button onClick={() => handleAddText('text/summary')}>Summary</Button>
          <Button onClick={() => handleAddText('text/podcast')}>Podcast</Button>
        </div>
      </div>
    </div>
  );
}