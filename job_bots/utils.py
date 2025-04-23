# Start of Selection
"""
Utility functions for job application bots.
"""

import json
import logging
import os
from typing import List, Dict
from pathlib import Path

logger = logging.getLogger(__name__)

# Base directory is set to project root for consistent file lookups
BASE_DIR = Path(__file__).resolve().parent.parent
SEARCH_QUERIES_FILE = BASE_DIR / "search_queries.json"
APPLIED_JOBS_FILE = BASE_DIR / "applied.txt"


def load_search_queries() -> List[Dict[str, str]]:
    """Load search queries from search_queries.json."""
    try:
        if SEARCH_QUERIES_FILE.exists():
            with SEARCH_QUERIES_FILE.open("r", encoding="utf-8") as f:
                queries = json.load(f)
            return [
                {
                    "query": q.get("query", ""),
                    "site_filter": q.get("site_filter", "join.com")
                }
                for q in queries
            ]
        else:
            logger.warning(f"{SEARCH_QUERIES_FILE} not found, using default queries")
    except Exception as e:
        logger.error(f"Error loading search queries: {e}")
    return []


def record_applied_job(job_url: str) -> None:
    """Record a job URL as applied in the applied.txt file."""
    try:
        # Ensure the parent directory exists
        APPLIED_JOBS_FILE.parent.mkdir(parents=True, exist_ok=True)
        with APPLIED_JOBS_FILE.open("a", encoding="utf-8") as f:
            f.write(f"{job_url}\n")
        logger.info(f"Recorded application for: {job_url}")
    except Exception as e:
        logger.error(f"Failed to record application: {e}")


def is_already_applied(job_url: str) -> bool:
    """Check if a job URL has already been applied to."""
    try:
        if APPLIED_JOBS_FILE.exists():
            with APPLIED_JOBS_FILE.open("r", encoding="utf-8") as f:
                applied_jobs = [line.strip() for line in f]
            return job_url in applied_jobs
        return False
    except Exception as e:
        logger.error(f"Error checking applied jobs: {e}")
        return False
# End of Selectio
