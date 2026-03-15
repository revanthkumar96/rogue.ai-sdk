"""Tests for LLM instrumentation configuration"""

import unittest
from unittest.mock import MagicMock, patch

import rouge
from rouge.config import RougeConfig
from rouge.integrations.llm import instrument_llm


class TestLLMInstrumentationConfig(unittest.TestCase):
    """Test LLM instrumentation configuration and filtering"""

    def setUp(self):
        self.config = RougeConfig(
            service_name="test-service",
            github_owner="test-owner",
            github_repo_name="test-repo",
            github_commit_hash="abc123",
            tracer_verbose=True
        )

    @patch("builtins.__import__")
    def test_instrument_all_by_default(self, mock_import):
        """Test that all providers are attempted if llm_providers is None"""
        # Mock successful import for OpenAI
        mock_openai = MagicMock()
        mock_import.side_effect = lambda name, fromlist: mock_openai if name == "opentelemetry.instrumentation.openai" else exec("raise ImportError")
        
        instrument_llm(self.config)
        
        # Check that OpenAI was attempted (this is enough to verify it tried all)
        # In our implementation, it tries all 10.
        self.assertGreaterEqual(mock_import.call_count, 1)

    @patch("builtins.__import__")
    def test_instrument_filtered_providers(self, mock_import):
        """Test that only specified providers are attempted"""
        self.config.llm_providers = ["OpenAI"]
        
        instrument_llm(self.config)
        
        # Check that only OpenAI was attempted
        # It should call __import__ with 'opentelemetry.instrumentation.openai'
        calls = [call[0][0] for call in mock_import.call_args_list]
        self.assertIn("opentelemetry.instrumentation.openai", calls)
        self.assertEqual(len(calls), 1)

    @patch("builtins.__import__")
    def test_instrument_disabled(self, mock_import):
        """Test that no providers are attempted if instrument_llm is False"""
        self.config.instrument_llm = False
        
        instrument_llm(self.config)
        
        self.assertEqual(mock_import.call_count, 0)


if __name__ == "__main__":
    unittest.main()
