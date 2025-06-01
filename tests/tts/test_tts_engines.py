import unittest
from unittest.mock import patch, MagicMock, call
import os
import sys
import asyncio # <--- Added asyncio

# Add the parent directory to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

# It's critical that these mocks are in place BEFORE TTS.tts_engines is imported.
MOCK_TORCH = MagicMock()
MOCK_TORCHAUDIO = MagicMock()
MOCK_PYDUB_LIB = MagicMock()
MOCK_PYDUB_EFFECTS = MagicMock()

MOCK_CHATTERBOX_PACKAGE = MagicMock()
MOCK_CHATTERBOX_TTS_MODULE = MagicMock()
GlobalMockChatterboxTTSClass = MagicMock()

MOCK_LLM_PACKAGE = MagicMock()
MOCK_LLM_CALLS_MODULE = MagicMock()
GlobalMockGenerateTitle = MagicMock(return_value="Mocked Title")

sys.modules['torch'] = MOCK_TORCH
sys.modules['torchaudio'] = MOCK_TORCHAUDIO
sys.modules['pydub'] = MOCK_PYDUB_LIB
sys.modules['pydub.effects'] = MOCK_PYDUB_EFFECTS
sys.modules['chatterbox'] = MOCK_CHATTERBOX_PACKAGE
sys.modules['chatterbox.tts'] = MOCK_CHATTERBOX_TTS_MODULE
MOCK_CHATTERBOX_TTS_MODULE.ChatterboxTTS = GlobalMockChatterboxTTSClass

sys.modules['llm'] = MOCK_LLM_PACKAGE
sys.modules['llm.LLM_calls'] = MOCK_LLM_CALLS_MODULE
MOCK_LLM_CALLS_MODULE.generate_title = GlobalMockGenerateTitle

from TTS.tts_engines import ChatterboxEngine


