import { useState, useEffect, useCallback } from 'react';
import { getSettings as fetchSettings, saveSettings, DEFAULT_SETTINGS, Settings } from "@/lib/settings";

export const useSettings = () => {
  const [settings, setSettings] = useState<Settings>(() => fetchSettings());

  const updateSetting = useCallback((key: keyof Settings, value: string) => {
    const newSettings = saveSettings({ [key]: value });
    if (newSettings) {
      setSettings(newSettings);
      // Trigger a storage event for other components
      window.dispatchEvent(new Event('settings-updated'));
    }
  }, []);

  useEffect(() => {
    const handleStorageChange = () => {
      const newSettings = fetchSettings();
      setSettings(newSettings);
    };
    
    window.addEventListener("storage", handleStorageChange);
    window.addEventListener("settings-updated", handleStorageChange);
    
    return () => {
      window.removeEventListener("storage", handleStorageChange);
      window.removeEventListener("settings-updated", handleStorageChange);
    };
  }, []);

  return { ...settings, updateSetting };
};
