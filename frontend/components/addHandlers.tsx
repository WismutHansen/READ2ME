import { useState } from 'react';
import { getSettings } from '@/lib/settings';

type MessageType = 'success' | 'error';

interface AddHandlersReturn {
  handleAddUrl: (url: string, endpoint: string, setUrl: (url: string) => void, onSuccess?: () => void) => Promise<void>;
  handleAddText: (text: string, endpoint: string, setText: (text: string) => void) => Promise<void>;
  alertDialogOpen: boolean;
  setAlertDialogOpen: (open: boolean) => void;
  alertMessage: string | null;
  messageType: MessageType;
}

export const useAddHandlers = (): AddHandlersReturn => {
  const [alertDialogOpen, setAlertDialogOpen] = useState(false);
  const [alertMessage, setAlertMessage] = useState<string | null>(null);
  const [messageType, setMessageType] = useState<MessageType>('success');

  const isValidUrl = (url: string): boolean => {
    try {
      new URL(url);
      return true;
    } catch {
      return false;
    }
  };

  const showAlert = (message: string, type: MessageType) => {
    setMessageType(type);
    setAlertMessage(message);
    setAlertDialogOpen(true);
  };

  const handleAddUrl = async (
    url: string,
    endpoint: string,
    setUrl: (url: string) => void,
    onSuccess?: () => void
  ): Promise<void> => {
    if (!isValidUrl(url)) {
      showAlert('Please enter a valid URL', 'error');
      return;
    }

    const { serverUrl, ttsEngine } = getSettings();
    const fullUrl = `${serverUrl}/v1/${endpoint}`;
    console.log('Making request to:', fullUrl);

    try {
      const response = await fetch(fullUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ url, tts_engine: ttsEngine }),
      });

      if (!response.ok) {
        console.error('Response not ok:', response.status, response.statusText);
        const errorText = await response.text();
        console.error('Error response:', errorText);
        throw new Error(`Failed to add URL to ${endpoint}`);
      }

      setUrl('');
      if (onSuccess) {
        onSuccess();
      }
      showAlert('URL added successfully', 'success');
    } catch (error) {
      console.error(`Error adding URL to ${endpoint}:`, error);
      showAlert(`Failed to add URL to ${endpoint}`, 'error');
    }
  };

  const handleAddText = async (
    text: string,
    endpoint: string,
    setText: (text: string) => void
  ): Promise<void> => {
    if (!text?.trim()) {
      showAlert('Please provide valid text', 'error');
      return;
    }

    const { serverUrl, ttsEngine } = getSettings();

    try {
      const response = await fetch(`${serverUrl}/v1/${endpoint}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ text, tts_engine: ttsEngine }),
      });

      if (!response.ok) {
        throw new Error(`Failed to add text to ${endpoint}`);
      }

      setText('');
      showAlert('Text added successfully', 'success');
    } catch (error) {
      console.error(`Error adding text to ${endpoint}:`, error);
      showAlert(`Failed to add text to ${endpoint}`, 'error');
    }
  };

  return {
    handleAddUrl,
    handleAddText,
    alertDialogOpen,
    setAlertDialogOpen,
    alertMessage,
    messageType,
  };
};
