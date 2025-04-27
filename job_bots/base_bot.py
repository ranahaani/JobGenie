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
import undetected_chromedriver as uc
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from webdriver_manager.chrome import ChromeDriverManager
from fake_useragent import UserAgent

from generate_cover_letter import CoverLetterGenerator
from google_job_scraper import GoogleSearchScraper
from proxy_utils import load_proxies_from_file, ProxyFinder
from job_bots.config import ApplicationConfig, PlatformConfig
from browser_stealth import BrowserStealth

# Configure logging
logger = logging.getLogger(__name__)

# Default wait timeout
DEFAULT_TIMEOUT = 10


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
        # self.stealth = BrowserStealth(use_proxy=True)
        self.user_agent = UserAgent(fallback='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
        self.chrome_options = self._configure_chrome_options()
        self.driver: Optional[webdriver.Chrome] = None
        self.wait: Optional[WebDriverWait] = None

    def _configure_chrome_options(self) -> Options:
        """Configure Chrome options for the webdriver with enhanced stealth settings."""
        options = uc.ChromeOptions()

        # Basic anti-detection options
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_argument('--disable-extensions')
        options.add_argument('--disable-infobars')
        options.add_argument('--disable-gpu')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--no-sandbox')
        options.add_argument('--log-level=3')

        # Enhanced privacy settings
        options.add_argument('--disable-notifications')
        options.add_argument('--disable-popup-blocking')
        options.add_argument('--disable-save-password-bubble')

        # Random window size to appear more natural
        width = random.randint(1050, 1200)
        height = random.randint(800, 900)
        options.add_argument(f'--window-size={width},{height}')

        # Add random timezone
        # timezones = [
        #     'America/New_York', 'America/Chicago', 'America/Denver', 'America/Los_Angeles',
        #     'Europe/London', 'Europe/Paris', 'Europe/Berlin', 'Europe/Moscow',
        #     'Asia/Tokyo', 'Asia/Shanghai', 'Asia/Dubai', 'Australia/Sydney'
        # ]
        # options.add_argument(f'--timezone={random.choice(timezones)}')

        # # Add random language
        # languages = ['en-US', 'en-GB', 'fr', 'es', 'de', 'it']
        # options.add_argument(f'--lang={random.choice(languages)}')

        # Set random user agent
        options.add_argument(f'--user-agent={self.user_agent.random}')

        return options

    def __enter__(self):
        """Initialize the driver when entering context."""
        self._initialize_driver()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Quit the driver when exiting context."""
        self._quit_driver()

    def _initialize_driver(self) -> None:
        """Initialize undetectable Chrome with enhanced stealth features."""
        try:
            # Configure Chrome binary path
            chrome_binary = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'
            if not os.path.exists(chrome_binary):
                chrome_binary = None  # Let undetected_chromedriver find Chrome automatically

            # Initialize driver with retry mechanism
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    logger.info(f"Attempting to initialize Chrome driver (attempt {attempt + 1}/{max_retries})")

                    # Create fresh options for each attempt
                    options = self._configure_chrome_options()
                    if chrome_binary:
                        options.binary_location = chrome_binary

                    # Add required arguments for undetected-chromedriver
                    options.add_argument('--no-first-run')
                    options.add_argument('--no-service-autorun')
                    options.add_argument('--password-store=basic')
                    options.add_argument('--no-default-browser-check')

                    # Use undetected_chromedriver
                    self.driver = uc.Chrome(
                        driver_executable_path=None,  # Let it auto-detect
                        options=options,
                        version_main=None,  # Auto-detect Chrome version
                        use_subprocess=True,
                        suppress_welcome=True
                    )

                    # Initialize wait object
                    self.wait = WebDriverWait(self.driver, DEFAULT_TIMEOUT)

                    # Apply additional stealth measures
                    self._apply_advanced_stealth()

                    logger.info("Chrome driver initialized successfully")
                    break

                except Exception as e:
                    logger.warning(f"Attempt {attempt + 1} failed: {str(e)}")
                    if self.driver:
                        try:
                            self.driver.quit()
                        except:
                            pass
                        self.driver = None

                    if attempt < max_retries - 1:
                        time.sleep(random.uniform(1, 3))
                        continue
                    raise Exception(f"Failed to initialize Chrome driver after {max_retries} attempts: {str(e)}")

        except Exception as e:
            logger.error(f"Failed to initialize Chrome driver: {e}")
            raise

    def _apply_advanced_stealth(self) -> None:
        """Apply advanced stealth measures using CDP and JavaScript."""
        if not self.driver:
            return

        # Apply stealth patches
        # self.stealth.apply_stealth_patches(self.driver)

        # Additional CDP commands for enhanced stealth
        self.driver.execute_cdp_cmd('Network.setUserAgentOverride', {
            "userAgent": self.user_agent.random,
            "platform": random.choice(['Windows', 'Linux', 'MacIntel']),
            "mobile": False
        })

        # Modify navigator properties
        self.driver.execute_script("""
            // Override navigator properties
            const originalNavigator = window.navigator;
            const navigatorProxy = new Proxy(originalNavigator, {
                has: (target, key) => true,
                get: (target, key) => {
                    switch (key) {
                        case 'webdriver':
                            return undefined;
                        case 'plugins':
                            // Return a non-empty plugins array
                            return [1, 2, 3, 4, 5].map(() => ({
                                name: Math.random().toString(36),
                                filename: Math.random().toString(36),
                                description: Math.random().toString(36),
                                length: Math.floor(Math.random() * 10)
                            }));
                        default:
                            return target[key];
                    }
                }
            });
            
            // Apply the proxy
            Object.defineProperty(window, 'navigator', {
                value: navigatorProxy,
                writable: false,
                configurable: false
            });
            
            // Add random WebGL noise
            const getParameterProxyHandler = {
                apply: function(target, thisArg, argumentsList) {
                    const param = argumentsList[0];
                    const noise = (Math.random() - 0.5) * 0.01;
                    const result = target.apply(thisArg, argumentsList);
                    
                    if (typeof result === 'number') {
                        return result * (1 + noise);
                    }
                    return result;
                }
            };
            
            if (WebGLRenderingContext.prototype.getParameter) {
                WebGLRenderingContext.prototype.getParameter = new Proxy(
                    WebGLRenderingContext.prototype.getParameter,
                    getParameterProxyHandler
                );
            }
        """)

    def _quit_driver(self) -> None:
        """Quit the Chrome webdriver with proper cleanup."""
        if self.driver:
            try:
                # Clear cookies and local storage
                self.driver.execute_script("window.localStorage.clear();")
                self.driver.delete_all_cookies()

                # Close all windows
                for handle in self.driver.window_handles:
                    self.driver.switch_to.window(handle)
                    self.driver.close()

            except Exception as e:
                logger.warning(f"Error during driver cleanup: {e}")

            finally:
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

    def _simulate_human_interaction(self) -> None:
        """Simulate sophisticated human-like behavior on the page."""
        if not self.driver:
            return

        # Apply base stealth behavior
        # self.stealth.simulate_human_behavior(self.driver)

        # Add natural scrolling behavior
        self.driver.execute_script("""
            function naturalScroll() {
                const maxScroll = Math.max(
                    document.documentElement.scrollHeight,
                    document.body.scrollHeight
                );
                let currentScroll = 0;
                let isScrolling = true;
                
                function easeInOutQuad(t) {
                    return t < 0.5 ? 2 * t * t : -1 + (4 - 2 * t) * t;
                }
                
                function scroll() {
                    if (!isScrolling) return;
                    
                    // Random scroll amount with natural acceleration/deceleration
                    const progress = currentScroll / maxScroll;
                    const step = Math.floor(easeInOutQuad(progress) * (Math.random() * 100 + 50));
                    
                    window.scrollBy(0, step);
                    currentScroll = window.pageYOffset;
                    
                    // Random pauses
                    if (Math.random() < 0.1) {
                        isScrolling = false;
                        setTimeout(() => {
                            isScrolling = true;
                            scroll();
                        }, Math.random() * 1000 + 500);
                    } else {
                        requestAnimationFrame(scroll);
                    }
                }
                
                scroll();
            }
            naturalScroll();
        """)

        # Add realistic mouse movements
        self.driver.execute_script("""
            function simulateMouseMovement() {
                function generateBezierPoints() {
                    const points = [];
                    const numPoints = Math.floor(Math.random() * 10) + 5;
                    
                    for (let i = 0; i < numPoints; i++) {
                        points.push({
                            x: Math.random() * window.innerWidth,
                            y: Math.random() * window.innerHeight,
                            timestamp: Date.now() + (i * (Math.random() * 100 + 50))
                        });
                    }
                    return points;
                }
                
                function bezierCurve(points, t) {
                    if (points.length === 1) return points[0];
                    
                    const newPoints = [];
                    for (let i = 0; i < points.length - 1; i++) {
                        newPoints.push({
                            x: (1 - t) * points[i].x + t * points[i + 1].x,
                            y: (1 - t) * points[i].y + t * points[i + 1].y
                        });
                    }
                    
                    return bezierCurve(newPoints, t);
                }
                
                function moveMouseAlongCurve(points) {
                    let t = 0;
                    
                    function animate() {
                        if (t >= 1) return;
                        
                        t += 0.02;
                        const pos = bezierCurve(points, t);
                        
                        const event = new MouseEvent('mousemove', {
                            view: window,
                            bubbles: true,
                            cancelable: true,
                            clientX: pos.x,
                            clientY: pos.y
                        });
                        
                        document.dispatchEvent(event);
                        requestAnimationFrame(animate);
                    }
                    
                    animate();
                }
                
                // Generate and follow multiple curves
                setInterval(() => {
                    if (Math.random() < 0.3) {
                        moveMouseAlongCurve(generateBezierPoints());
                    }
                }, Math.random() * 2000 + 1000);
            }
            simulateMouseMovement();
        """)

        # Add realistic typing behavior
        self.driver.execute_script("""
            function simulateTypingBehavior() {
                const inputs = document.querySelectorAll('input[type="text"], input[type="email"], textarea');
                
                inputs.forEach(input => {
                    input.addEventListener('focus', function() {
                        const text = this.value;
                        if (!text) return;
                        
                        // Clear and retype with natural delays
                        this.value = '';
                        let i = 0;
                        
                        function typeCharacter() {
                            if (i >= text.length) return;
                            
                            // Random typing speed
                            const delay = Math.random() * 200 + 50;
                            
                            // Occasional typo simulation
                            if (Math.random() < 0.05) {
                                const typo = String.fromCharCode(
                                    text.charCodeAt(i) + (Math.random() < 0.5 ? 1 : -1)
                                );
                                this.value += typo;
                                
                                // Fix typo after a short delay
                                setTimeout(() => {
                                    this.value = this.value.slice(0, -1) + text[i];
                                    i++;
                                    setTimeout(typeCharacter, delay);
                                }, 200);
                            } else {
                                this.value += text[i];
                                i++;
                                setTimeout(typeCharacter, delay);
                            }
                        }
                        
                        typeCharacter();
                    });
                });
            }
            simulateTypingBehavior();
        """)

        # Random delays between actions
        time.sleep(random.uniform(0.5, 2.0))

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
