from __future__ import annotations

import hashlib
import os
import threading
from typing import Optional

from database.repository import Repository
from core.logger import logger

class PINManager:
    def __init__(self, repo: Repository) -> None:
        self._repo = repo
        self._lock = threading.Lock()

    def _hash_pin(self, pin: str, salt: bytes) -> bytes:
        return hashlib.pbkdf2_hmac(
            'sha256',
            pin.encode('utf-8'),
            salt,
            100000
        )

    def is_enabled(self) -> bool:
        """Check if PIN protection is enabled."""
        return bool(self._repo.get_setting("pin_hash"))

    def set_pin(self, pin: str) -> bool:
        """Set or update the PIN. Must be 4-8 digits."""
        if not pin.isdigit() or not (4 <= len(pin) <= 8):
            return False
            
        salt = os.urandom(16)
        hashed = self._hash_pin(pin, salt)
        
        with self._lock:
            self._repo.set_setting("pin_salt", salt.hex())
            self._repo.set_setting("pin_hash", hashed.hex())
            logger.info("PIN updated successfully")
            return True

    def disable_pin(self) -> None:
        """Remove the PIN."""
        with self._lock:
            self._repo.set_setting("pin_salt", "")
            self._repo.set_setting("pin_hash", "")
            logger.info("PIN disabled")

    def verify_pin(self, pin: str) -> bool:
        """Verify the given PIN against the stored hash."""
        if not self.is_enabled():
            return True # If no PIN is set, verification passes
            
        with self._lock:
            salt_hex = self._repo.get_setting("pin_salt")
            hash_hex = self._repo.get_setting("pin_hash")
            
            if not salt_hex or not hash_hex:
                return False
                
            try:
                salt = bytes.fromhex(salt_hex)
                expected_hash = bytes.fromhex(hash_hex)
                actual_hash = self._hash_pin(pin, salt)
                return actual_hash == expected_hash
            except ValueError:
                logger.error("Failed to decode PIN salt/hash")
                return False
