#!/usr/bin/env python3
"""
CAPTCHA Avoidance and Evasion Utilities

This module provides utilities for avoiding and evading CAPTCHA detection
when scraping websites.
"""

import os
import time
import random
import logging
import tempfile
from typing import Dict, Any, Optional, List
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def configure_stealth_browser(options: Options = None) -> Options:
    """Configure a Chrome browser with stealth settings to avoid detection.
    
    Args:
        options: Existing Chrome options to modify (or creates new if None)
        
    Returns:
        Modified Chrome options
    """
    if options is None:
        options = Options()
    
    # Basic options to avoid detection
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    
    # Additional anti-detection measures
    options.add_argument('--disable-extensions')
    options.add_argument('--profile-directory=Default')
    options.add_argument('--incognito')
    options.add_argument('--disable-plugins-discovery')
    options.add_argument('--start-maximized')
    
    # Randomize window size slightly to appear more human
    width = random.randint(1050, 1200)
    height = random.randint(800, 900)
    options.add_argument(f'--window-size={width},{height}')
    
    # Add random timezone
    timezones = [
        'America/New_York', 'America/Chicago', 'America/Denver', 'America/Los_Angeles',
        'Europe/London', 'Europe/Paris', 'Europe/Berlin', 'Europe/Moscow',
        'Asia/Tokyo', 'Asia/Shanghai', 'Asia/Dubai', 'Australia/Sydney'
    ]
    options.add_argument(f'--timezone={random.choice(timezones)}')
    
    # Add random language
    languages = ['en-US', 'en-GB', 'fr', 'es', 'de', 'it']
    options.add_argument(f'--lang={random.choice(languages)}')
    
    return options

def create_stealth_driver(
    proxy: Optional[str] = None,
    headless: bool = True,
    use_tor: bool = False,
    driver_path: Optional[str] = None
) -> webdriver.Chrome:
    """Create a Chrome WebDriver with stealth settings.
    
    Args:
        proxy: Optional proxy server (format: ip:port)
        headless: Whether to run in headless mode
        use_tor: Whether to route through Tor network
        driver_path: Path to ChromeDriver executable
        
    Returns:
        Configured Chrome WebDriver
    """
    options = configure_stealth_browser()
    
    if headless:
        options.add_argument('--headless')
    
    # Add proxy if specified
    if proxy:
        if not proxy.startswith(('http://', 'https://')):
            proxy = f'http://{proxy}'
        options.add_argument(f'--proxy-server={proxy}')
    
    # Use Tor if specified (requires Tor to be running)
    if use_tor:
        options.add_argument('--proxy-server=socks5://127.0.0.1:9050')
    
    # Set up driver path
    if driver_path:
        service = Service(driver_path)
    else:
        service = Service(ChromeDriverManager().install())
    
    # Create driver
    driver = webdriver.Chrome(service=service, options=options)
    
    # Apply additional stealth techniques via JavaScript
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    
    # Apply random scroll behavior
    driver.execute_script("""
    // Random scroll functions to mimic human behavior
    window.randomScrollAmount = function() {
        return Math.floor(Math.random() * 100) + 50;
    };
    
    window.randomScrollDelay = function() {
        return Math.floor(Math.random() * 500) + 500;
    };
    """)
    
    # Set custom navigator properties
    driver.execute_script("""
    // Randomize navigator properties
    const platforms = ['Win32', 'MacIntel', 'Linux x86_64'];
    const vendors = ['Google Inc.', 'Apple Computer, Inc.', ''];
    
    Object.defineProperty(navigator, 'platform', {get: () => platforms[Math.floor(Math.random() * platforms.length)]});
    Object.defineProperty(navigator, 'vendor', {get: () => vendors[Math.floor(Math.random() * vendors.length)]});
    """)
    
    return driver

