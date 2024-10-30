const STORAGE_KEYS = {
  SERVER_URL: 'serverUrl',
  TTS_ENGINE: 'ttsEngine',
};

const getSettings = () => {
  if (typeof window === 'undefined') {
    return {
      serverUrl: 'http://localhost:7777',
      ttsEngine: 'edge',
    };
  }

  return {
    serverUrl: localStorage.getItem(STORAGE_KEYS.SERVER_URL) || 'http://localhost:7777',
    ttsEngine: localStorage.getItem(STORAGE_KEYS.TTS_ENGINE) || 'edge',
  };
};

export default getSettings;
