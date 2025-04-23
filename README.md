# Job Application Bot

This project is a Python-based automation tool designed to search for job listings and apply to them automatically. It supports multiple ATS platforms including join.com and Greenhouse.

## Features

- **Automated Job Search**: Searches for job listings on Google using specified queries.
- **Multi-platform Support**: 
  - **join.com**: Uses Selenium for automation.
- **CAPTCHA Solving**: Utilizes Anti-Captcha services to solve CAPTCHAs encountered during the application process.
- **Automated Job Application**: Automatically fills out and submits job application forms on supported websites.
- **Dynamic Form Handling**: Intelligently parses and fills form fields based on question context.

## New Features

### CAPTCHA-Resistant Google Job Scraping

The application now includes a robust job URL scraper with multiple strategies to avoid CAPTCHA detection:

1. **Multi-strategy approach**: Uses both requests-based scraping and Selenium as a fallback
2. **CAPTCHA detection**: Automatically detects when CAPTCHA is present and switches strategies
3. **Browser fingerprint evasion**: Implements multiple techniques to avoid detection:
   - Random User-Agent rotation
   - Random delays and scrolling behavior
   - Disabled WebDriver flags
   - Optional proxy support
   
#### Usage

```python
from google_job_scraper import GoogleJobScraper

# Initialize scraper (optionally with proxies for better results)
scraper = GoogleJobScraper(
    proxy_list=["http://your-proxy-server:port"],  # Optional
    use_selenium=True  # Enable Selenium fallback
)

# Search for jobs
job_urls = scraper.search_jobs(
    query="software developer join.com",
    site_filter="join.com",
    pages_to_search=3
)

# Print results
for idx, url in enumerate(job_urls, 1):
    print(f"{idx}. {url}")
```

### Benefits

- More reliable job search results
- Reduced CAPTCHA blocking
- Automatic fallback mechanisms when one method fails
- No need for paid CAPTCHA solving services

## Using the Enhanced Job Search

The CAPTCHA-resistant job search functionality can be used in several ways:

### Quick Start with Shell Script

Use the provided shell script for a convenient way to run the job search:

```bash
# Basic usage (search only)
./run_job_search.sh

# Search with headless mode and proxy finding
./run_job_search.sh --headless --proxies

# Use custom queries file
./run_job_search.sh --queries custom_queries.json

# Search and apply to jobs
./run_job_search.sh --apply
```

### Command Line Options

- `-h, --headless`: Run in headless mode
- `-p, --proxies`: Find and test new proxies before running
- `-q, --queries FILE`: Use custom queries file (default: search_queries.json)
- `-a, --apply`: Apply to jobs after finding them
- `--help`: Show help message

### Advanced Usage

You can create custom query files to target specific job types. Create a JSON file with this format:

```json
[
  {
    "query": "machine learning engineer remote join.com",
    "site_filter": "join.com"
  },
  {
    "query": "data engineer remote join.com",
    "site_filter": "join.com"
  }
]
```

Then run with:
```bash
./run_job_search.sh -q your_custom_queries.json
```

### Direct Module Usage

You can also use the modules directly in your Python code:

```python
from google_job_scraper import GoogleJobScraper

# With proxies
scraper = GoogleJobScraper(
    proxy_list=["http://your-proxy-server:port"],
    use_stealth=True
)

# Without proxies
scraper = GoogleJobScraper(use_stealth=True)

# Search for jobs
job_urls = scraper.search_jobs(
    query="software developer join.com",
    site_filter="join.com",
    pages_to_search=3
)

# Print results
for idx, url in enumerate(job_urls, 1):
    print(f"{idx}. {url}")
```

## Requirements

- Python 3.x
- Selenium (for join.com)
- Playwright (for Greenhouse)
- WebDriver Manager for Chrome
- Anti-Captcha Official Python Library
- Google Search Python Library

