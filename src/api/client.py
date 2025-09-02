"""WellDatabase API Client"""

import httpx
import time
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from io import BytesIO
import zipfile
import csv
import pandas as pd

from ..config.settings import (
    BASE_URL, DEFAULT_HEADERS, DEFAULT_TIMEOUT, 
    EXPORT_TIMEOUT, RETRY_ATTEMPTS, RETRY_BACKOFF_FACTOR
)

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class WellDatabaseError(Exception):
    """Base exception for WellDatabase API errors"""
    pass

class APITimeoutError(WellDatabaseError):
    """Raised when API request times out"""
    pass

class APIRateLimitError(WellDatabaseError):
    """Raised when API rate limit is exceeded"""
    pass

class WellDatabaseClient:
    """Client for interacting with WellDatabase API v2"""
    
    def __init__(self, api_key: str = None, base_url: str = BASE_URL):
        self.base_url = base_url
        self.headers = DEFAULT_HEADERS.copy()
        
        if api_key:
            self.headers['Api-Key'] = api_key
            
        self.session = httpx.Client(headers=self.headers, timeout=DEFAULT_TIMEOUT)
    
    def _make_request(self, method: str, endpoint: str, data: Dict = None, 
                     timeout: int = DEFAULT_TIMEOUT, max_retries: int = RETRY_ATTEMPTS) -> httpx.Response:
        """Make HTTP request with retry logic and error handling"""
        
        url = f"{self.base_url}{endpoint}"
        
        for attempt in range(max_retries):
            try:
                logger.debug(f"Making {method} request to {endpoint} (attempt {attempt + 1})")
                
                if method.upper() == 'POST':
                    response = self.session.post(url, json=data, timeout=timeout)
                elif method.upper() == 'GET':
                    response = self.session.get(url, params=data, timeout=timeout)
                else:
                    raise WellDatabaseError(f"Unsupported HTTP method: {method}")
                
                # Handle different response codes
                if response.status_code == 200:
                    return response
                elif response.status_code == 401:
                    raise WellDatabaseError("Unauthorized - check API key")
                elif response.status_code == 403:
                    raise WellDatabaseError("Forbidden - insufficient permissions")
                elif response.status_code == 404:
                    raise WellDatabaseError(f"Endpoint not found: {endpoint}")
                elif response.status_code == 429:
                    if attempt < max_retries - 1:
                        wait_time = RETRY_BACKOFF_FACTOR ** attempt
                        logger.warning(f"Rate limited, waiting {wait_time}s before retry")
                        time.sleep(wait_time)
                        continue
                    else:
                        raise APIRateLimitError("Rate limit exceeded - max retries reached")
                elif response.status_code == 500:
                    raise WellDatabaseError(f"Server error on {endpoint}: {response.text}")
                else:
                    raise WellDatabaseError(f"HTTP {response.status_code}: {response.text}")
                    
            except httpx.TimeoutException:
                if attempt < max_retries - 1:
                    wait_time = RETRY_BACKOFF_FACTOR ** attempt
                    logger.warning(f"Request timeout, waiting {wait_time}s before retry")
                    time.sleep(wait_time)
                    continue
                else:
                    raise APITimeoutError(f"Request timeout after {max_retries} attempts")
                    
            except httpx.ConnectError:
                raise WellDatabaseError("Connection error - check internet connection")
                
        return response
    
    def search_wells(self, filters: Dict, page_size: int = 100, page_offset: int = 0) -> Dict:
        """Search for wells using specified filters"""
        
        data = {
            'Filters': filters,
            'PageSize': page_size,
            'PageOffset': page_offset
        }
        
        response = self._make_request('POST', '/wells/search', data)
        return response.json()
    
    def get_production_data(self, well_ids: List[str], start_date: str, 
                           end_date: str, page_size: int = 1000, page_offset: int = 0) -> Dict:
        """Get production data for specified wells and date range.

        Uses API v2 search contract with Filters, targeting InfinityIds and ReportDate window.
        """
        
        data = {
            'Filters': {
                'InfinityIds': well_ids,
                'ReportDate': {
                    'Min': start_date,
                    'Max': end_date
                }
            },
            'PageSize': page_size,
            'PageOffset': page_offset
        }
        
        response = self._make_request('POST', '/production/search', data, timeout=60)
        return response.json()
    
    # Note: export endpoints removed from client to keep single-source search method
    
    def get_well_by_api(self, api_number: str) -> Optional[Dict]:
        """Find a specific well by API number"""
        
        # Clean API number (remove dashes, take first 10 digits)
        api_clean = api_number.replace('-', '').replace(' ', '')
        api_10 = api_clean[:10]
        
        filters = {'Api10': [api_10]}
        result = self.search_wells(filters, page_size=1)
        
        wells = result.get('data', [])
        return wells[0] if wells else None
    
    def get_orphaned_wells(self, state_id: int, orphan_statuses: List[str], 
                          page_size: int = 100, page_offset: int = 0) -> Dict:
        """Get orphaned wells for a specific state"""
        
        filters = {
            'StateIds': {'Included': [state_id]},
            'WellStatus': orphan_statuses
        }
        
        return self.search_wells(filters, page_size, page_offset)
    
    def get_all_pages(self, search_function, *args, max_pages: int = None, **kwargs) -> List[Dict]:
        """Get all pages from a paginated API response"""
        
        all_results = []
        page_offset = 0
        page_num = 0
        
        while True:
            if max_pages and page_num >= max_pages:
                break
                
            # Update page offset in kwargs
            kwargs['page_offset'] = page_offset
            
            result = search_function(*args, **kwargs)
            wells = result.get('data', [])
            
            if not wells:
                break
                
            all_results.extend(wells)
            
            # Check if we have more pages
            total = result.get('total', 0)
            current_count = len(all_results)
            
            if current_count >= total:
                break
                
            page_offset += kwargs.get('page_size', 100)
            page_num += 1
            
            # Add small delay to avoid rate limiting
            time.sleep(0.1)
            
            logger.info(f"Retrieved page {page_num + 1}, total wells: {current_count}/{total}")
        
        return all_results
    
    def health_check(self) -> bool:
        """Check if API is accessible"""
        
        try:
            # Simple search to test connectivity
            filters = {'StateIds': {'Included': [35]}}  # Oklahoma
            result = self.search_wells(filters, page_size=1)
            return 'data' in result
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False
    
    def close(self):
        """Close the HTTP session"""
        self.session.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()