def simulate_human_behavior(driver: webdriver.Chrome, min_duration: int = 5, max_duration: int = 15) -> None:
    """Simulate human browsing behavior to avoid detection.
    
    Args:
        driver: Chrome WebDriver instance
        min_duration: Minimum duration in seconds
        max_duration: Maximum duration in seconds
    """
    # Random duration for browsing simulation
    duration = random.randint(min_duration, max_duration)
    end_time = time.time() + duration
    
    # Get scroll height
    scroll_height = driver.execute_script("return document.body.scrollHeight")
    
    while time.time() < end_time:
        # Random scroll
        scroll_amount = random.randint(100, 300)
        current_position = driver.execute_script("return window.pageYOffset")
        
        # Scroll down with randomness
        new_position = min(current_position + scroll_amount, scroll_height - 800)
        driver.execute_script(f"window.scrollTo(0, {new_position})")
        
        # Random delay
        time.sleep(random.uniform(0.5, 2.0))
        
        # Occasional scroll up
        if random.random() < 0.3:
            up_amount = random.randint(50, 200)
            new_position = max(current_position - up_amount, 0)
            driver.execute_script(f"window.scrollTo(0, {new_position})")
            time.sleep(random.uniform(0.5, 1.5))
        
        # Randomly hover over elements
        if random.random() < 0.2:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, 'a, button, input, img')
                if elements:
                    elem = random.choice(elements)
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", elem)
                    time.sleep(random.uniform(0.5, 1.0))
            except Exception:
                pass

def rotate_user_agent(driver: webdriver.Chrome) -> None:
    """Rotate the User-Agent of the browser.
    
    Args:
        driver: Chrome WebDriver instance
    """
    # Common User-Agent strings
    user_agents = [
        # Chrome on Windows
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/97.0.4692.71 Safari/537.36',
        # Chrome on Mac
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/97.0.4692.71 Safari/537.36',
        # Firefox on Windows
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:96.0) Gecko/20100101 Firefox/96.0',
        # Firefox on Mac
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:96.0) Gecko/20100101 Firefox/96.0',
        # Safari on Mac
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.2 Safari/605.1.15',
        # Edge on Windows
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/97.0.4692.71 Safari/537.36 Edg/97.0.1072.62'
    ]
    
    # Select a random User-Agent
    ua = random.choice(user_agents)
    
    # Apply it via CDP
    driver.execute_cdp_cmd('Network.setUserAgentOverride', {"userAgent": ua})
    logger.info(f"Rotated User-Agent to: {ua}")

def rotate_ip_with_proxy_list(driver: webdriver.Chrome, proxy_list: List[str]) -> str:
    """Rotate the IP address using a list of proxies.
    
    Args:
        driver: Chrome WebDriver instance
        proxy_list: List of proxy URLs
        
    Returns:
        The selected proxy URL
    """
    if not proxy_list:
        logger.warning("No proxies available for rotation")
        return ""
    
    # Choose a random proxy
    proxy = random.choice(proxy_list)
    
    # Close the current browser
    driver.quit()
    
    # Configure new options
    options = configure_stealth_browser()
    
    # Set the new proxy
    if not proxy.startswith(('http://', 'https://')):
        proxy = f'http://{proxy}'
    options.add_argument(f'--proxy-server={proxy}')
    
    # Create a new driver
    new_driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    
    # Replace the old driver with the new one
    driver = new_driver
    
    logger.info(f"Rotated IP using proxy: {proxy}")
    return proxy

