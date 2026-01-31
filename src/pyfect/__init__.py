"""
pyfect: A Python-native effect system for explicit error handling and structured concurrency.

Core principles:
- Single execution model (sync/async composition)
- Explicit errors as values
- Structured concurrency
- Runtime-first design
- Small, minimal core

Example:
    >>> from pyfect import effect
    >>>
    >>> # Create effects
    >>> eff = effect.succeed(42)
    >>> result = effect.run_sync(eff)
    >>> assert result == 42
"""

from pyfect import effect
from pyfect.pipe import pipe

__version__ = "0.1.0"

__all__ = [
    "__version__",
    "effect",
    "pipe",
]
