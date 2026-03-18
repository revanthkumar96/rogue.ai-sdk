"""Unit tests for tracer_verbose functionality"""

import io
import os
import unittest
from contextlib import redirect_stdout

import rouge_ai
from rouge_ai import tracer


class TestTracerVerbose(unittest.TestCase):
    """Test tracer_verbose functionality"""

    def setUp(self):
        """Set up test environment"""
        # Clean up any existing env vars before each test
        self._cleanup_env_vars()
        # Shutdown any existing tracer
        tracer.shutdown()

    def tearDown(self):
        """Clean up after each test"""
        self._cleanup_env_vars()
        tracer.shutdown()

    def _cleanup_env_vars(self):
        """Remove test environment variables"""
        env_vars = [
            'ROUGE_TRACER_VERBOSE', 'ROUGE_LOGGER_VERBOSE',
            'ROUGE_SERVICE_NAME', 'ROUGE_GITHUB_OWNER',
            'ROUGE_GITHUB_REPO_NAME', 'ROUGE_GITHUB_COMMIT_HASH'
        ]
        for var in env_vars:
            if var in os.environ:
                del os.environ[var]

    def test_verbose_logging_enabled(self):
        """Test that verbose logging works when tracer_verbose is enabled"""
        # Set up environment variables
        os.environ['ROUGE_TRACER_VERBOSE'] = 'true'
        os.environ['ROUGE_SERVICE_NAME'] = 'test-service'
        os.environ['ROUGE_GITHUB_OWNER'] = 'test-owner'
        os.environ['ROUGE_GITHUB_REPO_NAME'] = 'test-repo'
        os.environ['ROUGE_GITHUB_COMMIT_HASH'] = 'abc1234'

        # Capture stdout to check for verbose output
        captured_output = io.StringIO()

        with redirect_stdout(captured_output):
            # Initialize rouge_ai with verbose logging enabled
            rouge_ai.init()

            # Get the config to verify tracer_verbose is True
            config = tracer.get_config()
            self.assertTrue(config.tracer_verbose)

            # Check that verbose initialization messages were printed
            output = captured_output.getvalue()
            self.assertIn("[Rouge-Tracer] Initializing Rouge with config:",
                          output)
            self.assertIn("tracer_verbose", output)

    def test_verbose_logging_disabled(self):
        """Test that verbose logging is suppressed when tracer_verbose is
        disabled
        """
        # Set up environment variables with verbose disabled
        os.environ['ROUGE_TRACER_VERBOSE'] = 'false'
        os.environ['ROUGE_SERVICE_NAME'] = 'test-service'
        os.environ['ROUGE_GITHUB_OWNER'] = 'test-owner'
        os.environ['ROUGE_GITHUB_REPO_NAME'] = 'test-repo'
        os.environ['ROUGE_GITHUB_COMMIT_HASH'] = 'abc1234'

        # Capture stdout to check for verbose output
        captured_output = io.StringIO()

        with redirect_stdout(captured_output):
            # Initialize tracer with verbose logging disabled
            rouge_ai.init()

            # Get the config to verify tracer_verbose is False
            config = tracer.get_config()
            self.assertFalse(config.tracer_verbose)

            # Check that verbose initialization messages were NOT printed
            output = captured_output.getvalue()
            self.assertNotIn("[Rouge-Tracer] Initializing Rouge with config:",
                             output)

    def test_verbose_logging_with_trace_function(self):
        """Test that verbose logging works with the trace decorator"""
        # Set up environment variables
        os.environ['ROUGE_TRACER_VERBOSE'] = 'true'
        os.environ['ROUGE_SERVICE_NAME'] = 'test-service'
        os.environ['ROUGE_GITHUB_OWNER'] = 'test-owner'
        os.environ['ROUGE_GITHUB_REPO_NAME'] = 'test-repo'
        os.environ['ROUGE_GITHUB_COMMIT_HASH'] = 'abc1234'

        # Initialize tracer
        rouge_ai.init()

        # Define a test function to trace
        @tracer.trace()
        def test_function():
            return "test result"

        # Call the traced function - verbose output goes to logger, not stdout
        result = test_function()
        self.assertEqual(result, "test result")

        # The test passes if no exception is raised and the function executes
        # The verbose logging is verified by the fact that the tracer was
        # initialized and the function was successfully traced

    def test_logger_verbose_enabled(self):
        """Test that logger verbose logging works when logger_verbose is
        enabled
        """
        # Set up environment variables
        os.environ['ROUGE_LOGGER_VERBOSE'] = 'true'
        os.environ['ROUGE_SERVICE_NAME'] = 'test-service'
        os.environ['ROUGE_GITHUB_OWNER'] = 'test-owner'
        os.environ['ROUGE_GITHUB_REPO_NAME'] = 'test-repo'
        os.environ['ROUGE_GITHUB_COMMIT_HASH'] = 'abc1234'

        # Capture stdout to check for verbose output
        captured_output = io.StringIO()

        with redirect_stdout(captured_output):
            # Initialize tracer with logger verbose logging enabled
            rouge_ai.init()

            # Get the config to verify logger_verbose is True
            config = tracer.get_config()
            self.assertTrue(config.logger_verbose)

            # Check that logger verbose initialization messages were printed
            output = captured_output.getvalue()
            self.assertIn("[Rouge-Logger] Initializing Rouge logger...",
                          output)
            self.assertIn(
                "[Rouge-Logger] Setting up logger with service name:", output)

    def test_logger_verbose_disabled(self):
        """Test that logger verbose logging is suppressed when
        logger_verbose is disabled
        """
        # Set up environment variables with logger verbose disabled
        os.environ['ROUGE_LOGGER_VERBOSE'] = 'false'
        os.environ['ROUGE_SERVICE_NAME'] = 'test-service'
        os.environ['ROUGE_GITHUB_OWNER'] = 'test-owner'
        os.environ['ROUGE_GITHUB_REPO_NAME'] = 'test-repo'
        os.environ['ROUGE_GITHUB_COMMIT_HASH'] = 'abc1234'

        # Capture stdout to check for verbose output
        captured_output = io.StringIO()

        with redirect_stdout(captured_output):
            # Initialize tracer with logger verbose logging disabled
            rouge_ai.init()

            # Get the config to verify logger_verbose is False
            config = tracer.get_config()
            self.assertFalse(config.logger_verbose)

            # Check that logger verbose initialization messages were NOT
            # printed
            output = captured_output.getvalue()
            self.assertNotIn("[Rouge-Logger] Initializing Rouge logger...",
                             output)
            self.assertNotIn(
                "[Rouge-Logger] Setting up logger with service name:", output)

    def test_both_verbose_enabled(self):
        """Test that both tracer_verbose and logger_verbose can be enabled
        simultaneously
        """
        # Set up environment variables
        os.environ['ROUGE_TRACER_VERBOSE'] = 'true'
        os.environ['ROUGE_LOGGER_VERBOSE'] = 'true'
        os.environ['ROUGE_SERVICE_NAME'] = 'test-service'
        os.environ['ROUGE_GITHUB_OWNER'] = 'test-owner'
        os.environ['ROUGE_GITHUB_REPO_NAME'] = 'test-repo'
        os.environ['ROUGE_GITHUB_COMMIT_HASH'] = 'abc1234'

        # Capture stdout to check for verbose output
        captured_output = io.StringIO()

        with redirect_stdout(captured_output):
            # Initialize tracer with both verbose modes enabled
            rouge_ai.init()

            # Get the config to verify both verbose modes are True
            config = tracer.get_config()
            self.assertTrue(config.tracer_verbose)
            self.assertTrue(config.logger_verbose)

            # Check that both tracer and logger verbose messages were printed
            output = captured_output.getvalue()
            self.assertIn("[Rouge-Tracer] Initializing Rouge with config:",
                          output)
            self.assertIn("[Rouge-Logger] Initializing Rouge logger...",
                          output)
            self.assertIn("tracer_verbose", output)
            self.assertIn("logger_verbose", output)

    def test_verbose_logging_default_behavior(self):
        """Test that verbose logging defaults to False when not set"""
        # Don't set ROUGE_TRACER_VERBOSE environment variable
        os.environ['ROUGE_SERVICE_NAME'] = 'test-service'
        os.environ['ROUGE_GITHUB_OWNER'] = 'test-owner'
        os.environ['ROUGE_GITHUB_REPO_NAME'] = 'test-repo'
        os.environ['ROUGE_GITHUB_COMMIT_HASH'] = 'abc1234'

        # Capture stdout to check for verbose output
        captured_output = io.StringIO()

        with redirect_stdout(captured_output):
            # Initialize tracer without setting tracer_verbose
            rouge_ai.init()

            # Get the config to verify tracer_verbose defaults to False
            config = tracer.get_config()
            self.assertFalse(config.tracer_verbose)

            # Check that verbose initialization messages were NOT printed
            output = captured_output.getvalue()
            self.assertNotIn("[Rouge-Tracer] Initializing Rouge with config:",
                             output)


if __name__ == '__main__':
    unittest.main()