def detect_captcha(driver: webdriver.Chrome) -> bool:
    """Detect if a CAPTCHA is present on the page.
    
    Args:
        driver: Chrome WebDriver instance
        
    Returns:
        True if CAPTCHA is detected
    """
    # Common CAPTCHA indicators in page content
    content_indicators = [
        'captcha',
        'robot',
        'human verification',
        'security check',
        'unusual traffic',
        'automated queries',
    ]
    
    # Common CAPTCHA element selectors
    element_selectors = [
        'iframe[src*="recaptcha"]',
        'iframe[src*="captcha"]',
        'div.g-recaptcha',
        'div.h-captcha',
        'form[action*="validateCaptcha"]',
        'div[class*="captcha"]',
        'input[name*="captcha"]',
        'img[alt*="captcha" i]',
    ]
    
    # Check page content
    page_text = driver.page_source.lower()
    for indicator in content_indicators:
        if indicator in page_text:
            logger.warning(f"CAPTCHA detected: Content contains '{indicator}'")
            return True
    
    # Check for CAPTCHA elements
    for selector in element_selectors:
        try:
            elements = driver.find_elements(By.CSS_SELECTOR, selector)
            if elements:
                logger.warning(f"CAPTCHA detected: Found element matching '{selector}'")
                return True
        except Exception:
            pass
    
    # Check page title for indicators
    title = driver.title.lower()
    captcha_title_indicators = ['captcha', 'security check', 'verify']
    for indicator in captcha_title_indicators:
        if indicator in title:
            logger.warning(f"CAPTCHA detected: Title contains '{indicator}'")
            return True
    
    # Check URL for redirects to CAPTCHA pages
    current_url = driver.current_url.lower()
    captcha_url_indicators = ['captcha', 'security', 'challenge', 'verify']
    for indicator in captcha_url_indicators:
        if indicator in current_url:
            logger.warning(f"CAPTCHA detected: URL contains '{indicator}'")
            return True
    
    return False

def save_cookies(driver: webdriver.Chrome, filename: str = 'cookies.json') -> None:
    """Save cookies from the browser session.
    
    Args:
        driver: Chrome WebDriver instance
        filename: File to save cookies to
    """
    import json
    
    cookies = driver.get_cookies()
    with open(filename, 'w') as f:
        json.dump(cookies, f, indent=2)
    
    logger.info(f"Saved {len(cookies)} cookies to {filename}")

def load_cookies(driver: webdriver.Chrome, filename: str = 'cookies.json') -> bool:
    """Load cookies into the browser session.
    
    Args:
        driver: Chrome WebDriver instance
        filename: File to load cookies from
        
    Returns:
        True if cookies were loaded successfully
    """
    import json
    
    try:
        with open(filename, 'r') as f:
            cookies = json.load(f)
            
        for cookie in cookies:
            # Handle sameSite compatibility
            if 'sameSite' in cookie and cookie['sameSite'] not in ['Strict', 'Lax', 'None']:
                cookie['sameSite'] = 'Lax'
            
            driver.add_cookie(cookie)
            
        logger.info(f"Loaded {len(cookies)} cookies from {filename}")
        return True
    except Exception as e:
        logger.error(f"Error loading cookies: {e}")
        return False

if __name__ == "__main__":
    # Example usage
    logger.info("Creating stealth browser...")
    driver = create_stealth_driver(headless=False)
    
    try:
        # Test with a Google search
        logger.info("Navigating to Google...")
        driver.get("https://www.google.com")
        
        # Simulate human behavior
        logger.info("Simulating human behavior...")
        simulate_human_behavior(driver, min_duration=5, max_duration=10)
        
        # Check for CAPTCHA
        if detect_captcha(driver):
            logger.warning("CAPTCHA detected during testing")
        else:
            logger.info("No CAPTCHA detected")
            
        # Search for something
        logger.info("Performing search...")
        try:
            search_box = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.NAME, "q"))
            )
            search_box.send_keys("python web scraping")
            search_box.submit()
            
            # Wait for results
            time.sleep(3)
            
            # Save cookies
            save_cookies(driver)
            
            # Check again for CAPTCHA
            if detect_captcha(driver):
                logger.warning("CAPTCHA detected after search")
            else:
                logger.info("Search completed without CAPTCHA")
                
        except TimeoutException:
            logger.error("Timed out waiting for search box")
            
    finally:
        # Clean up
        driver.quit()
        logger.info("Test completed") 