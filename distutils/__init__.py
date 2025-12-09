# Minimal distutils shim to satisfy third-party imports when real distutils is unavailable.
# This is NOT a full implementation — only what common packages expect at import time.
from . import version, spawn
__all__ = ['version', 'spawn']
