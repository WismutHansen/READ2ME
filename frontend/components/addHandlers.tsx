import { getSettings } from '@/lib/settings';

export const isValidUrl = (url: string): boolean => {
  try {
    new URL(url);
    return true;
  } catch {
    return false;
  }
};

export const handleAddUrl = async (
  url: string,
  endpoint: string,
  setUrl: (url: string) => void,
  setAlertMessage: (message: string | null) => void,
  setMessageType: (type: 'success' | 'error') => void,
  setModalOpen: (open: boolean) => void,
  setAlertDialogOpen: (open: boolean) => void  // Alert dialog control
) => {
  if (!isValidUrl(url)) {
    setMessageType('error');
    setAlertMessage('Please enter a valid URL');
    setAlertDialogOpen(true);
    setTimeout(() => {
      setAlertDialogOpen(false); // Close the alert dialog after 2 seconds
    }, 2000);
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
    setAlertDialogOpen(true);

    setTimeout(() => {
      setAlertDialogOpen(false);  // Close the alert dialog
      setModalOpen(false);        // Close the main modal
    }, 2000);

  } catch (error) {
    console.error(`Error adding URL to ${endpoint}:`, error);
    setMessageType('error');
    setAlertMessage(`Failed to add URL to ${endpoint}`);
    setAlertDialogOpen(true);

    setTimeout(() => {
      setAlertDialogOpen(false); // Close the alert dialog
    }, 2000);
  }
};

// Repeat similar changes for handleAddText function

export const handleAddText = async (
  text: string,
  endpoint: string,
  setText: (text: string) => void,
  setAlertMessage: (message: string | null) => void,
  setMessageType: (type: 'success' | 'error') => void,
  setModalOpen: (open: boolean) => void,
  setAlertDialogOpen: (open: boolean) => void  // Alert dialog control
) => {
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
    setAlertDialogOpen(true);

    setTimeout(() => {
      setAlertDialogOpen(false);  // Close the alert dialog
      setModalOpen(false);        // Close the main modal
    }, 2000);

  } catch (error) {
    console.error(`Error adding text to ${endpoint}:`, error);
    setMessageType('error');
    setAlertMessage(`Failed to add text to ${endpoint}`);
    setAlertDialogOpen(true);

    setTimeout(() => {
      setAlertDialogOpen(false); // Close the alert dialog
    }, 2000);
  }
};
