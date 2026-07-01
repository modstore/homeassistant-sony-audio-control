"""Exceptions for the Sony Audio Control client."""
from __future__ import annotations


class SonyAudioError(Exception):
    """Base exception for Sony Audio Control."""


class SonyAudioConnectionError(SonyAudioError):
    """Raised when the Sony device cannot be reached."""


class SonyAudioApiError(SonyAudioError):
    """Raised when the Sony device returns an API error."""

    def __init__(self, message: str, *, error: object | None = None) -> None:
        super().__init__(message)
        self.error = error
