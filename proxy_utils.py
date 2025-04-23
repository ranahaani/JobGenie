#!/usr/bin/env python3
"""
Proxy Utilities for Google Job Scraper

This module provides utilities for finding and testing proxies
to use with the GoogleJobScraper.
"""

import logging
import requests
import concurrent.futures
import random
import time
from typing import List, Dict, Tuple, Optional
from bs4 import BeautifulSoup
from fake_useragent import UserAgent

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ProxyFinder:
    """Utility class for finding and testing proxies."""
    
    def __init__(self, timeout: int = 5, max_workers: int = 10):
        """Initialize the proxy finder.
        
        Args:
            timeout: Timeout in seconds for proxy tests
            max_workers: Maximum number of concurrent workers for testing
        """
        self.timeout = timeout
        self.max_workers = max_workers
        self.user_agent = UserAgent()
        
    def _get_headers(self) -> Dict[str, str]:
        """Get random headers to avoid detection."""
        return {
            'User-Agent': self.user_agent.random,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        
    def fetch_free_proxies(self) -> List[str]:
        """Fetch free proxies from multiple sources.
        
        Returns:
            List of proxy URLs in format "http://ip:port"
        """
        proxies = []
        
        # Add proxy sources
        sources = [
            self._fetch_proxies_from_free_proxy_list,
            self._fetch_proxies_from_geonode,
            # Add more sources as needed
        ]
        
        # Fetch from all sources
        for source_func in sources:
            try:
                source_proxies = source_func()
                logger.info(f"Found {len(source_proxies)} proxies from {source_func.__name__}")
                proxies.extend(source_proxies)
            except Exception as e:
                logger.error(f"Error fetching proxies from {source_func.__name__}: {e}")
        
        # Remove duplicates
        proxies = list(set(proxies))
        logger.info(f"Found {len(proxies)} unique proxies")
        
        return proxies
        
    def _fetch_proxies_from_free_proxy_list(self) -> List[str]:
        """Fetch proxies from free-proxy-list.net.
        
        Returns:
            List of proxy URLs
        """
        proxies = []
        url = "https://free-proxy-list.net/"
        
        try:
            response = requests.get(url, headers=self._get_headers(), timeout=self.timeout)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            table = soup.find('table', id='proxylisttable')
            
            if not table:
                logger.warning("Proxy table not found on free-proxy-list.net")
                return []
                
            for row in table.find_all('tr')[1:]:  # Skip header row
                columns = row.find_all('td')
                if len(columns) >= 7:
                    ip = columns[0].text.strip()
                    port = columns[1].text.strip()
                    https = columns[6].text.strip()
                    
                    if https.lower() == 'yes':
                        schema = 'https'
                    else:
                        schema = 'http'
                        
                    proxy = f"{schema}://{ip}:{port}"
                    proxies.append(proxy)
                    
        except Exception as e:
            logger.error(f"Error fetching proxies from free-proxy-list.net: {e}")
            
        return proxies
        
    def _fetch_proxies_from_geonode(self) -> List[str]:
        """Fetch proxies from geonode.com API.
        
        Returns:
            List of proxy URLs
        """
        proxies = []
        url = "https://proxylist.geonode.com/api/proxy-list?limit=100&page=1&sort_by=lastChecked&sort_type=desc"
        
        try:
            response = requests.get(url, headers=self._get_headers(), timeout=self.timeout)
            response.raise_for_status()
            
            data = response.json()
            for proxy_data in data.get('data', []):
                ip = proxy_data.get('ip')
                port = proxy_data.get('port')
                protocols = proxy_data.get('protocols', [])
                
                if ip and port and protocols:
                    for protocol in protocols:
                        protocol = protocol.lower()
                        if protocol in ['http', 'https']:
                            proxy = f"{protocol}://{ip}:{port}"
                            proxies.append(proxy)
                    
        except Exception as e:
            logger.error(f"Error fetching proxies from geonode.com: {e}")
            
        return proxies
        
    def test_proxy(self, proxy: str) -> Tuple[str, bool, float]:
        """Test a proxy against Google.
        
        Args:
            proxy: Proxy URL in format "http://ip:port"
            
        Returns:
            Tuple of (proxy_url, is_working, response_time)
        """
        test_url = "https://www.google.com/search?q=test"
        proxies = {
            'http': proxy,
            'https': proxy
        }
        
        start_time = time.time()
        try:
            response = requests.get(
                test_url,
                headers=self._get_headers(),
                proxies=proxies,
                timeout=self.timeout
            )
            
            if response.status_code == 200 and "Google" in response.text:
                response_time = time.time() - start_time
                return proxy, True, response_time
                
        except Exception:
            pass
            
        return proxy, False, 0.0
        
    def find_working_proxies(self, num_proxies: int = 5) -> List[str]:
        """Find working proxies by testing a pool of free proxies.
        
        Args:
            num_proxies: Number of working proxies to find
            
        Returns:
            List of working proxy URLs
        """
        all_proxies = self.fetch_free_proxies()
        working_proxies = []
        
        if not all_proxies:
            logger.warning("No proxies found to test")
            return []
            
        # Shuffle the list to avoid always testing the same proxies
        random.shuffle(all_proxies)
        
        logger.info(f"Testing {len(all_proxies)} proxies...")
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_proxy = {
                executor.submit(self.test_proxy, proxy): proxy 
                for proxy in all_proxies
            }
            
            for future in concurrent.futures.as_completed(future_to_proxy):
                proxy, is_working, response_time = future.result()
                
                if is_working:
                    logger.info(f"Proxy {proxy} is working (response time: {response_time:.2f}s)")
                    working_proxies.append(proxy)
                    
                    # Check if we have enough working proxies
                    if len(working_proxies) >= num_proxies:
                        # Cancel remaining futures
                        for f in future_to_proxy:
                            f.cancel()
                        break
        
        logger.info(f"Found {len(working_proxies)} working proxies")
        return working_proxies

def save_proxies_to_file(proxies: List[str], filename: str = "working_proxies.txt") -> None:
    """Save working proxies to a file.
    
    Args:
        proxies: List of proxy URLs
        filename: Output filename
    """
    with open(filename, 'w') as f:
        for proxy in proxies:
            f.write(f"{proxy}\n")
    
    logger.info(f"Saved {len(proxies)} proxies to {filename}")

def load_proxies_from_file(filename: str = "working_proxies.txt") -> List[str]:
    """Load proxies from a file.
    
    Args:
        filename: Input filename
        
    Returns:
        List of proxy URLs
    """
    try:
        with open(filename, 'r') as f:
            proxies = [line.strip() for line in f if line.strip()]
        
        logger.info(f"Loaded {len(proxies)} proxies from {filename}")
        return proxies
    except FileNotFoundError:
        logger.warning(f"Proxy file {filename} not found")
        return []

if __name__ == "__main__":
    # Example usage
    finder = ProxyFinder(timeout=10)
    working_proxies = finder.find_working_proxies(num_proxies=5)
    
    if working_proxies:
        save_proxies_to_file(working_proxies)
        
        # Test the Google Job Scraper with the first working proxy
        from google_job_scraper import GoogleJobScraper
        
        scraper = GoogleJobScraper(proxy_list=working_proxies[:2])
        job_urls = scraper.search_jobs(
            query="software developer join.com",
            site_filter="join.com",
            pages_to_search=1
        )
        
        print("\nFound job URLs:")
        for idx, url in enumerate(job_urls, 1):
            print(f"{idx}. {url}")
    else:
        logger.warning("No working proxies found") 