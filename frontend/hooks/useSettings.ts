import { useState, useEffect } from 'react';

const STORAGE_KEYS = {
  SERVER_URL: 'serverUrl',
  TTS_ENGINE: 'ttsEngine',
};

// Regular function to get settings without React hooks
export const getSettings = () => {
  const serverUrl = localStorage.getItem(STORAGE_KEYS.SERVER_URL) || 'http://localhost:7777';
  const ttsEngine = localStorage.getItem(STORAGE_KEYS.TTS_ENGINE) || 'edge';
  return { serverUrl, ttsEngine };
};

// Custom hook for use within functional components
export const useSettings = () => {
  const [settings, setSettings] = useState(() => getSettings());

  useEffect(() => {
    const storedSettings = getSettings();
    setSettings(storedSettings);
  }, []);

  return settings;
};