## Setup

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd <repository-directory>
   ```

2. **Install the required packages**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up Playwright browsers and dependencies** (for Greenhouse applications):
   ```bash
   python install_browsers.py
   ```
   This script will install all necessary browsers and system dependencies for Playwright.

4. **Configure your environment**:
   - Ensure you have a valid Anti-Captcha API key.
   - Update the `cookies.json` file with your session cookies for join.com (if using).
   - Update the `config.json` file with your personal application details.
   - Ensure your resume PDF is located at the specified path in the code.
   - Verify that your `resume.json` file contains the correct information for filling out application forms.

## Usage

1. **Run the bot for all supported platforms**:
   ```bash
   python main.py
   ```

2. **Test Greenhouse applications specifically**:
   ```bash
   python test_greenhouse.py
   ```

3. **Customize your job search**:
   - Modify the job search query lists in `main.py` to change the job search criteria.
   - Add or remove platforms by modifying the relevant sections in `main.py`.

## Supported Platforms

### join.com
- Uses Selenium for automation
- Requires valid session cookies in `cookies.json`
- Handles multi-step application forms

## Important Notes

- Ensure that your `cookies.json` file is up-to-date with valid session cookies to avoid login issues with join.com.
- For the Greenhouse application script, the resume path is hardcoded - update it if your resume is located elsewhere.
- By default, the actual form submission is commented out in the Greenhouse handler for testing purposes. Uncomment the submit button click line to enable real submissions.
- Make sure your `config.json` and `resume.json` files are correctly filled out to ensure accurate application submissions.
- The Playwright implementation uses asynchronous API which is required when working with asyncio loops.

## Troubleshooting

### Playwright Issues

If you encounter errors related to Playwright:

1. Make sure you've run the `install_browsers.py` script to set up browsers properly:
   ```bash
   python install_browsers.py
   ```

2. If you see "Target page, context or browser has been closed" errors:
   - This usually indicates premature browser closing. The async implementation should fix this.

3. If you see "using Playwright Sync API inside the asyncio loop" errors:
   - The code has been updated to use the async API, which resolves this issue.

## Extending to Other Platforms

The codebase is designed to be extended to support additional ATS platforms. To add support for a new platform:

1. Create a new handler class following the pattern of `GreenhouseHandler`
2. Implement the platform-specific form filling logic
3. Add the new platform to the main execution flow in `main.py`

## License

This project is licensed under the MIT License. See the LICENSE file for more details.

# Advanced Google Job Scraper

This project provides a robust solution for scraping job URLs from Google search results using multiple fallback strategies to maximize success rate while avoiding CAPTCHA and rate limiting.

## Features

- **Multiple Scraping Strategies**:
  - Requests-based scraping with custom headers and proxy support
  - googlesearch-python library integration
  - Selenium WebDriver with stealth mode and human behavior simulation
  - Google JSON API-like endpoint access

- **Anti-Detection Measures**:
  - CAPTCHA detection and avoidance
  - Random delays and user agent rotation
  - Proxy support for IP rotation
  - Cookie management to maintain sessions
  - Stealth mode for browser automation

- **Reliability Features**:
  - Automatic retry mechanisms for all methods
  - Progressive fallback through multiple strategies
  - Robust error handling and recovery
  - Comprehensive logging

## Installation

1. Clone the repository:
   ```
   git clone <repository-url>
   cd <repository-directory>
   ```

2. Install required dependencies:
   ```
   pip install -r requirements.txt
   ```

3. (Optional) Configure Chrome WebDriver if you want to use Selenium:
   - The script will automatically download the appropriate WebDriver version

## Usage

### Basic Usage

```python
from google_job_scraper import GoogleJobScraper

# Initialize the scraper
scraper = GoogleJobScraper()

# Search for job listings
job_urls = scraper.search_jobs(
    query="python developer remote",
    site_filter="indeed.com",
    pages_to_search=3
)

# Print the results
for url in job_urls:
    print(url)
```

### Advanced Configuration

```python
from google_job_scraper import GoogleJobScraper

# Initialize with advanced options
scraper = GoogleJobScraper(
    driver_path="/path/to/chromedriver",  # Optional, will download if not provided
    proxy_list=["http://proxy1.com:8080", "http://proxy2.com:8080"],
    use_selenium=True,
    use_stealth=True,
    use_library=True,
    use_api=True,
    cookies_file="custom_cookies.json",
    headless=True,
    max_retries=3
)

# Use a specific method directly
job_urls = scraper.search_jobs_with_library(
    query="software engineer",
    site_filter="linkedin.com",
    pages_to_search=2,
    sleep_interval=5
)
```

## Testing

Use the provided test scripts to validate the scraper's functionality:

```bash
# Test all strategies (with fallback)
python test_scraper.py --query "python developer" --site "indeed.com" --pages 1

# Test individual strategies (to avoid rate limiting)
python test_scraper_slow.py --method requests --query "software engineer" --site "indeed.com"
python test_scraper_slow.py --method library --query "data scientist" --site "linkedin.com"
python test_scraper_slow.py --method selenium --query "machine learning" --site "glassdoor.com" --no-headless
python test_scraper_slow.py --method api --query "frontend developer" --site "monster.com"
```

## Avoiding Rate Limiting

To avoid getting rate-limited or blocked by Google:

1. Use longer delays between requests (`sleep_interval` parameter)
2. Rotate proxies when available
3. Run tests with only one method at a time
4. Limit the number of pages searched in a single session
5. Add a delay between testing sessions
6. Use the `--no-headless` option with Selenium to monitor and solve CAPTCHAs manually when needed

## License

[Add your license information here]

## Disclaimer

This tool is for educational purposes only. Please use responsibly and in accordance with Google's terms of service.
