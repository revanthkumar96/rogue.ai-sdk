import unittest
from unittest.mock import MagicMock, patch

from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import (BatchSpanProcessor,
                                            SimpleSpanProcessor)

from rouge_ai import init


class TestTracer(unittest.TestCase):

    def setUp(self):
        """Reset global state before each test"""
        import rouge_ai.logger as logger_module
        import rouge_ai.tracer as tracer_module

        # Clean up any existing providers
        if tracer_module._tracer_provider:
            tracer_module._tracer_provider.shutdown()
        tracer_module._tracer_provider = None
        tracer_module._config = None
        # Reset the OTel process-global so each test gets a fresh provider.
        tracer_module._reset_global_tracer_provider()

        # Clean up logger state thoroughly
        if logger_module._global_logger:
            # Remove all handlers from existing logger
            for handler in logger_module._global_logger.logger.handlers[:]:
                logger_module._global_logger.logger.removeHandler(handler)
                if hasattr(handler, 'close'):
                    handler.close()
        logger_module._global_logger = None
        logger_module._cloudwatch_handler = None

    def tearDown(self):
        """Clean up after each test"""
        import rouge_ai.logger as logger_module
        import rouge_ai.tracer as tracer_module

        if tracer_module._tracer_provider:
            tracer_module._tracer_provider.shutdown()
        tracer_module._tracer_provider = None
        tracer_module._config = None
        # Reset the OTel process-global so the next test gets a fresh provider.
        tracer_module._reset_global_tracer_provider()

        # Clean up logger state thoroughly
        if logger_module._global_logger:
            # Remove all handlers from existing logger
            for handler in logger_module._global_logger.logger.handlers[:]:
                logger_module._global_logger.logger.removeHandler(handler)
                if hasattr(handler, 'close'):
                    handler.close()
        logger_module._global_logger = None
        logger_module._cloudwatch_handler = None

    @patch('rouge_ai.credentials.CredentialManager.get_credentials')
    @patch('boto3.Session')
    def test_both_console_and_cloud_span_enabled(
        self,
        mock_boto_session,
        mock_get_credentials,
    ):
        """Test that both console and cloud span processors
        are added when both are enabled
        """
        # Mock AWS credentials
        mock_get_credentials.return_value = None
        mock_boto_session.return_value = MagicMock()

        provider = init(service_name="test-service",
                        github_owner="test-owner",
                        github_repo_name="test-repo",
                        github_commit_hash="test-hash",
                        enable_span_console_export=True,
                        enable_span_cloud_export=True,
                        otlp_endpoint="https://test-endpoint:4318/v1/traces")

        # Verify that a TracerProvider was created
        self.assertIsInstance(provider, TracerProvider)

        # Verify that both processors were added
        self.assertEqual(len(provider._active_span_processor._span_processors),
                         2)

        # Check processor types
        processors = provider._active_span_processor._span_processors
        processor_types = [type(processor) for processor in processors]

        # Should have both SimpleSpanProcessor
        # (console) and BatchSpanProcessor (OTLP)
        self.assertIn(SimpleSpanProcessor, processor_types)
        self.assertIn(BatchSpanProcessor, processor_types)

    def test_both_console_and_cloud_span_disabled(self):
        """Test that no span processors are added when both are disabled"""
        provider = init(service_name="test-service",
                        github_owner="test-owner",
                        github_repo_name="test-repo",
                        github_commit_hash="test-hash",
                        enable_span_console_export=False,
                        enable_span_cloud_export=False,
                        otlp_endpoint="https://test-endpoint:4318/v1/traces")

        # Verify that a TracerProvider was created
        self.assertIsInstance(provider, TracerProvider)

        # Verify that no processors were added
        self.assertEqual(len(provider._active_span_processor._span_processors),
                         0)

    def test_only_console_span_enabled(self):
        """Test that only console span processor is
        added when only console is enabled
        """
        provider = init(service_name="test-service",
                        github_owner="test-owner",
                        github_repo_name="test-repo",
                        github_commit_hash="test-hash",
                        enable_span_console_export=True,
                        enable_span_cloud_export=False,
                        otlp_endpoint="https://test-endpoint:4318/v1/traces")

        # Verify that a TracerProvider was created
        self.assertIsInstance(provider, TracerProvider)

        # Verify that only one processor was added
        self.assertEqual(len(provider._active_span_processor._span_processors),
                         1)

        # Check processor type
        processors = provider._active_span_processor._span_processors
        processor_types = [type(processor) for processor in processors]

        # Should only have SimpleSpanProcessor (console)
        self.assertIn(SimpleSpanProcessor, processor_types)
        self.assertNotIn(BatchSpanProcessor, processor_types)

    @patch('rouge_ai.credentials.CredentialManager.get_credentials')
    @patch('boto3.Session')
    def test_only_cloud_span_enabled(self, mock_boto_session,
                                     mock_get_credentials):
        """Test that only cloud span processor is added
        when only cloud is enabled
        """
        # Mock AWS credentials
        mock_get_credentials.return_value = None
        mock_boto_session.return_value = MagicMock()

        provider = init(service_name="test-service",
                        github_owner="test-owner",
                        github_repo_name="test-repo",
                        github_commit_hash="test-hash",
                        enable_span_console_export=False,
                        enable_span_cloud_export=True,
                        otlp_endpoint="https://test-endpoint:4318/v1/traces")

        # Verify that a TracerProvider was created
        self.assertIsInstance(provider, TracerProvider)

        # Verify that only one processor was added
        self.assertEqual(len(provider._active_span_processor._span_processors),
                         1)

        # Check processor type
        processors = provider._active_span_processor._span_processors
        processor_types = [type(processor) for processor in processors]

        # Should only have BatchSpanProcessor (OTLP/cloud)
        self.assertIn(BatchSpanProcessor, processor_types)
        self.assertNotIn(SimpleSpanProcessor, processor_types)

    # --- B9: capture helpers (pandas-free, valid attribute types) ----------

    def test_flatten_dict_no_pandas(self):
        """B9: nested dicts flatten without pandas."""
        from rouge_ai.tracer import _flatten_dict
        self.assertEqual(_flatten_dict({
            "a": {
                "b": 1
            },
            "c": 2
        }), {
            "a_b": 1,
            "c": 2
        })

    def test_coerce_attr_value(self):
        """B9: values coerce to valid OTel attribute types."""
        from rouge_ai.tracer import _coerce_attr_value
        self.assertEqual(_coerce_attr_value("s"), "s")
        self.assertEqual(_coerce_attr_value(5), 5)
        self.assertIs(_coerce_attr_value(True), True)
        # Non-scalars are JSON-encoded into a single string.
        self.assertEqual(_coerce_attr_value([1, 2]), "[1, 2]")
        self.assertEqual(_coerce_attr_value({"x": 1}), '{"x": 1}')

    def test_store_dict_truncates_with_env(self):
        """B9: long values truncate to the OTel length-limit env var."""
        import os

        from rouge_ai.tracer import _store_dict_in_span
        span = MagicMock()
        with patch.dict(os.environ,
                        {"OTEL_SPAN_ATTRIBUTE_VALUE_LENGTH_LIMIT": "5"}):
            _store_dict_in_span({"k": "abcdefghij"}, span, flatten=False)
        stored = span.set_attributes.call_args[0][0]
        self.assertEqual(stored["k"], "abcde")

    # --- B8: streaming spans cover the full iteration ----------------------

    def _exporter_on_provider(self):
        from opentelemetry.sdk.trace.export import SimpleSpanProcessor
        from opentelemetry.sdk.trace.export.in_memory_span_exporter import \
            InMemorySpanExporter

        import rouge_ai.tracer as tracer_module
        init(service_name="svc",
             local_mode=True,
             enable_span_console_export=False,
             enable_span_cloud_export=False,
             enable_log_cloud_export=False)
        exporter = InMemorySpanExporter()
        tracer_module._tracer_provider.add_span_processor(
            SimpleSpanProcessor(exporter))
        return exporter

    def test_sync_generator_span_covers_full_iteration(self):
        """B8: a traced generator yields all items and records one span."""
        from rouge_ai.tracer import TraceOptions, trace
        exporter = self._exporter_on_provider()

        @trace(TraceOptions(trace_return_value=True))
        def gen():
            yield 1
            yield 2

        self.assertEqual(list(gen()), [1, 2])
        spans = exporter.get_finished_spans()
        self.assertEqual(len(spans), 1)
        self.assertEqual(spans[0].attributes.get("return"), "[1, 2]")

    def test_async_generator_span_covers_full_iteration(self):
        """B8: a traced async generator yields all items and records a span."""
        import asyncio

        from rouge_ai.tracer import TraceOptions, trace
        exporter = self._exporter_on_provider()

        @trace(TraceOptions(trace_return_value=True))
        async def agen():
            yield "a"
            yield "b"

        async def consume():
            return [x async for x in agen()]

        self.assertEqual(asyncio.run(consume()), ["a", "b"])
        spans = exporter.get_finished_spans()
        self.assertEqual(len(spans), 1)
        self.assertEqual(spans[0].attributes.get("return"), '["a", "b"]')


if __name__ == '__main__':
    unittest.main()
