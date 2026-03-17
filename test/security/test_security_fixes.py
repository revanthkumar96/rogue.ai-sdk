"""Tests for Phase 1 security fixes"""

import os
import unittest
from unittest.mock import MagicMock, patch

from rouge.config import RougeConfig
from rouge.integrations.fastapi import sanitize_headers, _sanitize_body
from rouge.logger import SensitiveDataFilter
from rouge.utils.security import (
    CredentialCache,
    validate_commit_hash,
    validate_config_value,
    validate_github_identifier,
    validate_service_name,
    validate_token,
)


class TestConfigSecurity(unittest.TestCase):
    """Test configuration security fixes"""

    def test_https_endpoint_required(self):
        """Test that HTTP endpoints are rejected by default"""
        with self.assertRaises(ValueError) as context:
            config = RougeConfig(
                service_name="test-service",
                github_owner="test-owner",
                github_repo_name="test-repo",
                github_commit_hash="abc1234",
                otlp_endpoint="http://example.com/traces"
            )

        self.assertIn("Insecure HTTP endpoint", str(context.exception))

    def test_https_endpoint_allowed(self):
        """Test that HTTPS endpoints are accepted"""
        config = RougeConfig(
            service_name="test-service",
            github_owner="test-owner",
            github_repo_name="test-repo",
            github_commit_hash="abc1234",
            otlp_endpoint="https://example.com/traces"
        )
        self.assertEqual(config.otlp_endpoint, "https://example.com/traces")

    def test_localhost_http_allowed(self):
        """Test that HTTP is allowed for localhost"""
        config = RougeConfig(
            service_name="test-service",
            github_owner="test-owner",
            github_repo_name="test-repo",
            github_commit_hash="abc1234",
            otlp_endpoint="http://localhost:4318/traces"
        )
        self.assertEqual(config.otlp_endpoint, "http://localhost:4318/traces")

    def test_http_allowed_with_flag(self):
        """Test that HTTP can be explicitly allowed"""
        config = RougeConfig(
            service_name="test-service",
            github_owner="test-owner",
            github_repo_name="test-repo",
            github_commit_hash="abc1234",
            otlp_endpoint="http://example.com/traces",
            allow_insecure_transport=True
        )
        self.assertEqual(config.otlp_endpoint, "http://example.com/traces")

    def test_metadata_endpoint_blocked(self):
        """Test that metadata endpoints are blocked"""
        with self.assertRaises(ValueError) as context:
            config = RougeConfig(
                service_name="test-service",
                github_owner="test-owner",
                github_repo_name="test-repo",
                github_commit_hash="abc1234",
                otlp_endpoint="http://169.254.169.254/latest/meta-data",
                allow_insecure_transport=True
            )

        self.assertIn("Metadata endpoint not allowed", str(context.exception))

    def test_body_logging_disabled_by_default(self):
        """Test that body logging is disabled by default"""
        config = RougeConfig(
            service_name="test-service",
            github_owner="test-owner",
            github_repo_name="test-repo",
            github_commit_hash="abc1234"
        )
        self.assertFalse(config.log_response_bodies)
        self.assertFalse(config.log_request_bodies)

    def test_sanitization_enabled_by_default(self):
        """Test that data sanitization is enabled by default"""
        config = RougeConfig(
            service_name="test-service",
            github_owner="test-owner",
            github_repo_name="test-repo",
            github_commit_hash="abc1234"
        )
        self.assertTrue(config.sanitize_telemetry_data)


