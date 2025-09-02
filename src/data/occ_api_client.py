#!/usr/bin/env python3
"""
Oklahoma Corporation Commission (OCC) API Client
Direct integration with OCC's official RBDMS wells database
"""

import requests
import pandas as pd
import json
from typing import List, Dict, Optional, Tuple
from pathlib import Path
import logging
from datetime import datetime
import time

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class OCCAPIClient:
    """Client for Oklahoma Corporation Commission RBDMS Wells API"""
    
    def __init__(self, cache_dir: str = ".cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        
        # Official OCC RBDMS Wells API endpoint
        self.base_url = "https://gis.occ.ok.gov/server/rest/services/Hosted/RBDMS_WELLS/FeatureServer/220/query"
        
        # Orphan well status codes from OCC
        self.orphan_statuses = ['OR', 'STFD', 'SFFO', 'SFAW']
        
        # API constraints
        self.max_record_count = 2000  # OCC limit per request
        
    def _make_request(self, params: Dict, max_retries: int = 3) -> Dict:
        """Make API request with retry logic"""
        
        for attempt in range(max_retries):
            try:
                response = requests.get(self.base_url, params=params, timeout=60)
                response.raise_for_status()
                
                data = response.json()
                
                # Check for API errors
                if 'error' in data:
                    raise Exception(f"OCC API Error: {data['error']}")
                
                return data
                
            except requests.RequestException as e:
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt
                    logger.warning(f"Request failed, retrying in {wait_time}s: {e}")
                    time.sleep(wait_time)
                else:
                    logger.error(f"Request failed after {max_retries} attempts: {e}")
                    raise
                    
    def get_orphan_wells_count(self) -> int:
        """Get total count of orphan wells without fetching all data"""
        
        orphan_where = "wellstatus IN ('{}')".format("','".join(self.orphan_statuses))
        
        params = {
            'where': orphan_where,
            'returnCountOnly': 'true',
            'f': 'json'
        }
        
        logger.info("Getting orphan wells count from OCC...")
        
        try:
            data = self._make_request(params)
            count = data.get('count', 0)
            
            logger.info(f"Found {count:,} orphan wells in OCC registry")
            return count
            
        except Exception as e:
            logger.error(f"Error getting orphan wells count: {e}")
            return 0
    
    def get_orphan_wells_batch(self, offset: int = 0, limit: int = None) -> List[Dict]:
        """Get a batch of orphan wells with pagination"""
        
        if limit is None:
            limit = self.max_record_count
        
        orphan_where = "wellstatus IN ('{}')".format("','".join(self.orphan_statuses))
        
        params = {
            'where': orphan_where,
            'outFields': '*',  # Get all fields
            'returnGeometry': 'true',  # Include lat/lon
            'f': 'json',
            'resultOffset': offset,
            'resultRecordCount': limit
        }
        
        logger.info(f"Fetching orphan wells batch: offset={offset}, limit={limit}")
        
        try:
            data = self._make_request(params)
            
            features = data.get('features', [])
            
            # Extract well records
            wells = []
            for feature in features:
                attributes = feature.get('attributes', {})
                geometry = feature.get('geometry', {})
                
                # Combine attributes with geometry
                well = attributes.copy()
                if geometry:
                    well['latitude'] = geometry.get('y')
                    well['longitude'] = geometry.get('x')
                
                wells.append(well)
            
            logger.info(f"Retrieved {len(wells)} orphan wells from batch")
            return wells
            
        except Exception as e:
            logger.error(f"Error fetching orphan wells batch: {e}")
            return []
    
    def get_all_orphan_wells(self, force_refresh: bool = False) -> pd.DataFrame:
        """Get all orphan wells with automatic pagination"""
        
        cache_file = self.cache_dir / f"occ_orphan_wells_{datetime.now().strftime('%Y%m%d')}.json"
        
        # Use cached data if available and not forcing refresh
        if cache_file.exists() and not force_refresh:
            logger.info(f"Loading cached orphan wells from {cache_file}")
            with open(cache_file, 'r') as f:
                wells_data = json.load(f)
            return pd.DataFrame(wells_data)
        
        logger.info("Downloading complete orphan wells dataset from OCC...")
        
        # Get total count first
        total_count = self.get_orphan_wells_count()
        if total_count == 0:
            logger.warning("No orphan wells found in OCC registry")
            return pd.DataFrame()
        
        # Fetch all wells with pagination
        all_wells = []
        offset = 0
        batch_size = self.max_record_count
        
        while offset < total_count:
            batch_wells = self.get_orphan_wells_batch(offset, batch_size)
            
            if not batch_wells:
                logger.warning(f"Empty batch at offset {offset}, stopping")
                break
            
            all_wells.extend(batch_wells)
            offset += len(batch_wells)
            
            logger.info(f"Progress: {len(all_wells)}/{total_count} wells downloaded")
            
            # Rate limiting
            time.sleep(0.5)
        
        df = pd.DataFrame(all_wells)
        
        # Cache the results
        with open(cache_file, 'w') as f:
            json.dump(all_wells, f, indent=2, default=str)
        
        logger.info(f"Downloaded {len(df)} total orphan wells and cached to {cache_file}")
        
        return df
    
    def normalize_api_numbers(self, df: pd.DataFrame) -> pd.DataFrame:
        """Normalize API numbers for WellDatabase compatibility"""
        
        if 'api' not in df.columns:
            logger.error("No 'api' column found in OCC data")
            return df
        
        logger.info("Normalizing API numbers for WellDatabase compatibility...")
        
        # Convert API to string and clean
        df['api_raw'] = df['api'].astype(str).str.strip()
        
        # Remove any non-numeric characters and pad to proper length
        df['api_clean'] = df['api_raw'].str.replace(r'[^0-9]', '', regex=True)
        
        # Create standardized API formats
        df['api_10'] = df['api_clean'].str[:10].str.zfill(10)
        df['api_14'] = df['api_clean'].str[:14].str.zfill(14)
        
        # Oklahoma state prefix (35) validation
        df['valid_oklahoma_api'] = df['api_10'].str.startswith('35')
        
        valid_count = df['valid_oklahoma_api'].sum()
        total_count = len(df)
        
        logger.info(f"API normalization complete: {valid_count}/{total_count} have valid Oklahoma API format")
        
        if valid_count < total_count * 0.8:  # Less than 80% valid
            logger.warning("Low percentage of valid Oklahoma APIs - check data quality")
        
        return df
    
    def get_orphan_wells_for_welldatabase(self, force_refresh: bool = False) -> Tuple[List[str], pd.DataFrame]:
        """
        Get orphan wells formatted for WellDatabase lookup
        
        Returns:
            Tuple of (api_10_list, full_dataframe_with_context)
        """
        
        logger.info("Preparing orphan wells for WellDatabase integration...")
        
        # Get all orphan wells
        df = self.get_all_orphan_wells(force_refresh)
        
        if df.empty:
            logger.warning("No orphan wells data available")
            return [], df
        
        # Normalize API numbers
        df = self.normalize_api_numbers(df)
        
        # Filter to valid Oklahoma APIs only
        valid_df = df[df['valid_oklahoma_api'] == True].copy()
        
        # Get unique API list for WellDatabase lookup
        api_list = valid_df['api_10'].dropna().unique().tolist()
        
        # Add metadata
        valid_df['data_source'] = 'OCC_RBDMS_API'
        valid_df['orphan_status_confirmed'] = True
        valid_df['download_date'] = datetime.now().isoformat()
        
        logger.info(f"Prepared {len(api_list)} unique orphan well APIs for WellDatabase lookup")
        
        return api_list, valid_df
    
    def analyze_orphan_status_codes(self) -> Dict:
        """Analyze the distribution of orphan status codes"""
        
        logger.info("Analyzing orphan well status code distribution...")
        
        df = self.get_all_orphan_wells()
        
        if df.empty:
            return {}
        
        # Status code analysis
        status_counts = df['wellstatus'].value_counts()
        
        # Well type analysis
        welltype_counts = df['welltype'].value_counts() if 'welltype' in df.columns else {}
        
        # County distribution
        county_counts = df['county'].value_counts().head(10) if 'county' in df.columns else {}
        
        analysis = {
            'total_orphan_wells': len(df),
            'status_code_distribution': status_counts.to_dict(),
            'well_type_distribution': welltype_counts.to_dict() if welltype_counts else {},
            'top_counties': county_counts.to_dict() if county_counts else {},
            'orphan_status_codes_used': self.orphan_statuses,
            'analysis_date': datetime.now().isoformat()
        }
        
        return analysis


def test_occ_api_integration():
    """Test the OCC API integration"""
    
    print("🔍 TESTING OCC API INTEGRATION")
    print("=" * 50)
    
    client = OCCAPIClient()
    
    try:
        # Test 1: Get count
        print("\n📊 Test 1: Getting orphan wells count...")
        count = client.get_orphan_wells_count()
        print(f"✅ Found {count:,} orphan wells in OCC registry")
        
        # Test 2: Get small batch
        print(f"\n📋 Test 2: Getting first 10 orphan wells...")
        batch = client.get_orphan_wells_batch(offset=0, limit=10)
        print(f"✅ Retrieved {len(batch)} wells in test batch")
        
        if batch:
            sample_well = batch[0]
            print(f"   Sample well fields: {list(sample_well.keys())}")
            print(f"   Sample API: {sample_well.get('api', 'Unknown')}")
            print(f"   Sample name: {sample_well.get('well_name', 'Unknown')}")
            print(f"   Sample status: {sample_well.get('wellstatus', 'Unknown')}")
        
        # Test 3: API normalization
        print(f"\n🔧 Test 3: API number normalization...")
        df = pd.DataFrame(batch)
        df = client.normalize_api_numbers(df)
        print(f"✅ Normalized API numbers for {len(df)} wells")
        
        if not df.empty:
            print(f"   Sample API-10: {df.iloc[0]['api_10']}")
            print(f"   Valid OK format: {df.iloc[0]['valid_oklahoma_api']}")
        
        # Test 4: Status analysis
        print(f"\n📈 Test 4: Status code analysis...")
        analysis = client.analyze_orphan_status_codes()
        print(f"✅ Status analysis complete:")
        print(f"   Total orphan wells: {analysis.get('total_orphan_wells', 0):,}")
        print(f"   Status codes: {analysis.get('status_code_distribution', {})}")
        print(f"   Well types: {list(analysis.get('well_type_distribution', {}).keys())}")
        
        print(f"\n🎯 OCC API INTEGRATION TEST PASSED!")
        return True
        
    except Exception as e:
        print(f"\n❌ OCC API integration test failed: {e}")
        return False


if __name__ == "__main__":
    success = test_occ_api_integration()
    
    if success:
        print(f"\n✅ Ready to integrate with WellDatabase!")
        print(f"   Next step: Use get_orphan_wells_for_welldatabase() for hydration")
    else:
        print(f"\n❌ Fix OCC API issues before proceeding")