import { useState, useEffect } from 'react';
import { Button, ButtonProps } from "@/components/ui/button";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Input } from "@/components/ui/input";
import { Settings } from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import { useSettings } from "@/hooks/useSettings";

interface SettingsManagerProps {
  variant?: ButtonProps['variant'];
}

export default function SettingsManager({ variant = "outline" }: SettingsManagerProps) {
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const { serverUrl, ttsEngine, updateSetting } = useSettings();
  const [localServerUrl, setLocalServerUrl] = useState(serverUrl);
  const [localTtsEngine, setLocalTtsEngine] = useState(ttsEngine);
  const { toast } = useToast();

  useEffect(() => {
    if (isSettingsOpen) {
      setLocalServerUrl(serverUrl);
      setLocalTtsEngine(ttsEngine);
    }
  }, [isSettingsOpen, serverUrl, ttsEngine]);

  const validateUrl = (url: string): boolean => {
    try {
      new URL(url);
      return true;
    } catch (e) {
      return false;
    }
  };

  const handleSave = () => {
    if (!localServerUrl || !validateUrl(localServerUrl)) {
      toast({
        variant: "destructive",
        title: !localServerUrl ? "Please enter a server URL" : "Please enter a valid server URL",
      });
      return;
    }

    updateSetting('serverUrl', localServerUrl);
    updateSetting('ttsEngine', localTtsEngine);

    toast({ title: "Settings saved successfully" });
    setIsSettingsOpen(false);
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
            <Select value={localTtsEngine} onValueChange={setLocalTtsEngine}>
              <SelectTrigger className="w-full">
                <SelectValue placeholder="Select TTS Engine" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="edge">edge TTS (online)</SelectItem>
                <SelectItem value="kokoro">Kokoro TTS (local)</SelectItem>
                <SelectItem value="openai">OpenAI (online)</SelectItem>
                {/* <SelectItem value="styletts2_studio">StyleTTS2 Studio (local)</SelectItem> */}
                {/* <SelectItem value="F5">F5 (local)</SelectItem> */}
                {/* <SelectItem value="styletts2">styleTTS 2 (local)</SelectItem> */}
                {/* <SelectItem value="piper">piper (local)</SelectItem> */}
                {/* <SelectItem value="OuteTTS">OuteTTS (local)</SelectItem> */}
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-2">
            <label className="text-sm font-medium">Server URL</label>
            <Input
              type="text"
              value={localServerUrl}
              onChange={(e) => setLocalServerUrl(e.target.value)}
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
