import { useState, useEffect } from 'react';
import { Button, ButtonProps } from "@/components/ui/button"
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Input } from "@/components/ui/input"
import { Settings } from "lucide-react"
import { useToast } from "@/hooks/use-toast"

interface SettingsManagerProps {
  variant?: ButtonProps['variant']
}

const DEFAULT_SERVER = 'http://127.0.0.1:7777';
const STORAGE_KEYS = {
  SERVER_URL: 'serverUrl',
  TTS_ENGINE: 'ttsEngine'
};

export default function SettingsManager({ variant = "outline" }: SettingsManagerProps) {
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [ttsEngine, setTtsEngine] = useState('edge TTS (online)');
  const [serverUrl, setServerUrl] = useState(DEFAULT_SERVER);
  const { toast } = useToast();

  // Load saved settings on component mount
  useEffect(() => {
    const savedServerUrl = localStorage.getItem(STORAGE_KEYS.SERVER_URL);
    const savedTtsEngine = localStorage.getItem(STORAGE_KEYS.TTS_ENGINE);

    if (savedServerUrl) setServerUrl(savedServerUrl);
    if (savedTtsEngine) setTtsEngine(savedTtsEngine);
  }, []);

  const validateUrl = (url: string): boolean => {
    try {
      new URL(url);
      return true;
    } catch (e) {
      return false;
    }
  };

  const handleSave = () => {
    try {
      // Validate server URL
      if (!serverUrl) {
        toast({
          variant: "destructive",
          title: "Please enter a server URL",
        });
        return;
      }

      if (!validateUrl(serverUrl)) {
        toast({
          variant: "destructive",
          title: "Please enter a valid server URL",
        });
        return;
      }

      // Save to localStorage
      localStorage.setItem(STORAGE_KEYS.SERVER_URL, serverUrl);
      localStorage.setItem(STORAGE_KEYS.TTS_ENGINE, ttsEngine);

      // Show success message
      toast({
        title: "Settings saved successfully",
      });

      // Close the dialog
      setIsSettingsOpen(false);
    } catch (error) {
      toast({
        variant: "destructive",
        title: "Failed to save settings",
      });
    }
  };

  return (
    <Dialog open={isSettingsOpen} onOpenChange={setIsSettingsOpen}>
      <DialogTrigger asChild>
        <Button variant={variant} size="icon">
          <Settings className="h-[1.2rem] w-[1.2rem]" />
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-[425px]">
        <DialogHeader>
          <DialogTitle>Settings</DialogTitle>
        </DialogHeader>
        
        <div className="space-y-4">
          <div className="space-y-2">
            <label className="text-sm font-medium">TTS Engine</label>
            <Select value={ttsEngine} onValueChange={setTtsEngine}>
              <SelectTrigger className="w-full">
                <SelectValue placeholder="Select TTS Engine" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="edge">edge TTS (online)</SelectItem>
                <SelectItem value="F5">F5 (local)</SelectItem>
                <SelectItem value="styletts2">styleTTS 2 (local)</SelectItem>
                <SelectItem value="piper">piper (local)</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-2">
            <label className="text-sm font-medium">Server URL</label>
            <Input
              type="text"
              value={serverUrl}
              onChange={(e) => setServerUrl(e.target.value)}
              placeholder="Enter server URL"
            />
          </div>
        </div>

        <div className="flex justify-end mt-4">
          <Button onClick={handleSave}>Save</Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
