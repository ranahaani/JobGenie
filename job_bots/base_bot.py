"""
Base bot implementation with common functionality for all platforms.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Any
import json
import logging
import random
import time
import os

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

from generate_cover_letter import CoverLetterGenerator
from google_job_scraper import GoogleSearchScraper
from proxy_utils import load_proxies_from_file, ProxyFinder
from job_bots.config import ApplicationConfig, PlatformConfig

# Configure logging
logger = logging.getLogger(__name__)


class BaseJobApplicationBot(ABC):
    """Abstract base class for job application bots."""

    MAX_RETRIES = 5
    DEFAULT_HR_NAME = "HR Manager"
    RETRY_DELAY = (1, 3)  # Random delay range for retries
    SUBMISSION_DELAY = (10, 20)  # Random delay range after submission

    def __init__(self, 
                 driver_path: str, 
                 platform_config: PlatformConfig,
                 cookies_file: Optional[Path] = None):
        """Initialize the base job application bot.

        Args:
            driver_path: Path to the Chrome driver
            platform_config: Platform-specific configuration
            cookies_file: Path to the cookies file (optional)
        """
        self.driver_path = driver_path
        self.platform_config = platform_config
        
        # Use cookies file from platform config if not explicitly provided
        if cookies_file is None and platform_config.cookies_file:
            cookies_file = platform_config.cookies_file
            
        self.cookies_file = Path(cookies_file) if cookies_file else None
        self.chrome_options = self._configure_chrome_options()
        self.driver: Optional[webdriver.Chrome] = None

    @staticmethod
    def _configure_chrome_options() -> Options:
        """Configure Chrome options for the webdriver."""
        options = Options()
        options.add_argument("--log-level=3")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        return options

    def __enter__(self):
        """Initialize the driver when entering context."""
        self._initialize_driver()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Quit the driver when exiting context."""
        self._quit_driver()

    def _initialize_driver(self) -> None:
        """Initialize the Chrome webdriver."""
        service = Service(self.driver_path)
        self.driver = webdriver.Chrome(service=service, options=self.chrome_options)

    def _quit_driver(self) -> None:
        """Quit the Chrome webdriver."""
        if self.driver:
            self.driver.quit()

    def _random_delay(self, delay_range: Tuple[int, int]) -> None:
        """Implement a random delay within the specified range.

        Args:
            delay_range: Tuple of (min_delay, max_delay) in seconds
        """
        time.sleep(random.uniform(*delay_range))

    def _load_cookies(self) -> None:
        """Load cookies from file and add them to the driver."""
        if not self.cookies_file or not self.cookies_file.exists():
            logger.warning("No cookies file available, skipping cookie loading")
            return

        cookies = json.loads(self.cookies_file.read_text())
        for cookie in cookies:
            if "sameSite" in cookie and cookie["sameSite"] not in ["Strict", "Lax", "None"]:
                cookie["sameSite"] = "Lax"
            self._random_delay((0.5, 1))
            self.driver.add_cookie(cookie)

    def search_jobs(self, query: str, site_filter: str) -> List[str]:
        """Search for job listings on Google.

        Args:
            query: Search query string
            site_filter: Domain to filter results

        Returns:
            List of job URLs
        """
        # Use enhanced GoogleJobScraper with CAPTCHA avoidance
        try:
            # Try to load proxies if available
            proxies = load_proxies_from_file("working_proxies.txt")
            
            # If no proxies found and we're not in headless mode, try to find some
            if not proxies and not os.environ.get('HEADLESS', False):
                logger.info("No proxies found, attempting to find some...")
                finder = ProxyFinder(timeout=10)
                proxies = finder.find_working_proxies(num_proxies=3)
                
            scraper = GoogleSearchScraper(
                proxy_list=proxies,
                use_selenium=True,
                use_stealth=True,
                headless=os.environ.get('HEADLESS', False)
            )
            return scraper.search_jobs(query=query, site_filter=site_filter, pages_to_search=3)
        except Exception as e:
            logger.error(f"Error using advanced scraper: {e}. Falling back to basic scraper.")
            # Fall back to basic scraper if anything goes wrong
            basic_scraper = GoogleSearchScraper(use_selenium=True, use_stealth=False)
            return basic_scraper.search_jobs(query=query, site_filter=site_filter, pages_to_search=3)

    def generate_cover_letter(self, job_title: str, job_description: str, hr_name: str) -> str:
        """Generate a cover letter for the job application.

        Args:
            job_title: Title of the job
            job_description: Description of the job
            hr_name: Name of the HR contact

        Returns:
            Path to the generated cover letter PDF file
        """
        cover_letter_generator = CoverLetterGenerator()
        cover_letter_text = cover_letter_generator.generate_cover_letter(
            job_description, job_title, hr_name
        )
        cover_letter_generator.save_cover_letter_as_pdf(cover_letter_text)
        return str(Path("cover_letter.pdf").absolute())

    @abstractmethod
    def _extract_job_details(self) -> Tuple[str, str, str]:
        """Extract job details from the page.

        Returns:
            Tuple of (job_title, job_description, hr_name)
        """
        pass

    @abstractmethod
    def apply_to_job(self, job_url: str, config: ApplicationConfig) -> bool:
        """Apply to a specific job.

        Args:
            job_url: URL of the job posting
            config: Application configuration

        Returns:
            Boolean indicating if application was successful
        """
        pass

    @abstractmethod
    def login_and_apply_to_jobs(self, job_urls: List[str], config: ApplicationConfig) -> None:
        """Login and apply to multiple jobs.

        Args:
            job_urls: List of job URLs to apply to
            config: Application configuration
        """
        pass 