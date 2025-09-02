"""Configuration settings for WellDatabase API"""

import os

# API Configuration
API_KEY = os.getenv("WBD_API_KEY", "")
BASE_URL = os.getenv("WBD_BASE_URL", "https://app.welldatabase.com/api/v2")

# Request Configuration
DEFAULT_TIMEOUT = 30
EXPORT_TIMEOUT = 300
RETRY_ATTEMPTS = 3
RETRY_BACKOFF_FACTOR = 2

# Pagination
DEFAULT_PAGE_SIZE = 100
MAX_PAGE_SIZE = 1000

# Headers
DEFAULT_HEADERS = {
    'Content-Type': 'application/json',
    'Api-Key': API_KEY,
    'User-Agent': 'WellDatabase-Orphan-Analysis'
}

# Output Directories
OUTPUT_DIR = "output"
REPORTS_DIR = "reports"
CACHE_DIR = ".cache"