"""Tests for rouge_ai initialization behavior"""

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import yaml

import rouge_ai
import rouge_ai.tracer
from rouge_ai import init, shutdown


class TestTracerInitialization(unittest.TestCase):
    """Test rouge_ai initialization with YAML config and init() overrides"""

    def setUp(self):
        """Reset global state before each test"""
        # Reset global state
        rouge_ai.tracer._tracer_provider = None
        rouge_ai.tracer._config = None
        shutdown()

    def tearDown(self):
        """Clean up after each test"""
        shutdown()

    def test_yaml_config_loading_on_import(self):
        """Test that importing rouge_ai loads configuration from YAML file"""
        # Create a temporary YAML config file
        test_config = {
            'service_name': 'test-service-from-yaml',
            'environment': 'test-env',
            'github_owner': 'yaml-owner',
            'github_repo_name': 'yaml-repo',
            'github_commit_hash': 'abc1234yaml'
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / '.rouge_ai-config.yaml'

            # Write test config to YAML file
            with open(config_path, 'w') as f:
                yaml.dump(test_config, f)

            # Mock Path.cwd() to return our temp directory
            with patch('rouge_ai.utils.config.Path.cwd',
                       return_value=Path(temp_dir)):
                # Initialize rouge_ai (this should load the YAML config)
                init()

                # Verify that configuration was loaded from YAML
                self.assertIsNotNone(rouge_ai.tracer._config)
                self.assertEqual(rouge_ai.tracer._config.service_name,
                                 'test-service-from-yaml')
                self.assertEqual(rouge_ai.tracer._config.environment,
                                 'test-env')
                self.assertEqual(rouge_ai.tracer._config.github_owner,
                                 'yaml-owner')
                self.assertEqual(rouge_ai.tracer._config.github_repo_name,
                                 'yaml-repo')
                self.assertEqual(rouge_ai.tracer._config.github_commit_hash,
                                 'abc1234yaml')

    def test_init_overrides_yaml_config(self):
        """Test that rouge_ai.init() parameters override YAML configuration"""
        # Create a temporary YAML config file
        yaml_config = {
            'service_name': 'yaml-service',
            'environment': 'yaml-env',
            'github_owner': 'yaml-owner',
            'github_repo_name': 'yaml-repo',
            'github_commit_hash': 'yamlcommit123',
            'token': 'yaml-token-123',
            'enable_log_cloud_export': True
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / '.rouge_ai-config.yaml'

            # Write YAML config
            with open(config_path, 'w') as f:
                yaml.dump(yaml_config, f)

            # Mock Path.cwd() to return our temp directory
            with patch('rouge_ai.utils.config.Path.cwd',
                       return_value=Path(temp_dir)):
                # Initialize with override parameters
                _ = init(service_name='override-service',
                         environment='override-env',
                         github_commit_hash='overridecommit456',
                         token='override-token-456',
                         enable_log_cloud_export=False)

                # Verify that init() parameters override YAML values
                self.assertIsNotNone(rouge_ai.tracer._config)
                self.assertEqual(rouge_ai.tracer._config.service_name,
                                 'override-service')  # Overridden
                self.assertEqual(rouge_ai.tracer._config.environment,
                                 'override-env')  # Overridden
                self.assertEqual(rouge_ai.tracer._config.github_owner,
                                 'yaml-owner')  # From YAML
                self.assertEqual(rouge_ai.tracer._config.github_repo_name,
                                 'yaml-repo')  # From YAML
                self.assertEqual(rouge_ai.tracer._config.github_commit_hash,
                                 'overridecommit456')  # Overridden
                self.assertEqual(rouge_ai.tracer._config.token,
                                 'override-token-456')  # Overridden
                self.assertEqual(
                    rouge_ai.tracer._config.enable_log_cloud_export,
                    False)  # Overridden

    def test_init_without_yaml_config(self):
        """Test that rouge_ai.init() works without YAML configuration"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Mock Path.cwd() to return temp directory (no YAML file)
            with patch('rouge_ai.utils.config.Path.cwd',
                       return_value=Path(temp_dir)):
                # Initialize with only init() parameters
                _ = init(service_name='init-only-service',
                         environment='init-only-env',
                         github_owner='init-owner',
                         github_repo_name='init-repo',
                         github_commit_hash='initcommit789')

                # Verify that configuration comes from init() parameters only
                self.assertIsNotNone(rouge_ai.tracer._config)
                self.assertEqual(rouge_ai.tracer._config.service_name,
                                 'init-only-service')
                self.assertEqual(rouge_ai.tracer._config.environment,
                                 'init-only-env')
                self.assertEqual(rouge_ai.tracer._config.github_owner,
                                 'init-owner')
                self.assertEqual(rouge_ai.tracer._config.github_repo_name,
                                 'init-repo')
                self.assertEqual(rouge_ai.tracer._config.github_commit_hash,
                                 'initcommit789')

    def test_multiple_init_calls_with_same_params(self):
        """Test that multiple init() calls with same parameters
        return the same tracer provider
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch('rouge_ai.utils.config.Path.cwd',
                       return_value=Path(temp_dir)):
                # First init call
                tracer_provider1 = init(service_name='test-service',
                                        github_owner='test-owner',
                                        github_repo_name='test-repo',
                                        github_commit_hash='testcommit123')

                # Second init call with NO parameters
                # (should return same instance)
                tracer_provider2 = init()

                # Should return the same instance (no kwargs provided)
                self.assertIs(tracer_provider1, tracer_provider2)

                # Configuration should remain from first call
                self.assertEqual(rouge_ai.tracer._config.service_name,
                                 'test-service')

    def test_multiple_init_calls_with_different_params(self):
        """Test that init() with different params updates config in place"""
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch('rouge_ai.utils.config.Path.cwd',
                       return_value=Path(temp_dir)):
                # First init call
                tracer_provider1 = init(service_name='test-service',
                                        github_owner='test-owner',
                                        github_repo_name='test-repo',
                                        github_commit_hash='testcommit123')

                # Second init call with different parameters
                # - should reinitialize
                tracer_provider2 = init(
                    service_name='different-service',
                    github_owner='different-owner',
                    github_repo_name='different-repo',
                    github_commit_hash='differentcommit456')

                # Re-init reuses the same provider (B1: no clobbering of the
                # global); only the configuration is updated.
                self.assertIs(tracer_provider1, tracer_provider2)

                # Configuration should be updated to new values
                self.assertEqual(rouge_ai.tracer._config.service_name,
                                 'different-service')

    def test_reinitialization_with_overrides(self):
        """Test that calling init() again with kwargs
        reinitializes with new config
        """
        yaml_config = {
            'service_name': 'yaml-service',
            'environment': 'yaml-env',
            'github_owner': 'yaml-owner',
            'github_repo_name': 'yaml-repo',
            'github_commit_hash': 'yamlcommit123',
            'token': 'yaml-token',
            'enable_log_cloud_export': True
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / '.rouge_ai-config.yaml'

            # Write YAML config
            with open(config_path, 'w') as f:
                yaml.dump(yaml_config, f)

            # Mock Path.cwd() to return our temp directory
            with patch('rouge_ai.utils.config.Path.cwd',
                       return_value=Path(temp_dir)):
                # First initialization (YAML only)
                tracer_provider1 = init()

                # Verify initial config from YAML
                self.assertIsNotNone(rouge_ai.tracer._config)
                self.assertEqual(rouge_ai.tracer._config.service_name,
                                 'yaml-service')
                self.assertEqual(rouge_ai.tracer._config.token, 'yaml-token')
                self.assertEqual(rouge_ai.tracer._config.environment,
                                 'yaml-env')

                # Second initialization with overrides
                # - this should reinitialize
                tracer_provider2 = init(service_name='reinitialized-service',
                                        token='reinitialized-token',
                                        environment='reinitialized-env')

                # Verify that configuration was updated with overrides
                self.assertIsNotNone(rouge_ai.tracer._config)
                self.assertEqual(rouge_ai.tracer._config.service_name,
                                 'reinitialized-service')  # Overridden
                self.assertEqual(rouge_ai.tracer._config.token,
                                 'reinitialized-token')  # Overridden
                self.assertEqual(rouge_ai.tracer._config.environment,
                                 'reinitialized-env')  # Overridden
                self.assertEqual(rouge_ai.tracer._config.github_owner,
                                 'yaml-owner')  # From YAML

                # Re-init reuses the same provider (B1); config is overridden.
                self.assertIsNotNone(tracer_provider2)
                self.assertIs(tracer_provider1, tracer_provider2)

    def test_reinit_reuses_provider_not_clobbered(self):
        """B1: re-init with new kwargs reuses the provider (no clobber)."""
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch('rouge_ai.utils.config.Path.cwd',
                       return_value=Path(temp_dir)):
                tp1 = init(service_name='svc-a',
                           local_mode=True,
                           enable_span_cloud_export=False,
                           enable_log_cloud_export=False)
                tp2 = init(service_name='svc-b',
                           local_mode=True,
                           enable_span_cloud_export=False,
                           enable_log_cloud_export=False)
                self.assertIs(tp1, tp2)
                self.assertEqual(rouge_ai.tracer._config.service_name, 'svc-b')

    def test_init_does_not_override_existing_provider(self):
        """B1: init() reuses an externally-set provider, not clobbering it."""
        from opentelemetry import trace as otel_trace
        from opentelemetry.sdk.trace import TracerProvider as SDKTracerProvider
        external = SDKTracerProvider()
        otel_trace.set_tracer_provider(external)
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch('rouge_ai.utils.config.Path.cwd',
                       return_value=Path(temp_dir)):
                init(service_name='svc',
                     local_mode=True,
                     enable_span_cloud_export=False,
                     enable_log_cloud_export=False)
        self.assertIs(otel_trace.get_tracer_provider(), external)

    def test_shutdown_resets_to_proxy_not_noop(self):
        """B2: shutdown resets to a Proxy provider so re-init works again."""
        from opentelemetry import trace as otel_trace
        from opentelemetry.trace import ProxyTracerProvider
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch('rouge_ai.utils.config.Path.cwd',
                       return_value=Path(temp_dir)):
                init(service_name='svc',
                     local_mode=True,
                     enable_span_cloud_export=False,
                     enable_log_cloud_export=False)
                shutdown()
                self.assertIsInstance(otel_trace.get_tracer_provider(),
                                      ProxyTracerProvider)
                tp = init(service_name='svc2',
                          local_mode=True,
                          enable_span_cloud_export=False,
                          enable_log_cloud_export=False)
                self.assertIsNotNone(tp)
                self.assertIs(otel_trace.get_tracer_provider(), tp)

    def test_resource_uses_create_with_env_attributes(self):
        """B4/B6: Resource.create adds SDK defaults + OTEL env attrs."""
        env = {"OTEL_RESOURCE_ATTRIBUTES": "custom.tag=xyz"}
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch('rouge_ai.utils.config.Path.cwd',
                       return_value=Path(temp_dir)):
                with patch.dict(os.environ, env):
                    provider = init(service_name='svc',
                                    local_mode=True,
                                    enable_span_cloud_export=False,
                                    enable_log_cloud_export=False)
                    attrs = dict(provider.resource.attributes)
        # telemetry.sdk.name is only added by Resource.create (proves B4).
        self.assertIn("telemetry.sdk.name", attrs)
        self.assertEqual(attrs.get("telemetry.sdk.language"), "python")
        # OTEL_RESOURCE_ATTRIBUTES is merged in (proves B6).
        self.assertEqual(attrs.get("custom.tag"), "xyz")
        self.assertEqual(attrs.get("service.name"), "svc")

    def test_span_exporter_http_for_https_endpoint(self):
        """B5: an https endpoint selects the HTTP/protobuf exporter."""
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import \
            OTLPSpanExporter as HTTPExporter

        from rouge_ai.config import RougeConfig
        from rouge_ai.tracer import _create_span_exporter
        cfg = RougeConfig(service_name='svc',
                          otlp_endpoint='https://example.com:4318/v1/traces')
        self.assertIsInstance(_create_span_exporter(cfg), HTTPExporter)

    def test_span_exporter_grpc_for_grpc_scheme(self):
        """B5: a grpc:// endpoint selects the gRPC exporter."""
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import \
            OTLPSpanExporter as GRPCExporter

        from rouge_ai.config import RougeConfig
        from rouge_ai.tracer import _create_span_exporter
        cfg = RougeConfig(service_name='svc',
                          otlp_endpoint='grpc://localhost:4317',
                          allow_insecure_transport=True)
        self.assertIsInstance(_create_span_exporter(cfg), GRPCExporter)

    def test_span_exporter_protocol_env_override(self):
        """B5/B6: OTEL_EXPORTER_OTLP_PROTOCOL=grpc forces the gRPC exporter."""
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import \
            OTLPSpanExporter as GRPCExporter

        from rouge_ai.config import RougeConfig
        from rouge_ai.tracer import _create_span_exporter
        cfg = RougeConfig(service_name='svc',
                          otlp_endpoint='http://localhost:4318/v1/traces',
                          allow_insecure_transport=True)
        with patch.dict(os.environ, {"OTEL_EXPORTER_OTLP_PROTOCOL": "grpc"}):
            self.assertIsInstance(_create_span_exporter(cfg), GRPCExporter)

    def test_propagators_not_overridden_when_otel_env_set(self):
        """B3: honor OTEL_PROPAGATORS - don't override global propagators."""
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch('rouge_ai.utils.config.Path.cwd',
                       return_value=Path(temp_dir)):
                with patch.dict(os.environ,
                                {"OTEL_PROPAGATORS": "tracecontext"}):
                    with patch('rouge_ai.tracer.set_global_textmap') as m:
                        init(service_name='svc',
                             local_mode=True,
                             enable_span_cloud_export=False,
                             enable_log_cloud_export=False)
                        m.assert_not_called()

    def test_propagators_installed_without_otel_env(self):
        """B3: install W3C propagators when OTEL_PROPAGATORS is unset."""
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch('rouge_ai.utils.config.Path.cwd',
                       return_value=Path(temp_dir)):
                with patch.dict(os.environ):
                    os.environ.pop("OTEL_PROPAGATORS", None)
                    with patch('rouge_ai.tracer.set_global_textmap') as m:
                        init(service_name='svc',
                             local_mode=True,
                             enable_span_cloud_export=False,
                             enable_log_cloud_export=False)
                        m.assert_called_once()

    def test_sampler_ratio_config(self):
        """B7: traces_sampler_ratio installs a ratio-based sampler."""
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch('rouge_ai.utils.config.Path.cwd',
                       return_value=Path(temp_dir)):
                provider = init(service_name='svc',
                                local_mode=True,
                                enable_span_cloud_export=False,
                                enable_log_cloud_export=False,
                                traces_sampler_ratio=0.25)
        self.assertIn("0.25", provider.sampler.get_description())

    def test_otel_traces_sampler_env_honored(self):
        """B6/B7: OTEL_TRACES_SAMPLER is honored when no ratio is set."""
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch('rouge_ai.utils.config.Path.cwd',
                       return_value=Path(temp_dir)):
                with patch.dict(
                        os.environ, {
                            "OTEL_TRACES_SAMPLER": "traceidratio",
                            "OTEL_TRACES_SAMPLER_ARG": "0.1"
                        }):
                    provider = init(service_name='svc',
                                    local_mode=True,
                                    enable_span_cloud_export=False,
                                    enable_log_cloud_export=False)
        self.assertIn("0.1", provider.sampler.get_description())


if __name__ == '__main__':
    unittest.main()
