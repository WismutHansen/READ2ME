'use client';

export interface Settings {
  serverUrl: string;
  ttsEngine: string;
}

export const AVAILABLE_TTS_ENGINES = ['edge', 'localai', 'chatterbox'] as const;

export const DEFAULT_SETTINGS: Settings = {
  serverUrl: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:7777',
  ttsEngine: 'edge'
};

export function getSettings(): Settings {
  if (typeof window === 'undefined') {
    return DEFAULT_SETTINGS;
  }
  
  const savedSettings = localStorage.getItem('settings');
  if (savedSettings) {
    try {
      const parsed = JSON.parse(savedSettings);
      // Ensure we have all required settings
      return {
        ...DEFAULT_SETTINGS,
        ...parsed
      };
    } catch (e) {
      console.error('Error parsing settings:', e);
      return DEFAULT_SETTINGS;
    }
  }
  return DEFAULT_SETTINGS;
}

export function saveSettings(settings: Partial<Settings>) {
  if (typeof window === 'undefined') return;
  
  const currentSettings = getSettings();
  const newSettings = {
    ...currentSettings,
    ...settings
  };
  
  localStorage.setItem('settings', JSON.stringify(newSettings));
  return newSettings;
}
