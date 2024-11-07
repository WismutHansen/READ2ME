import { useState } from 'react';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Textarea } from './ui/textarea';
import {
  AlertDialog,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog"

const STORAGE_KEYS = {
  SERVER_URL: 'serverUrl',
  TTS_ENGINE: 'ttsEngine',
};

export default function ArticleAdder() {
  const [url, setUrl] = useState('');
  const [text, setText] = useState('');
  const [alertMessage, setAlertMessage] = useState<string | null>(null);
  const [messageType, setMessageType] = useState<'success' | 'error'>('success');

  const getSettings = () => {
    const serverUrl = localStorage.getItem(STORAGE_KEYS.SERVER_URL) || 'http://localhost:7777';
    const ttsEngine = localStorage.getItem(STORAGE_KEYS.TTS_ENGINE) || 'edge';
    return { serverUrl, ttsEngine };
  };

  const isValidUrl = (url: string): boolean => {
    try {
      new URL(url);
      return true;
    } catch {
      return false;
    }
  };

  const handleAddUrl = async (endpoint: string) => {
    if (!isValidUrl(url)) {
      setMessageType('error');
      setAlertMessage('Please enter a valid URL');
      return;
    }

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
      setMessageType('success');
      setAlertMessage('URL added successfully');
    } catch (error) {
      console.error(`Error adding URL to ${endpoint}:`, error);
      setMessageType('error');
      setAlertMessage(`Failed to add URL to ${endpoint}`);
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
      setMessageType('success');
      setAlertMessage('Text added successfully');
    } catch (error) {
      console.error(`Error adding text to ${endpoint}:`, error);
      setMessageType('error');
      setAlertMessage(`Failed to add text to ${endpoint}`);
    }
  };

  return (
    <div className="space-y-4">
      <h2 className="text">Add Single Article by URL</h2>

      {/* URL inputs */}
      <div className="space-y-2">
        <Input
          type="text"
          placeholder="Article URL"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
        />
        <div className="flex flex-wrap gap-2">
          <Button onClick={() => handleAddUrl('url/full')}>Full Text</Button>
          <Button onClick={() => handleAddUrl('url/summary')}>Summary</Button>
          <Button onClick={() => handleAddUrl('url/podcast')}>Podcast</Button>
        </div>
      </div>

      {/* Text inputs */}
      <div className="space-y-2">
        <h2 className="text">Add Text</h2>
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

      {/* AlertDialog for Messages */}
      <AlertDialog open={!!alertMessage} onOpenChange={() => setAlertMessage(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>
              {messageType === 'success' ? 'Success' : 'Error'}
            </AlertDialogTitle>
            <AlertDialogDescription>
              {alertMessage}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel onClick={() => setAlertMessage(null)}>Ok</AlertDialogCancel>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
