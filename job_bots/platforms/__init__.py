"""
Platform-specific job application bot implementations.

This package contains implementations for different job application platforms,
such as Join.com, Greenhouse, and others.
"""

from job_bots.platforms.join_bot import JoinApplicationBot
from job_bots.platforms.greenhouse_bot import GreenhouseApplicationBot

__all__ = [
    'JoinApplicationBot',
    'GreenhouseApplicationBot',
] 