class TestChatterboxEngine(unittest.TestCase):

    def setUp(self):
        MOCK_TORCH.reset_mock()
        MOCK_TORCHAUDIO.reset_mock()
        MOCK_PYDUB_LIB.reset_mock()
        MOCK_PYDUB_EFFECTS.reset_mock()
        MOCK_CHATTERBOX_PACKAGE.reset_mock()
        MOCK_CHATTERBOX_TTS_MODULE.reset_mock()
        GlobalMockChatterboxTTSClass.reset_mock()
        MOCK_LLM_PACKAGE.reset_mock()
        MOCK_LLM_CALLS_MODULE.reset_mock()
        GlobalMockGenerateTitle.reset_mock()

        self.mock_model_instance = MagicMock()
        self.mock_model_instance.sr = 16000
        GlobalMockChatterboxTTSClass.from_pretrained.return_value = self.mock_model_instance

        self.mock_audio_segment_class = MagicMock()
        MOCK_PYDUB_LIB.AudioSegment = self.mock_audio_segment_class
        self.mock_segment_instance = MagicMock()
        self.mock_audio_segment_class.from_wav.return_value = self.mock_segment_instance
        MOCK_PYDUB_EFFECTS.speedup = MagicMock(return_value=self.mock_segment_instance)

        self.original_torch_device = MOCK_TORCH.device
        self.mock_torch_device_mps_instance = MagicMock(return_value="mps_device_mock")

        def side_effect_torch_device(arg):
            if arg == 'mps':
                return self.mock_torch_device_mps_instance
            return self.original_torch_device(arg)
        MOCK_TORCH.device = MagicMock(side_effect=side_effect_torch_device)

        self.original_torch_load = MOCK_TORCH.load
        MOCK_TORCH.load = MagicMock()

        self.mock_text_preprocessor_instance = MagicMock()
        self.mock_text_preprocessor_instance.preprocess_text.return_value = ["test chunk"]
        self.text_preprocessor_patch = patch('TTS.tts_engines._TEXT_PREPROCESSOR', self.mock_text_preprocessor_instance)
        self.text_preprocessor_patch.start()

        self.voice_dir = "dummy_voices/"
        self.listdir_patch = patch('os.listdir', return_value=['dummy_voice.wav'])
        self.mock_listdir = self.listdir_patch.start()
        self.path_exists_patch = patch('os.path.exists', return_value=True)
        self.mock_path_exists = self.path_exists_patch.start()
        self.mimetypes_patch = patch('mimetypes.guess_type', return_value=('audio/wav', None))
        self.mock_mimetypes = self.mimetypes_patch.start()

        MOCK_TORCH.cuda.is_available.return_value = False
        MOCK_TORCH.backends.mps.is_available.return_value = False


    def tearDown(self):
        self.text_preprocessor_patch.stop()
        self.listdir_patch.stop()
        self.path_exists_patch.stop()
        self.mimetypes_patch.stop()

        MOCK_TORCH.device = self.original_torch_device
        MOCK_TORCH.load = self.original_torch_load

    # Changed to non-async, using asyncio.run()
    def test_model_loaded_and_unloaded_during_generate_audio_cpu(self):
        async def main_logic():
            MOCK_TORCH.cuda.is_available.return_value = False
            MOCK_TORCH.backends.mps.is_available.return_value = False

            engine = ChatterboxEngine(voice_dir=self.voice_dir)
            self.assertEqual(engine.device, 'cpu')
            self.assertIsNone(engine.model, "Model should be None initially")

            MOCK_TORCH.reset_mock()
            GlobalMockChatterboxTTSClass.from_pretrained.reset_mock()
            MOCK_TORCH.cuda.is_available.return_value = False
            MOCK_TORCH.backends.mps.is_available.return_value = False

            self.mock_model_instance.generate.return_value = MOCK_TORCH.randn(1, 16000)

            await engine.generate_audio("test text", "dummy_voice.wav")

            GlobalMockChatterboxTTSClass.from_pretrained.assert_called_once_with(device='cpu')
            self.assertIsNone(engine.model, "Model should be None after generate_audio")
            MOCK_TORCHAUDIO.save.assert_called()
            MOCK_TORCH.cuda.empty_cache.assert_not_called()
        asyncio.run(main_logic())

    # Changed to non-async, using asyncio.run()
    def test_model_loaded_and_unloaded_during_generate_audio_cuda(self):
        async def main_logic():
            MOCK_TORCH.cuda.is_available.return_value = True
            MOCK_TORCH.backends.mps.is_available.return_value = False

            engine = ChatterboxEngine(voice_dir=self.voice_dir)
            self.assertEqual(engine.device, 'cuda')
            self.assertIsNone(engine.model, "Model should be None initially")

            MOCK_TORCH.reset_mock()
            GlobalMockChatterboxTTSClass.from_pretrained.reset_mock()
            MOCK_TORCH.cuda.is_available.return_value = True
            MOCK_TORCH.backends.mps.is_available.return_value = False

            self.mock_model_instance.generate.return_value = MOCK_TORCH.randn(1, 16000)

            await engine.generate_audio("test text", "dummy_voice.wav")

            GlobalMockChatterboxTTSClass.from_pretrained.assert_called_once_with(device='cuda')
            self.assertIsNone(engine.model, "Model should be None after generate_audio")
            MOCK_TORCH.cuda.empty_cache.assert_called_once()
        asyncio.run(main_logic())

    # Changed to non-async, using asyncio.run()
    def test_model_loaded_and_unloaded_during_generate_audio_mps(self):
        async def main_logic():
            MOCK_TORCH.cuda.is_available.return_value = False
            MOCK_TORCH.backends.mps.is_available.return_value = True

            engine = ChatterboxEngine(voice_dir=self.voice_dir)
            self.assertEqual(engine.device, 'mps')
            self.assertIsNone(engine.model, "Model should be None initially")

            MOCK_TORCH.reset_mock()
            GlobalMockChatterboxTTSClass.from_pretrained.reset_mock()
            MOCK_TORCH.load.reset_mock()
            MOCK_TORCH.cuda.is_available.return_value = False
            MOCK_TORCH.backends.mps.is_available.return_value = True

            self.mock_model_instance.generate.return_value = MOCK_TORCH.randn(1, 16000)

            await engine.generate_audio("test text", "dummy_voice.wav")

            GlobalMockChatterboxTTSClass.from_pretrained.assert_called_once_with(device='mps')
            self.assertIsNone(engine.model, "Model should be None after generate_audio")
            MOCK_TORCH.cuda.empty_cache.assert_not_called()
        asyncio.run(main_logic())

    def test_load_model_actually_loads_cpu(self):
        MOCK_TORCH.cuda.is_available.return_value = False
        MOCK_TORCH.backends.mps.is_available.return_value = False
        engine = ChatterboxEngine(voice_dir=self.voice_dir)
        self.assertEqual(engine.device, 'cpu')
        self.assertIsNone(engine.model)
        GlobalMockChatterboxTTSClass.from_pretrained.reset_mock()

        engine.load_model()

        self.assertIsNotNone(engine.model)
        GlobalMockChatterboxTTSClass.from_pretrained.assert_called_once_with(device='cpu')
        self.assertEqual(engine.sample_rate, self.mock_model_instance.sr)

    def test_unload_model_actually_unloads_cpu(self):
        MOCK_TORCH.cuda.is_available.return_value = False
        MOCK_TORCH.backends.mps.is_available.return_value = False
        engine = ChatterboxEngine(voice_dir=self.voice_dir)
        engine.model = self.mock_model_instance
        engine.sample_rate = self.mock_model_instance.sr

        MOCK_TORCH.reset_mock()
        MOCK_TORCH.cuda.is_available.return_value = False
        MOCK_TORCH.backends.mps.is_available.return_value = False

        engine.unload_model()

        self.assertIsNone(engine.model)
        self.assertIsNone(engine.sample_rate)
        MOCK_TORCH.cuda.empty_cache.assert_not_called()

    def test_unload_model_actually_unloads_cuda(self):
        MOCK_TORCH.cuda.is_available.return_value = True
        MOCK_TORCH.backends.mps.is_available.return_value = False
        engine = ChatterboxEngine(voice_dir=self.voice_dir)
        engine.model = self.mock_model_instance
        engine.sample_rate = self.mock_model_instance.sr

        MOCK_TORCH.reset_mock()
        MOCK_TORCH.cuda.is_available.return_value = True

        engine.unload_model()

        self.assertIsNone(engine.model)
        self.assertIsNone(engine.sample_rate)
        MOCK_TORCH.cuda.empty_cache.assert_called_once()

if __name__ == '__main__':
    unittest.main()
