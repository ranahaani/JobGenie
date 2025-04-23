# JobGenie Modular Bot Framework

A modular framework for automating job applications across multiple ATS (Applicant Tracking System) platforms.

## Architecture

The JobGenie framework is designed with modularity and extensibility in mind, allowing for easy addition of new job application platforms:

```
job_bots/
├── __init__.py            # Package exports
├── base_bot.py            # Base bot abstract class with common functionality
├── config.py              # Configuration classes for user data and platform settings
├── factory.py             # Factory to create platform-specific bots
├── utils.py               # Shared utility functions
└── platforms/             # Platform-specific implementations
    ├── __init__.py        # Platform exports
    ├── join_bot.py        # Join.com implementation
    └── greenhouse_bot.py  # Greenhouse implementation
```

## Key Components

### 1. Base Bot

`BaseJobApplicationBot` is an abstract class that defines the common interface and functionality for all platform-specific bots. It handles:

- Webdriver initialization and cleanup
- Basic cookie management
- Random delays for human-like behavior
- Common utilities (job search, cover letter generation)
- Context management with `__enter__` and `__exit__` methods

### 2. Platform-Specific Bots

Each platform has its own implementation in the `platforms/` directory:

- `JoinApplicationBot` - Handles job applications on Join.com
- `GreenhouseApplicationBot` - Handles job applications on Greenhouse.io

### 3. Configuration

`ApplicationConfig` - Contains user data for job applications:
- Required skills and experience
- Work authorization and sponsorship requirements
- Compensation expectations
- Availability dates
- Language proficiency

`PlatformConfig` - Platform-specific settings:
- Login URLs
- Cookie file paths
- Custom settings per platform

### 4. Factory

`JobApplicationBotFactory` - Creates the appropriate bot instance based on the job URL:
- Detects platforms from URLs
- Creates platform-specific bots
- Groups URLs by platform for efficient processing

### 5. Utils

Utility functions for:
- Loading search queries
- Recording applied jobs
- Checking if already applied to jobs

## Adding a New Platform

To add support for a new job application platform:

1. Create a new file in the `platforms/` directory (e.g., `workday_bot.py`)

2. Implement a new class that inherits from `BaseJobApplicationBot`:

```python
from job_bots.base_bot import BaseJobApplicationBot
from job_bots.config import ApplicationConfig, PlatformConfig

class WorkdayApplicationBot(BaseJobApplicationBot):
    """Bot for automating job applications on Workday platform."""
    
    def __init__(self, driver_path: str, platform_config: PlatformConfig, cookies_file=None):
        super().__init__(driver_path, platform_config, cookies_file)
        # Platform-specific initialization
    
    def _extract_job_details(self):
        """Extract job details from the page."""
        # Implement job details extraction
        # Return (job_title, job_description, hr_name)
        
    def apply_to_job(self, job_url, config):
        """Apply to a specific job."""
        # Implement job application logic
        # Return True if successful, False otherwise
        
    def login_and_apply_to_jobs(self, job_urls, config):
        """Login and apply to multiple jobs."""
        # Implement multi-job application logic
```

3. Update the imports in `platforms/__init__.py`:

```python
from job_bots.platforms.join_bot import JoinApplicationBot
from job_bots.platforms.greenhouse_bot import GreenhouseApplicationBot
from job_bots.platforms.workday_bot import WorkdayApplicationBot

__all__ = [
    'JoinApplicationBot',
    'GreenhouseApplicationBot',
    'WorkdayApplicationBot',
]
```

4. Add platform detection to `JobApplicationBotFactory.detect_platform()`:

```python
@staticmethod
def detect_platform(url: str) -> str:
    url_lower = url.lower()
    
    if 'join.com' in url_lower:
        return 'join'
    elif 'boards.greenhouse.io' in url_lower or 'greenhouse.io' in url_lower:
        return 'greenhouse'
    elif 'workday.com' in url_lower:  # Add detection for new platform
        return 'workday'
    else:
        # Default to join.com for unknown platforms
        logger.warning(f"Unknown platform for URL: {url}. Defaulting to join.com")
        return 'join'
```

5. Add bot creation to `JobApplicationBotFactory.create_bot()`:

```python
@staticmethod
def create_bot(platform: str, driver_path: str, platform_configs: Dict[str, PlatformConfig], 
               cookies_file: Optional[Path] = None) -> BaseJobApplicationBot:
    # Get the platform configuration
    platform_config = platform_configs.get(platform)
    if not platform_config:
        logger.warning(f"No configuration found for platform: {platform}. Using default.")
        platform_config = PlatformConfig(platform_name=platform)
    
    if platform == 'greenhouse':
        logger.info("Creating Greenhouse application bot")
        return GreenhouseApplicationBot(driver_path, platform_config, cookies_file)
    elif platform == 'workday':  # Add creation for new platform
        logger.info("Creating Workday application bot")
        return WorkdayApplicationBot(driver_path, platform_config, cookies_file)
    else:
        # Default to join.com
        logger.info("Creating Join.com application bot")
        return JoinApplicationBot(driver_path, platform_config, cookies_file)
```

6. Add platform configuration to `PlatformConfig.load_all_platforms()`:

```python
@classmethod
def load_all_platforms(cls) -> Dict[str, 'PlatformConfig']:
    platforms = {}
    
    # Join.com configuration
    platforms['join'] = PlatformConfig(
        platform_name='join',
        login_url='https://join.com/auth/login',
        cookies_file='cookies.json',
    )
    
    # Greenhouse configuration
    platforms['greenhouse'] = PlatformConfig(
        platform_name='greenhouse',
        # Greenhouse doesn't typically require login for applications
        custom_settings={
            'use_analyzer': True,
        }
    )
    
    # New platform
    platforms['workday'] = PlatformConfig(
        platform_name='workday',
        login_url='https://www.myworkday.com/login',
        custom_settings={
            'application_flow': 'multi-page',
        }
    )
    
    return platforms
```

## Usage

The main script handles the end-to-end flow of the job application process:

```python
#!/usr/bin/env python3
import logging
from webdriver_manager.chrome import ChromeDriverManager

from job_bots.config import ApplicationConfig, PlatformConfig
from job_bots.factory import JobApplicationBotFactory
from job_bots.utils import load_search_queries
from google_job_scraper import GoogleSearchScraper

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    # Load search queries
    search_query_data = load_search_queries()
    
    # Load application configuration
    config = ApplicationConfig.from_file('config.json')
    
    # Collect job URLs to apply to
    all_job_urls = collect_job_urls(search_query_data)
    
    # Load platform configurations
    platform_configs = PlatformConfig.load_all_platforms()
    
    # Group URLs by platform
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

if __name__ == "__main__":
    main()
```

## Configuration Files

### search_queries.json

Define job search queries:

```json
[
    {
        "query": "software engineer react",
        "site_filter": "join.com"
    },
    {
        "query": "frontend developer",
        "site_filter": "boards.greenhouse.io"
    }
]
```

### config.json

Define user application data:

```json
{
    "reside_in_barcelona": "Yes",
    "start_date": "01-11-2023",
    "expected_compensation": "70000",
    "english_proficiency": "Fluent",
    "require_sponsorship": "No",
    "react_experience": "4 years",
    "skills": ["JavaScript", "React", "TypeScript", "Node.js"],
    "german_proficiency": "Basic",
    "current_city": "Barcelona",
    "remotely_available": "Yes"
}
``` 