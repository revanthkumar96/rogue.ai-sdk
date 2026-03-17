"""Security utilities for Rouge SDK

This module provides security-focused utilities including:
- Input validation for configuration values
- Credential caching with encryption
- Sensitive data detection and sanitization
"""

import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Optional


def validate_service_name(value: str) -> str:
    """Validate service_name format.

    Args:
        value: Service name to validate

    Returns:
        Validated service name

    Raises:
        ValueError: If service name format is invalid
    """
    if not re.match(r'^[a-zA-Z0-9_\-\.]{1,64}$', value):
        raise ValueError(
            "Invalid service_name. Use alphanumeric characters, dash, "
            "underscore, or dot only (max 64 chars)")
    return value


def validate_github_identifier(field_name: str, value: str) -> str:
    """Validate GitHub owner/repo name format.

    Args:
        field_name: Name of the field being validated
        value: Value to validate

    Returns:
        Validated value

    Raises:
        ValueError: If format is invalid
    """
    if not re.match(r'^[a-zA-Z0-9_\-\.]{1,100}$', value):
        raise ValueError(
            f"Invalid {field_name}. Use alphanumeric characters, dash, "
            f"underscore, or dot only (max 100 chars)")
    return value


def validate_commit_hash(value: str) -> str:
    """Validate git commit hash format.

    Args:
        value: Commit hash to validate

    Returns:
        Validated commit hash

    Raises:
        ValueError: If commit hash format is invalid
    """
    if not re.match(r'^[a-f0-9]{7,40}$', value):
        raise ValueError(
            "Invalid git commit hash. Must be 7-40 hexadecimal characters")
    return value


def validate_token(value: str) -> str:
    """Validate API token format.

    Args:
        value: Token to validate

    Returns:
        Validated token

    Raises:
        ValueError: If token format is invalid
    """
    if len(value) < 20 or len(value) > 500:
        raise ValueError(
            "Invalid token length. Must be between 20 and 500 characters")
    return value


def validate_config_value(field: str, value: Any) -> Any:
    """Validate a configuration value based on its field name.

    Args:
        field: Configuration field name
        value: Value to validate

    Returns:
        Validated value

    Raises:
        ValueError: If validation fails
    """
    if not isinstance(value, str):
        # Only validate string fields
        return value

    if field == "service_name":
        return validate_service_name(value)
    elif field in ["github_owner", "github_repo_name"]:
        return validate_github_identifier(field, value)
    elif field == "github_commit_hash":
        return validate_commit_hash(value)
    elif field == "token":
        return validate_token(value)

    return value


