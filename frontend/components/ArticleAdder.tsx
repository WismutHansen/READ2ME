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
import { handleAddUrl, handleAddText } from '@/components/addHandlers';
export default function ArticleAdder() {
  const [url, setUrl] = useState('');
  const [text, setText] = useState('');
  const [alertMessage, setAlertMessage] = useState<string | null>(null);
  const [messageType, setMessageType] = useState<'success' | 'error'>('success');

  const isValidUrl = (url: string): boolean => {
    try {
      new URL(url);
      return true;
    } catch {
      return false;
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
          <Button onClick={() => handleAddUrl(url, 'url/full', setUrl, setAlertMessage, setMessageType)}>Full Text</Button>
          <Button onClick={() => handleAddUrl(url, 'url/summary', setUrl, setAlertMessage, setMessageType)}>Summary</Button>
          <Button onClick={() => handleAddUrl(url, 'url/podcast', setUrl, setAlertMessage, setMessageType)}>Podcast</Button>
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
          <Button onClick={() => handleAddText(text, 'text/full', setText, setAlertMessage, setMessageType)}>Full Text</Button>
          <Button onClick={() => handleAddText(text, 'text/summary', setText, setAlertMessage, setMessageType)}>Summary</Button>
          <Button onClick={() => handleAddText(text, 'text/podcast', setText, setAlertMessage, setMessageType)}>Podcast</Button>
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
