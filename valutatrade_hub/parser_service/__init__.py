"""
Parser Service для ValutaTrade Hub
"""

from .config import config
from .updater import RatesUpdater

__all__ = ["RatesUpdater", "config"]