class TestInputValidation(unittest.TestCase):
    """Test input validation functions"""

    def test_validate_service_name_valid(self):
        """Test valid service names"""
        valid_names = [
            "my-service",
            "my_service",
            "my.service",
            "MyService123",
            "service-1.2.3",
        ]
        for name in valid_names:
            result = validate_service_name(name)
            self.assertEqual(result, name)

    def test_validate_service_name_invalid(self):
        """Test invalid service names"""
        invalid_names = [
            "",  # Empty
            "a" * 65,  # Too long
            "my service",  # Space
            "my@service",  # Special char
            "my/service",  # Slash
        ]
        for name in invalid_names:
            with self.assertRaises(ValueError):
                validate_service_name(name)

    def test_validate_github_identifier_valid(self):
        """Test valid GitHub identifiers"""
        valid_ids = ["owner", "my-org", "my_org", "org.name"]
        for id_val in valid_ids:
            result = validate_github_identifier("github_owner", id_val)
            self.assertEqual(result, id_val)

    def test_validate_commit_hash_valid(self):
        """Test valid commit hashes"""
        valid_hashes = [
            "abc1234",  # Short
            "abc1234567890abcdef1234567890abcdef1234",  # Full
        ]
        for hash_val in valid_hashes:
            result = validate_commit_hash(hash_val)
            self.assertEqual(result, hash_val)

    def test_validate_commit_hash_invalid(self):
        """Test invalid commit hashes"""
        invalid_hashes = [
            "abc123",  # Too short
            "xyz1234",  # Invalid chars
            "ABC1234",  # Uppercase
        ]
        for hash_val in invalid_hashes:
            with self.assertRaises(ValueError):
                validate_commit_hash(hash_val)

    def test_validate_token_valid(self):
        """Test valid tokens"""
        valid_token = "a" * 20  # 20 chars
        result = validate_token(valid_token)
        self.assertEqual(result, valid_token)

    def test_validate_token_invalid(self):
        """Test invalid tokens"""
        with self.assertRaises(ValueError):
            validate_token("short")  # Too short

        with self.assertRaises(ValueError):
            validate_token("a" * 501)  # Too long


class TestHeaderSanitization(unittest.TestCase):
    """Test header sanitization"""

    def test_sensitive_headers_redacted(self):
        """Test that sensitive headers are redacted"""
        headers = [
            (b'authorization', b'Bearer secret-token'),
            (b'x-api-key', b'api-key-12345'),
            (b'cookie', b'session=abc123'),
        ]

        sanitized = sanitize_headers(headers)

        self.assertEqual(
            sanitized['http.header.authorization'], '***REDACTED***'
        )
        self.assertEqual(sanitized['http.header.x-api-key'], '***REDACTED***')
        self.assertEqual(sanitized['http.header.cookie'], '***REDACTED***')

    def test_safe_headers_preserved(self):
        """Test that safe headers are preserved"""
        headers = [
            (b'content-type', b'application/json'),
            (b'user-agent', b'Mozilla/5.0'),
        ]

        sanitized = sanitize_headers(headers)

        self.assertEqual(
            sanitized['http.header.content-type'], 'application/json'
        )
        self.assertEqual(sanitized['http.header.user-agent'], 'Mozilla/5.0')

    def test_unknown_headers_dropped(self):
        """Test that unknown headers are silently dropped"""
        headers = [
            (b'x-custom-header', b'custom-value'),
            (b'x-unknown', b'unknown-value'),
        ]

        sanitized = sanitize_headers(headers)

        # Unknown headers should not be in output
        self.assertNotIn('http.header.x-custom-header', sanitized)
        self.assertNotIn('http.header.x-unknown', sanitized)


class TestBodySanitization(unittest.TestCase):
    """Test body sanitization"""

    def test_email_redaction(self):
        """Test email address redaction"""
        body = '{"user": "john@example.com", "email": "jane.doe@company.org"}'
        sanitized = _sanitize_body(body)

        self.assertNotIn('john@example.com', sanitized)
        self.assertNotIn('jane.doe@company.org', sanitized)
        self.assertIn('[EMAIL]', sanitized)

    def test_ssn_redaction(self):
        """Test SSN redaction"""
        body = '{"ssn": "123-45-6789"}'
        sanitized = _sanitize_body(body)

        self.assertNotIn('123-45-6789', sanitized)
        self.assertIn('[SSN]', sanitized)

    def test_credit_card_redaction(self):
        """Test credit card redaction"""
        body = '{"card": "4532-1234-5678-9010"}'
        sanitized = _sanitize_body(body)

        self.assertNotIn('4532-1234-5678-9010', sanitized)
        self.assertIn('[CARD]', sanitized)

    def test_phone_redaction(self):
        """Test phone number redaction"""
        body = '{"phone": "555-123-4567"}'
        sanitized = _sanitize_body(body)

        self.assertNotIn('555-123-4567', sanitized)
        self.assertIn('[PHONE]', sanitized)

    def test_password_field_redaction(self):
        """Test password field redaction"""
        body = '{"username": "john", "password": "secretpass123"}'
        sanitized = _sanitize_body(body)

        self.assertNotIn('secretpass123', sanitized)
        self.assertIn('"password":"***"', sanitized)

    def test_token_field_redaction(self):
        """Test token field redaction"""
        body = '{"token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"}'
        sanitized = _sanitize_body(body)

        self.assertNotIn('eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9', sanitized)
        self.assertIn('"token":"***"', sanitized)


