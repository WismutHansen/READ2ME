'use client';

export interface Settings {
  serverUrl: string;
}

export const DEFAULT_SETTINGS: Settings = {
  serverUrl: 'http://localhost:7777'
};

export function getSettings(): Settings {
  if (typeof window === 'undefined') {
    return DEFAULT_SETTINGS;
  }
  
  const savedSettings = localStorage.getItem('settings');
  if (savedSettings) {
    try {
      return JSON.parse(savedSettings);
    } catch (e) {
      console.error('Error parsing settings:', e);
    }
  }
  return DEFAULT_SETTINGS;
}
