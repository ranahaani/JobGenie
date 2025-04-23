import time
import random
import logging
import urllib.parse
from typing import List, Dict, Optional, Set, Union
import requests
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import WebDriverException
from webdriver_manager.chrome import ChromeDriverManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class GoogleSearchScraper:
    """Scrapes URLs from Google search results with fallback methods."""

    def __init__(self,
                 proxy_list: Optional[List[str]] = None,
                 max_retries: int = 3,
                 headless: bool = True,
                 driver_path: Optional[str] = None):
        """Initialize the scraper with options.
        
        Args:
            proxy_list: List of proxy servers to rotate through
            max_retries: Maximum number of retries for each method
            headless: Whether to run browser in headless mode
            driver_path: Path to ChromeDriver (optional, will download if not provided)
        """
        self.proxy_list = proxy_list or []
        self.max_retries = max_retries
        self.headless = headless
        self.driver_path = driver_path
        self.user_agent = UserAgent(
            fallback='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36')
        self.driver = None
        self.current_proxy_index = 0

    def _get_random_delay(self, min_delay: float = 1.0, max_delay: float = 3.0) -> float:
        """Get a random delay within range to appear more human-like."""
        return random.uniform(min_delay, max_delay)

    def _get_headers(self) -> Dict[str, str]:
        """Generate random headers to avoid detection."""
        return {
            'User-Agent': self.user_agent.random,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'DNT': '1',
        }

    def _get_current_proxy(self) -> Optional[Dict[str, str]]:
        """Get the current proxy from the rotation list."""
        if not self.proxy_list:
            return None

        proxy = self.proxy_list[self.current_proxy_index]
        self.current_proxy_index = (self.current_proxy_index + 1) % len(self.proxy_list)

        return {
            'http': proxy,
            'https': proxy
        }

    def _initialize_selenium(self) -> None:
        """Initialize Selenium WebDriver with anti-detection measures."""
        if self.driver:
            return

        options = Options()
        if self.headless:
            options.add_argument('--headless=new')

        # Anti-detection measures
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_argument(f'--user-agent={self.user_agent.random}')
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)

        # Set proxy if available
        if self.proxy_list:
            proxy = self.proxy_list[self.current_proxy_index].replace('http://', '')
            options.add_argument(f'--proxy-server={proxy}')
            self.current_proxy_index = (self.current_proxy_index + 1) % len(self.proxy_list)

        if self.driver_path:
            service = Service(self.driver_path)
        else:
            service = Service(ChromeDriverManager().install())

        self.driver = webdriver.Chrome(service=service, options=options)

        # Execute CDP commands to mask WebDriver usage
        self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        self.driver.execute_cdp_cmd('Network.setUserAgentOverride', {"userAgent": self.user_agent.random})

    def _quit_selenium(self) -> None:
        """Quit the Selenium WebDriver."""
        if self.driver:
            try:
                self.driver.quit()
            except Exception as e:
                logger.error(f"Error quitting Selenium: {e}")
            finally:
                self.driver = None

    def _detect_captcha(self, content: Union[str, webdriver.Chrome]) -> bool:
        """Detect if CAPTCHA is present in content or selenium driver.
        
        Args:
            content: HTML content as string or Selenium WebDriver instance
            
        Returns:
            True if CAPTCHA is detected
        """
        if isinstance(content, webdriver.Chrome):
            html_content = content.page_source
        else:
            html_content = content

        soup = BeautifulSoup(html_content, 'html.parser')

        # Check for common CAPTCHA indicators
        captcha_indicators = [
            'captcha', 'robot', 'unusual traffic', 'human verification',
            'security check', 'automated queries', 'recaptcha',
            'g-recaptcha', 'captcha-box', 'captcha-container'
        ]

        # Check page text
        page_text = soup.get_text().lower()
        for indicator in captcha_indicators:
            if indicator in page_text:
                logger.warning(f"CAPTCHA detected: Text contains '{indicator}'")
                return True

        # Check for CAPTCHA elements
        for indicator in ['recaptcha', 'captcha']:
            elements = soup.find_all(lambda tag: tag.name and (
                    (tag.has_attr('id') and indicator in tag['id'].lower()) or
                    (tag.has_attr('class') and any(indicator in c.lower() for c in tag['class'])) or
                    (tag.has_attr('name') and indicator in tag['name'].lower())
            ))
            if elements:
                logger.warning(f"CAPTCHA detected: Found {len(elements)} {indicator} elements")
                return True

        # Check for reCAPTCHA iframes
        iframes = soup.find_all('iframe')
        for iframe in iframes:
            src = iframe.get('src', '')
            if 'recaptcha' in src or 'captcha' in src:
                logger.warning(f"CAPTCHA detected: iframe with src containing captcha")
                return True

        return False

    def extract_urls_from_html(self, html_content: str, domain_filter: Optional[str] = None) -> List[str]:
        """Extract URLs from Google search results HTML, enforcing domain-specific patterns.
        
        Args:
            html_content: HTML content from Google search results page
            domain_filter: Optional domain to filter results for
            
        Returns:
            List of URLs
        """
        import re
        extracted_urls = []
        soup = BeautifulSoup(html_content, 'html.parser')

        # Method 1: Standard search result containers
        search_divs = soup.find_all(['div', 'a'], attrs={'class': ['yuRUbf', 'g', 'tF2Cxc']})
        for div in search_divs:
            try:
                a_tag = div if div.name == 'a' else div.find('a')
                if a_tag and a_tag.has_attr('href'):
                    url = a_tag['href']
                    if url.startswith('http'):
                        extracted_urls.append(url)
            except Exception as e:
                logger.debug(f"Error extracting URL from div: {e}")

        # Method 2: Google's redirected URLs and other anchors
        for a_tag in soup.find_all('a', href=True):
            try:
                href = a_tag['href']
                if href.startswith('/url?') and 'url?q=' in href and '/search?q=' not in href:
                    raw = href.split('url?q=')[1].split('&')[0]
                    url = urllib.parse.unquote(raw)
                    extracted_urls.append(url)
                elif href.startswith('http'):
                    extracted_urls.append(href)
            except Exception as e:
                logger.debug(f"Error extracting URL from anchor: {e}")

        # Method 3: Via <cite> tags linking back to actual <a>
        for cite in soup.find_all('cite'):
            try:
                parent = cite
                for _ in range(5):
                    if parent and parent.name == 'a' and parent.has_attr('href'):
                        url = parent['href']
                        if url.startswith('http'):
                            extracted_urls.append(url)
                        break
                    parent = parent.parent
            except Exception as e:
                logger.debug(f"Error extracting URL from citation: {e}")

        # Enforce domain-specific URL patterns
        filtered = []
        if domain_filter and 'join.com' in domain_filter:
            # Pattern: https://join.com/companies/<company>/<id>-<slug>[?query]
            join_re = re.compile(r'^https?://join\.com/companies/[^/]+/\d+[-\w]*(?:\?[\w=&-]+)?$')
            for url in extracted_urls:
                if join_re.match(url):
                    filtered.append(url)
                else:
                    logger.debug(f"Discarding invalid join.com URL: {url}")
        elif domain_filter and 'greenhouse' in domain_filter:
            # Pattern: https://job-boards.greenhouse.io/<org>/jobs/<job_id>[?query]
            gh_re = re.compile(r'^https?://job-boards\.greenhouse\.io/[^/]+/jobs/\d+(?:\?[\w=&-]+)?$')
            for url in extracted_urls:
                if gh_re.match(url):
                    filtered.append(url)
                else:
                    logger.debug(f"Discarding invalid greenhouse URL: {url}")
        else:
            # Generic filter by domain substring if provided
            for url in extracted_urls:
                if not domain_filter or domain_filter in url:
                    filtered.append(url)

        # Deduplicate while preserving order
        unique_urls = []
        seen = set()
        for url in filtered:
            if url not in seen:
                seen.add(url)
                unique_urls.append(url)

        logger.info(f"Extracted {len(unique_urls)} unique URLs from HTML")
        return unique_urls

    def search_with_requests(self, query: str, domain_filter: Optional[str] = None,
                             num_pages: int = 3) -> List[str]:
        """Search Google and extract URLs using the requests library.
        
        Args:
            query: Search query string
            domain_filter: Optional domain to filter results
            num_pages: Number of result pages to search
            
        Returns:
            List of URLs
        """
        all_urls = []

        # Modify query to include site filter if provided
        search_query = query
        if domain_filter and "site:" not in query:
            search_query = f"{query} site:{domain_filter}"

        for page in range(num_pages):
            # Calculate start index for pagination
            start_index = page * 10

            # Prepare search URL
            search_url = f"https://www.google.com/search?q={urllib.parse.quote(search_query)}&start={start_index}&tbs=qdr:w"
            # Add a random delay
            time.sleep(self._get_random_delay())

            # Implement retry mechanism
            for attempt in range(self.max_retries):
                try:
                    # Get proxies and headers
                    headers = self._get_headers()
                    proxies = self._get_current_proxy()

                    logger.info(f"Requesting page {page + 1} with URL: {search_url} (Attempt {attempt + 1})")
                    response = requests.get(
                        search_url,
                        headers=headers,
                        proxies=proxies,
                        timeout=30
                    )

                    # Check if request was successful
                    if response.status_code == 200:
                        # Check for CAPTCHA
                        if self._detect_captcha(response.text):
                            logger.warning(f"CAPTCHA detected on page {page + 1}, trying again")

                            # Longer delay before retry
                            time.sleep(self._get_random_delay(5.0, 10.0))
                            continue

                        # Extract URLs from HTML
                        page_urls = self.extract_urls_from_html(response.text, domain_filter)
                        logger.info(f"Found {len(page_urls)} URLs on page {page + 1}")

                        # Add to overall results
                        all_urls.extend(page_urls)

                        # If this page had no results, we've likely reached the end
                        if not page_urls:
                            logger.info("No URLs found on this page, stopping pagination")
                            break

                        # Success - break retry loop
                        break
                    else:
                        logger.warning(f"Request failed with status code: {response.status_code}")

                        # Wait before retry
                        time.sleep(self._get_random_delay(3.0, 7.0))

                except Exception as e:
                    logger.error(f"Error fetching search results: {e}")

                    # Wait before retry
                    time.sleep(self._get_random_delay(3.0, 7.0))

                # If all retries failed for this page, try switching to Selenium
                if attempt == self.max_retries - 1:
                    logger.warning("All requests attempts failed, stopping requests approach")
                    return all_urls

        return all_urls

    def search_with_selenium(self, query: str, domain_filter: Optional[str] = None,
                             num_pages: int = 3) -> List[str]:
        """Search Google and extract URLs using Selenium WebDriver.
        
        Args:
            query: Search query string
            domain_filter: Optional domain to filter results
            num_pages: Number of result pages to search
            
        Returns:
            List of URLs
        """
        all_urls = []

        # Modify query to include site filter if provided
        search_query = query
        if domain_filter and "site:" not in query:
            search_query = f"{query} site:{domain_filter}"

        try:
            # Initialize Selenium
            self._initialize_selenium()

            for page in range(num_pages):
                # Calculate start index for pagination
                start_index = page * 10

                # Prepare search URL
                search_url = f"https://www.google.com/search?q={urllib.parse.quote(search_query)}&start={start_index}&tbs=qdr:w"
                # Add a random delay between pages
                if page > 0:
                    time.sleep(self._get_random_delay(2.0, 5.0))

                # Implement retry mechanism
                for attempt in range(self.max_retries):
                    try:
                        # Navigate to the search URL
                        logger.info(f"Navigating to page {page + 1} with Selenium (Attempt {attempt + 1})")
                        self.driver.get(search_url)

                        # Wait for page to load
                        time.sleep(self._get_random_delay(2.0, 4.0))

                        # Simulate human-like scrolling
                        self._simulate_scrolling()

                        # Check for CAPTCHA
                        if self._detect_captcha(self.driver):
                            logger.warning(f"CAPTCHA detected on page {page + 1}, trying again")
                            
                            # Restart browser for next attempt
                            self._quit_selenium()
                            time.sleep(self._get_random_delay(5.0, 10.0))
                            self._initialize_selenium()
                            continue

                        # Extract URLs from page source
                        page_urls = self.extract_urls_from_html(self.driver.page_source, domain_filter)
                        logger.info(f"Found {len(page_urls)} URLs on page {page + 1} with Selenium")

                        # Add to overall results
                        all_urls.extend(page_urls)

                        # If this page had no results, we've likely reached the end
                        if not page_urls:
                            logger.info("No URLs found on this page, stopping pagination")
                            break

                        # Success - break retry loop
                        break

                    except WebDriverException as e:
                        logger.error(f"WebDriver error: {e}")

                        # Restart browser for next attempt
                        self._quit_selenium()
                        time.sleep(self._get_random_delay(3.0, 7.0))
                        self._initialize_selenium()

                    # If all retries failed for this page, give up
                    if attempt == self.max_retries - 1:
                        logger.warning("All Selenium attempts failed, stopping Selenium approach")
                        return all_urls

        except Exception as e:
            logger.error(f"Error in Selenium search: {e}")

        finally:
            # Clean up
            self._quit_selenium()

        return all_urls

    def _simulate_scrolling(self):
        """Simulate human-like scrolling behavior."""
        if not self.driver:
            return

        try:
            # Get page height
            page_height = self.driver.execute_script("return document.body.scrollHeight")

            # Scroll down in smaller increments
            current_position = 0
            scroll_step = random.randint(300, 700)  # Random scroll amount

            while current_position < page_height:
                scroll_amount = min(scroll_step, page_height - current_position)
                self.driver.execute_script(f"window.scrollBy(0, {scroll_amount});")
                current_position += scroll_amount

                # Random pause between scrolls
                time.sleep(random.uniform(0.2, 0.7))

            # Scroll back up partially
            self.driver.execute_script(f"window.scrollBy(0, {-random.randint(300, 800)});")
            time.sleep(random.uniform(0.5, 1.0))

        except Exception as e:
            logger.debug(f"Error during scrolling simulation: {e}")

    def search(self, query: str, domain_filter: Optional[str] = None, num_pages: int = 3) -> List[str]:
        """Search Google and return URLs using fallback strategies.
        
        Args:
            query: Search query string
            domain_filter: Optional domain to filter results
            num_pages: Number of result pages to search
            
        Returns:
            List of unique URLs
        """
        logger.info(f"Searching with query: '{query}'{f' and domain filter: {domain_filter}' if domain_filter else ''}")

        # First try with requests (faster and lighter)
        urls = self.search_with_requests(query, domain_filter, num_pages)

        # If requests approach fails or finds few results, try with Selenium
        if len(urls) < 5 and num_pages > 0:
            logger.info(f"Found only {len(urls)} URLs with requests, trying Selenium fallback")
            selenium_urls = self.search_with_selenium(query, domain_filter, num_pages)

            # Merge URL lists, maintaining order but removing duplicates
            seen = set(urls)
            for url in selenium_urls:
                if url not in seen:
                    seen.add(url)
                    urls.append(url)

        # Log stats
        logger.info(f"Search complete, found {len(urls)} unique URLs")
        return urls


# Example usage
if __name__ == "__main__":
    # Initialize the scraper
    scraper = GoogleSearchScraper(
        proxy_list=None,  # Add your proxy list here if needed
        max_retries=3,
        headless=True
    )

    # Search for a query
    search_query = "python developer jobs"
    domain_filter = "join.com"  # Optional domain filter

    # Get search results
    results = scraper.search(
        query=search_query,
        domain_filter=domain_filter,
        num_pages=2
    )

    # Print results
    print(f"\nFound {len(results)} URLs:")
    for i, url in enumerate(results, 1):
        print(f"{i}. {url}")
