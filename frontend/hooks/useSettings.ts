import { useState, useEffect, useCallback } from 'react';
import { getSettings as fetchSettings, DEFAULT_SETTINGS, Settings } from "@/lib/settings";

export const useSettings = () => {
  const [settings, setSettings] = useState<Settings>(() => fetchSettings());

  const updateSetting = useCallback((key: keyof Settings, value: string) => {
    const updatedSettings = { ...settings, [key]: value };
    localStorage.setItem('settings', JSON.stringify(updatedSettings));
    setSettings(updatedSettings);
  }, [settings]);

  useEffect(() => {
    const handleStorageChange = () => setSettings(fetchSettings());
    window.addEventListener("storage", handleStorageChange);
    return () => window.removeEventListener("storage", handleStorageChange);
  }, []);

  return { ...settings, updateSetting };
};