class CredentialCache:
    """Encrypted credential caching for Rouge SDK.

    This class provides secure local caching of credentials with encryption
    at rest to reduce dependency on external credential endpoints.
    """

    def __init__(self):
        """Initialize credential cache."""
        self.cache_dir = Path.home() / ".rouge"
        self.cache_file = self.cache_dir / "credentials.enc"
        self._ensure_cache_dir()

    def _ensure_cache_dir(self) -> None:
        """Ensure cache directory exists with proper permissions."""
        if not self.cache_dir.exists():
            self.cache_dir.mkdir(mode=0o700, exist_ok=True)
        else:
            # Ensure directory has secure permissions
            try:
                os.chmod(self.cache_dir, 0o700)
            except Exception:
                # On Windows, chmod may not work as expected
                pass

    def _get_encryption_key(self) -> Optional[bytes]:
        """Get or create encryption key.

        Returns:
            Encryption key bytes, or None if unavailable
        """
        try:
            # Try using cryptography library if available
            from cryptography.fernet import Fernet

            key_file = self.cache_dir / ".key"

            if key_file.exists():
                with open(key_file, 'rb') as f:
                    return f.read()
            else:
                # Generate new key
                key = Fernet.generate_key()
                with open(key_file, 'wb') as f:
                    f.write(key)
                # Secure the key file
                try:
                    os.chmod(key_file, 0o600)
                except Exception:
                    pass
                return key

        except ImportError:
            # Cryptography not available, fall back to simple obfuscation
            # This is not secure encryption, just better than plaintext
            print(
                "[Rouge] Warning: cryptography library not available. "
                "Credential cache will use simple obfuscation only. "
                "Install cryptography for secure encryption: "
                "pip install cryptography",
                file=sys.stderr)
            return None

    def _encrypt_data(self, data: bytes) -> bytes:
        """Encrypt data using Fernet symmetric encryption.

        Args:
            data: Data to encrypt

        Returns:
            Encrypted data
        """
        key = self._get_encryption_key()
        if key is None:
            # Fall back to simple base64 obfuscation
            import base64
            return base64.b64encode(data)

        try:
            from cryptography.fernet import Fernet
            fernet = Fernet(key)
            return fernet.encrypt(data)
        except Exception:
            # Encryption failed, return obfuscated
            import base64
            return base64.b64encode(data)

    def _decrypt_data(self, encrypted_data: bytes) -> Optional[bytes]:
        """Decrypt data using Fernet symmetric encryption.

        Args:
            encrypted_data: Encrypted data

        Returns:
            Decrypted data, or None if decryption fails
        """
        key = self._get_encryption_key()
        if key is None:
            # Fall back to base64 deobfuscation
            try:
                import base64
                return base64.b64decode(encrypted_data)
            except Exception:
                return None

        try:
            from cryptography.fernet import Fernet
            fernet = Fernet(key)
            return fernet.decrypt(encrypted_data)
        except Exception:
            # Try base64 deobfuscation as fallback
            try:
                import base64
                return base64.b64decode(encrypted_data)
            except Exception:
                return None

    def save_credentials(self, credentials: dict) -> bool:
        """Save credentials to encrypted cache.

        Args:
            credentials: Credentials dictionary to cache

        Returns:
            True if save successful, False otherwise
        """
        try:
            # Serialize credentials
            cred_json = json.dumps(credentials).encode('utf-8')

            # Encrypt
            encrypted = self._encrypt_data(cred_json)

            # Write to cache file
            with open(self.cache_file, 'wb') as f:
                f.write(encrypted)

            # Secure the cache file
            try:
                os.chmod(self.cache_file, 0o600)
            except Exception:
                pass

            return True

        except Exception as e:
            print(f"[Rouge] Warning: Failed to cache credentials: {e}",
                  file=sys.stderr)
            return False

    def load_credentials(self) -> Optional[dict]:
        """Load credentials from encrypted cache.

        Returns:
            Credentials dictionary, or None if unavailable or invalid
        """
        if not self.cache_file.exists():
            return None

        try:
            # Read encrypted data
            with open(self.cache_file, 'rb') as f:
                encrypted = f.read()

            # Decrypt
            decrypted = self._decrypt_data(encrypted)
            if decrypted is None:
                return None

            # Deserialize
            credentials = json.loads(decrypted.decode('utf-8'))

            # Validate credential structure
            if not self._validate_credentials(credentials):
                return None

            return credentials

        except Exception as e:
            print(f"[Rouge] Warning: Failed to load cached credentials: {e}",
                  file=sys.stderr)
            return None

    def clear_cache(self) -> bool:
        """Clear cached credentials.

        Returns:
            True if clear successful, False otherwise
        """
        try:
            if self.cache_file.exists():
                self.cache_file.unlink()
            return True
        except Exception:
            return False

    def _validate_credentials(self, credentials: dict) -> bool:
        """Validate credential structure.

        Args:
            credentials: Credentials dictionary to validate

        Returns:
            True if valid, False otherwise
        """
        if not isinstance(credentials, dict):
            return False

        # Check for required fields (adjust based on your credential format)
        required_fields = ['hash', 'region']
        for field in required_fields:
            if field not in credentials:
                return False

        return True

    def is_expired(self, credentials: dict) -> bool:
        """Check if credentials are expired.

        Args:
            credentials: Credentials dictionary

        Returns:
            True if expired, False otherwise
        """
        # Check if credentials have an expiration timestamp
        if 'expires_at' not in credentials:
            # No expiration set, consider valid for 1 hour from cache time
            import time
            cache_mtime = self.cache_file.stat().st_mtime
            return (time.time() - cache_mtime) > 3600

        import time
        return time.time() > credentials.get('expires_at', 0)
