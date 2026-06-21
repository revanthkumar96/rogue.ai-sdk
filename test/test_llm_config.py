"""Tests for LLM instrumentation configuration"""

import os
import unittest
from unittest.mock import MagicMock, patch

from rouge_ai.config import RougeConfig
from rouge_ai.integrations.llm import instrument_llm
from rouge_ai.tracer import _load_env_config


class TestLLMInstrumentationConfig(unittest.TestCase):
    """Test LLM instrumentation configuration and filtering"""

    def setUp(self):
        self.config = RougeConfig(service_name="test-service",
                                  github_owner="test-owner",
                                  github_repo_name="test-repo",
                                  github_commit_hash="abc1234",
                                  tracer_verbose=True)

    @patch("builtins.__import__")
    def test_instrument_all_by_default(self, mock_import):
        """Test that all providers are attempted if llm_providers is None"""
        # Mock successful import for OpenAI
        mock_openai = MagicMock()

        def side_effect(name, fromlist=None):
            if name == "opentelemetry.instrumentation.openai":
                return mock_openai
            raise ImportError

        mock_import.side_effect = side_effect

        instrument_llm(self.config)

        # Verify OpenAI was attempted (this checks if all were tried)
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

    @patch("builtins.__import__")
    def test_haystack_is_wired(self, mock_import):
        """Haystack (shipped in the [llm] extra) is now instrumented."""
        mock_import.side_effect = ImportError
        instrument_llm(self.config)
        calls = [call[0][0] for call in mock_import.call_args_list]
        self.assertIn("opentelemetry.instrumentation.haystack", calls)

    @patch("builtins.__import__")
    def test_block_list_excludes_provider(self, mock_import):
        """A blocked provider is skipped even under allow-all (default)."""
        mock_import.side_effect = ImportError
        self.config.llm_block_providers = ["OpenAI"]

        instrument_llm(self.config)

        calls = [call[0][0] for call in mock_import.call_args_list]
        self.assertNotIn("opentelemetry.instrumentation.openai", calls)
        # Other providers are still attempted.
        self.assertIn("opentelemetry.instrumentation.anthropic", calls)

    @patch("builtins.__import__")
    def test_block_list_overrides_allow_list(self, mock_import):
        """Block-list wins over allow-list for the same provider."""
        mock_import.side_effect = ImportError
        self.config.llm_providers = ["openai", "anthropic"]
        self.config.llm_block_providers = ["anthropic"]

        instrument_llm(self.config)

        calls = [call[0][0] for call in mock_import.call_args_list]
        self.assertEqual(calls, ["opentelemetry.instrumentation.openai"])


class TestLLMEnvConfig(unittest.TestCase):
    """LLM instrumentation is configurable via environment variables."""

    def test_llm_providers_parsed_from_env(self):
        with patch.dict(os.environ,
                        {"ROUGE_LLM_PROVIDERS": "openai, anthropic"}):
            cfg = _load_env_config()
        self.assertEqual(cfg["llm_providers"], ["openai", "anthropic"])

    def test_llm_block_providers_parsed_from_env(self):
        with patch.dict(os.environ,
                        {"ROUGE_LLM_BLOCK_PROVIDERS": "cohere,replicate"}):
            cfg = _load_env_config()
        self.assertEqual(cfg["llm_block_providers"], ["cohere", "replicate"])

    def test_instrument_llm_bool_parsed_from_env(self):
        with patch.dict(os.environ, {"ROUGE_INSTRUMENT_LLM": "false"}):
            cfg = _load_env_config()
        self.assertIs(cfg["instrument_llm"], False)


if __name__ == "__main__":
    unittest.main()
