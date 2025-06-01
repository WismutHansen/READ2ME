import unittest
from unittest.mock import patch, MagicMock
import os
import sys

# Add the parent directory to sys.path to allow imports from llm
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

# Conditional import for ask_Ollama
try:
    from llm.Local_Ollama import ask_Ollama
except ImportError:
    # This might happen if 'ollama' package is not installed in the test environment
    # We can define a placeholder if needed or ensure tests are skipped if module not found
    ask_Ollama = None

# Mock ollama client before it's potentially used.
# We are testing the logic within ask_Ollama, not the ollama client itself.
mock_ollama_client_class = MagicMock()
mock_ollama_client_instance = MagicMock()
mock_ollama_client_class.return_value = mock_ollama_client_instance

# Simulate stream response for client.chat
mock_ollama_client_instance.chat.return_value = iter([
    {"message": {"content": "response chunk 1"}},
    {"message": {"content": "response chunk 2"}},
])

# Patch 'ollama.Client' at the class level in the module where it's imported (llm.Local_Ollama)
# This needs to be active before the class is defined if ask_Ollama is None due to import error.
# However, it's better to apply patches within test methods or setUp for clarity.

@unittest.skipIf(ask_Ollama is None, "ollama package not found, skipping Local_Ollama tests")
class TestAskOllama(unittest.TestCase):

    @patch('llm.Local_Ollama.Client', new=mock_ollama_client_class)
    @patch('os.getenv')
    def test_ask_ollama_low_vram_true(self, mock_getenv):
        # Configure os.getenv for this test
        def side_effect(key, default=None):
            if key == "LOW_VRAM":
                return "True"
            if key == "OLLAMA_BASE_URL":
                return "http://localhost:11434" # Provide default for other getenv calls
            if key == "MODEL_NAME":
                return "test_model"
            return default
        mock_getenv.side_effect = side_effect

        mock_ollama_client_instance.chat.reset_mock() # Reset call stats

        ask_Ollama("test message")

        mock_ollama_client_instance.chat.assert_called_once()
        args, kwargs = mock_ollama_client_instance.chat.call_args
        self.assertEqual(kwargs.get('keep_alive'), "0s")

    @patch('llm.Local_Ollama.Client', new=mock_ollama_client_class)
    @patch('os.getenv')
    def test_ask_ollama_low_vram_false(self, mock_getenv):
        def side_effect(key, default=None):
            if key == "LOW_VRAM":
                return "False"
            if key == "OLLAMA_BASE_URL":
                return "http://localhost:11434"
            if key == "MODEL_NAME":
                return "test_model"
            return default
        mock_getenv.side_effect = side_effect

        mock_ollama_client_instance.chat.reset_mock()

        ask_Ollama("test message")

        mock_ollama_client_instance.chat.assert_called_once()
        args, kwargs = mock_ollama_client_instance.chat.call_args
        self.assertEqual(kwargs.get('keep_alive'), "5m")

    @patch('llm.Local_Ollama.Client', new=mock_ollama_client_class)
    @patch('os.getenv')
    def test_ask_ollama_low_vram_not_set(self, mock_getenv):
        # Simulate LOW_VRAM not being set, relying on the default in os.getenv("LOW_VRAM", "False")
        def side_effect(key, default=None):
            if key == "LOW_VRAM":
                return default # This will be "False" as per ask_Ollama implementation
            if key == "OLLAMA_BASE_URL":
                return "http://localhost:11434"
            if key == "MODEL_NAME":
                return "test_model"
            return default # For any other os.getenv call
        mock_getenv.side_effect = side_effect

        mock_ollama_client_instance.chat.reset_mock()

        ask_Ollama("test message")

        mock_ollama_client_instance.chat.assert_called_once()
        args, kwargs = mock_ollama_client_instance.chat.call_args
        self.assertEqual(kwargs.get('keep_alive'), "5m") # Expecting "5m" as "False" is the default

if __name__ == '__main__':
    # This allows running the tests directly from this file
    # Ensure that the ollama package is available or handle the skip
    if ask_Ollama:
        unittest.main()
    else:
        print("Skipping TestAskOllama: ollama package not found or Local_Ollama.py could not be imported.")
        # You could also raise an exception or exit differently here
        # For CI, it's often better to let the test runner handle skips.
        # The @unittest.skipIf decorator should handle this in a test runner context.
        pass
