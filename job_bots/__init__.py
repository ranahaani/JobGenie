"""
JobGenie - Automated job application bot package.

This package provides a modular framework for automating job applications
across different platforms like Join.com, Greenhouse, and others.
"""

from job_bots.config import ApplicationConfig
from job_bots.factory import JobApplicationBotFactory
from job_bots.base_bot import BaseJobApplicationBot

__all__ = [
    'ApplicationConfig',
    'JobApplicationBotFactory',
    'BaseJobApplicationBot',
] 