"""
Synthetic Account Authentication and User Repository.

Provides an isolated in-memory test repository for verifying logins:
- Zero dependency on external databases.
- Supports valid credentials, bad passwords, unknown users, and banned accounts.
- BigWorld login status codes consistent with client disassembly.
"""

from dataclasses import dataclass
from enum import IntEnum
from typing import Dict, Optional
import hashlib
import os


class LoginStatus(IntEnum):
    """BigWorld Login Status Codes (Client VA 0x1008a844c)."""
    SUCCESS = 0x01
    BAD_PASSWORD = 0x02
    NOT_FOUND = 0x03
    BANNED = 0x04
    ALREADY_LOGGED_IN = 0x05
    VERSION_MISMATCH = 0x06
    MALFORMED_REQUEST = 0x07


@dataclass
class AuthResult:
    """Outcome of an authentication attempt."""
    status: LoginStatus
    error_message: str
    account_id: Optional[int] = None
    username: Optional[str] = None


@dataclass
class TestAccount:
    """Represents a synthetic user account."""
    account_id: int
    username: str
    password_hash: str
    salt: str
    is_banned: bool = False
    diamonds: int = 1000
    gold: int = 50000


class InMemoryAccountRepository:
    """Manages synthetic test accounts in memory."""

    def __init__(self):
        self._accounts: Dict[str, TestAccount] = {}
        self._seed_default_accounts()

    def _hash_password(self, password: str, salt: str) -> str:
        """Computes SHA-256 hash with cryptographic salt."""
        h = hashlib.sha256()
        h.update(salt.encode('utf-8'))
        h.update(password.encode('utf-8'))
        return h.hexdigest()

    def add_account(self, account_id: int, username: str, password: str, is_banned: bool = False):
        """Adds a test account to the in-memory repository."""
        salt = os.urandom(16).hex()
        password_hash = self._hash_password(password, salt)
        self._accounts[username.lower()] = TestAccount(
            account_id=account_id,
            username=username,
            password_hash=password_hash,
            salt=salt,
            is_banned=is_banned
        )

    def _seed_default_accounts(self):
        """Prepopulates repository with standard synthetic test fixtures."""
        self.add_account(1001, "test_user_1", "password123")
        self.add_account(1002, "test_user_2", "secure_pass_456")
        self.add_account(1003, "banned_user", "banned_pass", is_banned=True)

    def authenticate(self, username: str, plain_password: str) -> AuthResult:
        """
        Validates username and plain password against stored records.
        """
        account = self._accounts.get(username.lower())
        if not account:
            return AuthResult(
                status=LoginStatus.NOT_FOUND,
                error_message="Account does not exist.",
                username=username
            )

        if account.is_banned:
            return AuthResult(
                status=LoginStatus.BANNED,
                error_message="Account has been suspended.",
                account_id=account.account_id,
                username=username
            )

        expected_hash = self._hash_password(plain_password, account.salt)
        if expected_hash != account.password_hash:
            return AuthResult(
                status=LoginStatus.BAD_PASSWORD,
                error_message="Incorrect password.",
                account_id=account.account_id,
                username=username
            )

        return AuthResult(
            status=LoginStatus.SUCCESS,
            error_message="",
            account_id=account.account_id,
            username=username
        )