class TestLoggerSensitiveDataFilter(unittest.TestCase):
    """Test logger sensitive data filter"""

    def test_aws_credentials_redacted(self):
        """Test AWS credentials are redacted from logs"""
        import logging

        filter_obj = SensitiveDataFilter()

        # Create a test log record
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="AWS credentials: aws_access_key_id=AKIAIOSFODNN7EXAMPLE",
            args=(),
            exc_info=None
        )

        # Apply filter
        filter_obj.filter(record)

        # Check that credential is redacted
        self.assertNotIn('AKIAIOSFODNN7EXAMPLE', record.msg)
        self.assertIn('***REDACTED***', record.msg)

    def test_api_keys_redacted(self):
        """Test API keys are redacted from logs"""
        import logging

        filter_obj = SensitiveDataFilter()

        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="API key: sk-1234567890abcdef1234567890abcdef12345678901234",
            args=(),
            exc_info=None
        )

        filter_obj.filter(record)

        self.assertNotIn('sk-1234567890abcdef', record.msg)
        self.assertIn('***REDACTED***', record.msg)


class TestCredentialCache(unittest.TestCase):
    """Test credential caching"""

    def setUp(self):
        """Set up test fixtures"""
        self.cache = CredentialCache()
        self.test_credentials = {
            'hash': 'test-hash-123',
            'region': 'us-west-2',
            'aws_access_key_id': 'AKIAIOSFODNN7EXAMPLE',
            'aws_secret_access_key': 'wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY',
            'aws_session_token': 'session-token-example',
        }

    def tearDown(self):
        """Clean up after tests"""
        self.cache.clear_cache()

    def test_save_and_load_credentials(self):
        """Test saving and loading credentials"""
        # Save credentials
        success = self.cache.save_credentials(self.test_credentials)
        self.assertTrue(success)

        # Load credentials
        loaded = self.cache.load_credentials()
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded['hash'], self.test_credentials['hash'])
        self.assertEqual(loaded['region'], self.test_credentials['region'])

    def test_load_nonexistent_cache(self):
        """Test loading when cache doesn't exist"""
        self.cache.clear_cache()
        loaded = self.cache.load_credentials()
        self.assertIsNone(loaded)

    def test_cache_file_permissions(self):
        """Test that cache file has secure permissions"""
        self.cache.save_credentials(self.test_credentials)

        # Check file exists
        self.assertTrue(self.cache.cache_file.exists())

        # On Unix systems, check permissions
        if os.name != 'nt':  # Not Windows
            import stat
            file_stat = self.cache.cache_file.stat()
            # Should be readable/writable by owner only (0o600)
            mode = stat.S_IMODE(file_stat.st_mode)
            self.assertEqual(mode, 0o600)

    def test_credential_validation(self):
        """Test credential structure validation"""
        # Valid credentials
        valid = {'hash': 'test', 'region': 'us-east-1'}
        self.assertTrue(self.cache._validate_credentials(valid))

        # Invalid credentials (missing required fields)
        invalid1 = {'hash': 'test'}  # Missing region
        self.assertFalse(self.cache._validate_credentials(invalid1))

        invalid2 = "not a dict"
        self.assertFalse(self.cache._validate_credentials(invalid2))


if __name__ == '__main__':
    unittest.main()
