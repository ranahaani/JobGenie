#!/usr/bin/env python3
"""
JobGenie - Automated job application bot for multiple platforms.

This script automates job applications across different platforms like
Join.com, Greenhouse, and others. It searches for jobs, extracts job details,
generates cover letters, and submits applications.
"""

import logging
import os
from typing import Dict, List

from webdriver_manager.chrome import ChromeDriverManager

from job_bots.config import ApplicationConfig, PlatformConfig
from job_bots.factory import JobApplicationBotFactory
from job_bots.utils import load_search_queries
from google_job_scraper import GoogleSearchScraper

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("application.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def collect_job_urls(search_query_data: List[Dict[str, str]]) -> List[str]:
    """Collect job URLs from search queries.

    Args:
        search_query_data: List of search query dictionaries

    Returns:
        List of job URLs
    """
    all_job_urls = []

    # Collect all job URLs using the CAPTCHA-resistant scraper
    logger.info("Collecting job URLs using CAPTCHA-resistant scraper...")
    for query_data in search_query_data:
        query = query_data.get("query")
        site_filter = query_data.get("site_filter", "join.com")

        try:
            # Use standalone scraper
            scraper = GoogleSearchScraper()
            job_urls = scraper.search(
                query=query,
                domain_filter=site_filter,
                num_pages=3
            )

            logger.info(f"Found {len(job_urls)} jobs for query: {query}")
            all_job_urls.extend(job_urls)
        except Exception as e:
            logger.error(f"Error processing query {query}: {e}")

    # Remove duplicates
    all_job_urls = list(dict.fromkeys(all_job_urls))
    logger.info(f"Found total of {len(all_job_urls)} unique job URLs")

    return all_job_urls


def main():
    """Main entry point for the job application bot."""
    # Load search queries
    search_query_data = load_search_queries()

    try:
        # Load application configuration
        config = ApplicationConfig.from_file('config.json')

        # Collect job URLs to apply to
        all_job_urls = collect_job_urls(search_query_data)

        # Proceed only if we have job URLs to apply to
        if all_job_urls:
            # Load platform configurations
            platform_configs = PlatformConfig.load_all_platforms()

            # Group URLs by platform for more efficient processing
            grouped_urls = JobApplicationBotFactory.group_urls_by_platform(all_job_urls)

            # Process each platform's URLs with the appropriate bot
            driver_path = ChromeDriverManager().install()

            for platform, platform_urls in grouped_urls.items():
                if not platform_urls:
                    continue

                logger.info(f"Processing {len(platform_urls)} URLs for platform {platform}")

                # Create the appropriate bot for this platform
                with JobApplicationBotFactory.create_bot(
                        platform=platform,
                        driver_path=driver_path,
                        platform_configs=platform_configs
                ) as bot:
                    bot.login_and_apply_to_jobs(platform_urls, config)
        else:
            logger.warning("No job URLs found to apply to")

    except Exception as e:
        logger.error(f"Application error: {e}")


if __name__ == "__main__":
    main() 
