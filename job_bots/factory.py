"""
Factory for creating job application bots for different platforms.
"""

from pathlib import Path
from typing import List, Dict, Optional
import logging

from job_bots.base_bot import BaseJobApplicationBot
from job_bots.config import PlatformConfig
# The imports below will be used after the platform bots are implemented
# from job_bots.platforms import JoinApplicationBot, GreenhouseApplicationBot

# Configure logging
logger = logging.getLogger(__name__)


class JobApplicationBotFactory:
    """Factory class to create appropriate job application bot based on URL."""
    
    @staticmethod
    def detect_platform(url: str) -> str:
        """Detect the application platform from a job URL.
        
        Args:
            url: Job posting URL
            
        Returns:
            String indicating the platform ('join', 'greenhouse', etc.)
        """
        url_lower = url.lower()
        
        if 'join.com' in url_lower:
            return 'join'
        elif 'boards.greenhouse.io' in url_lower or 'job-boards.greenhouse.io' in url_lower or 'greenhouse.io' in url_lower:
            return 'greenhouse'
        elif 'lever.co' in url_lower or 'jobs.lever.co' in url_lower:
            return 'lever'
        else:
            # Default to join.com for unknown platforms for now
            logger.warning(f"Unknown platform for URL: {url}")
            return
    
    @staticmethod
    def create_bot(platform: str, driver_path: str, platform_configs: Dict[str, PlatformConfig], 
                   cookies_file: Optional[Path] = None) -> BaseJobApplicationBot:
        """Create a job application bot for the specified platform.
        
        Args:
            platform: Platform identifier ('join', 'greenhouse', etc.)
            driver_path: Path to the Chrome driver
            platform_configs: Dictionary of platform configurations
            cookies_file: Path to the cookies file (optional)
            
        Returns:
            Appropriate job application bot instance
        """
        # Handle import here to avoid circular imports
        from job_bots.platforms import JoinApplicationBot, GreenhouseApplicationBot, LeverApplicationBot
        
        # Get the platform configuration
        platform_config = platform_configs.get(platform)
        if not platform_config:
            logger.warning(f"No configuration found for platform: {platform}. Using default.")
            platform_config = PlatformConfig(platform_name=platform)
        
        if platform == 'greenhouse':
            logger.info("Creating Greenhouse application bot")
            return GreenhouseApplicationBot(driver_path, platform_config, cookies_file)
        elif platform == 'lever':
            logger.info("Creating Lever.co application bot")
            return LeverApplicationBot(driver_path, platform_config, cookies_file)
        else:
            # Default to join.com
            logger.info("Creating Join.com application bot")
            return JoinApplicationBot(driver_path, platform_config, cookies_file)
    
    @staticmethod
    def group_urls_by_platform(urls: List[str]) -> Dict[str, List[str]]:
        """Group job URLs by platform for more efficient processing.
        
        Args:
            urls: List of job URLs
            
        Returns:
            Dictionary mapping platform identifiers to lists of URLs
        """
        grouped_urls = {}
        
        for url in urls:
            platform = JobApplicationBotFactory.detect_platform(url)
            if not platform:
                continue
            
            if platform not in grouped_urls:
                grouped_urls[platform] = []
                
            grouped_urls[platform].append(url)
        
        # Log the grouping results
        for platform, platform_urls in grouped_urls.items():
            logger.info(f"Found {len(platform_urls)} URLs for platform: {platform}")
            
        return grouped_urls 
