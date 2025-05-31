import sys
import torch
from chatterbox.tts import ChatterboxTTS

class ChatterboxEngine:
    def __init__(self, device=None):
        self.device = self._detect_device(device)
        print(f"Using {self.device} device for Chatterbox TTS.", file=sys.stderr)
        self.model = self._load_model()
        self.sample_rate = self.model.sr
        print("Chatterbox model loaded", file=sys.stderr)

    def _detect_device(self, device):
        if device is not None:
            return device
        if torch.cuda.is_available():
            return "cuda"
        elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            return "mps"
        return "cpu"

    def _load_model(self):
        # Save original torch.load and restore after model loading
        original_torch_load = torch.load
        try:
            if self.device == "mps":
                # Apply MPS device mapping patch
                def patched_torch_load(*args, **kwargs):
                    if "map_location" not in kwargs:
                        kwargs["map_location"] = torch.device(self.device)
                    return original_torch_load(*args, **kwargs)
                torch.load = patched_torch_load
            
            return ChatterboxTTS.from_pretrained(device=self.device)
        finally:
            # Always restore torch.load
            torch.load = original_torch_load

    def synthesize(self, text):
        if not text:
            return None, self.sample_rate
        wav_tensor = self.model.generate(text)
        return wav_tensor.squeeze(0).cpu().numpy(), self.sample_rate
