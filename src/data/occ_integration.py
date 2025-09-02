#!/usr/bin/env python3
"""
Oklahoma Corporation Commission (OCC) Integration
Authoritative orphan well list from OCC, hydrated with WellDatabase technical data
"""

import requests
import pandas as pd
import json
from typing import List, Dict, Tuple, Optional
from pathlib import Path
import logging
from datetime import datetime

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class OCCOrphanRegistry:
    """Interface to Oklahoma Corporation Commission orphan well registry"""
    
    def __init__(self, cache_dir: str = ".cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        
        # OCC ArcGIS endpoints
        self.occ_orphan_url = "https://services.arcgis.com/LG9Yn2oFqZi5PnO5/arcgis/rest/services/RBDMS_Orphan_Funds_Wells/FeatureServer/0/query"
        
    def download_occ_orphan_registry(self, force_refresh: bool = False) -> pd.DataFrame:
        """
        Download the official OCC orphan well registry
        
        Args:
            force_refresh: If True, download fresh data regardless of cache
            
        Returns:
            DataFrame with orphan well data including API numbers
        """
        
        cache_file = self.cache_dir / f"occ_orphan_registry_{datetime.now().strftime('%Y%m%d')}.json"
        
        # Use cached data if available and not forcing refresh
        if cache_file.exists() and not force_refresh:
            logger.info(f"Loading cached OCC data from {cache_file}")
            with open(cache_file, 'r') as f:
                data = json.load(f)
            return pd.DataFrame(data)
        
        logger.info("Downloading fresh OCC orphan registry data...")
        
        # ArcGIS REST API parameters
        params = {
            'where': '1=1',  # Get all records
            'outFields': '*',  # Get all fields
            'f': 'json',      # JSON format
            'returnGeometry': 'false'  # Don't need geometry for this use case
        }
        
        try:
            response = requests.get(self.occ_orphan_url, params=params, timeout=60)
            response.raise_for_status()
            
            data = response.json()
            
            if 'features' not in data:
                raise ValueError(f"Unexpected OCC API response format: {data.keys()}")
            
            # Extract features and convert to DataFrame
            records = []
            for feature in data['features']:
                attributes = feature.get('attributes', {})
                records.append(attributes)
            
            df = pd.DataFrame(records)
            
            logger.info(f"Downloaded {len(df)} orphan wells from OCC registry")
            
            # Cache the data
            with open(cache_file, 'w') as f:
                json.dump(records, f, indent=2, default=str)
            
            logger.info(f"Cached OCC data to {cache_file}")
            
            return df
            
        except requests.RequestException as e:
            logger.error(f"Failed to download OCC data: {e}")
            raise
        except Exception as e:
            logger.error(f"Error processing OCC data: {e}")
            raise
    
    def normalize_api_numbers(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Normalize API numbers to handle Oklahoma's API quirks
        
        Args:
            df: DataFrame with API column
            
        Returns:
            DataFrame with normalized API10 and API14 columns
        """
        
        # Identify API column (may have different names)
        api_column = None
        for col in df.columns:
            if 'api' in col.lower():
                api_column = col
                break
        
        if not api_column:
            logger.warning("No API column found in OCC data")
            return df
        
        logger.info(f"Normalizing API numbers from column: {api_column}")
        
        # Clean API numbers
        df['api_raw'] = df[api_column].astype(str)
        df['api_clean'] = df['api_raw'].str.replace('-', '').str.replace(' ', '').str.strip()
        
        # Create API10 and API14 versions
        df['api_10'] = df['api_clean'].str[:10].str.zfill(10)
        df['api_14'] = df['api_clean'].str[:14].str.zfill(14)
        
        # Remove invalid APIs
        df = df[df['api_10'].str.len() >= 10]
        
        logger.info(f"Normalized {len(df)} API numbers")
        
        return df
    
    def get_orphan_api_list(self, force_refresh: bool = False) -> List[str]:
        """
        Get list of orphan well API numbers for WellDatabase lookup
        
        Args:
            force_refresh: If True, download fresh OCC data
            
        Returns:
            List of API10 numbers for orphan wells
        """
        
        df = self.download_occ_orphan_registry(force_refresh)
        df = self.normalize_api_numbers(df)
        
        # Get unique API numbers
        api_list = df['api_10'].dropna().unique().tolist()
        
        logger.info(f"Generated {len(api_list)} unique orphan well APIs from OCC registry")
        
        return api_list
    
    def get_orphan_registry_with_context(self, force_refresh: bool = False) -> pd.DataFrame:
        """
        Get complete orphan registry with OCC context data
        
        Args:
            force_refresh: If True, download fresh OCC data
            
        Returns:
            DataFrame with orphan wells and OCC regulatory context
        """
        
        df = self.download_occ_orphan_registry(force_refresh)
        df = self.normalize_api_numbers(df)
        
        # Add analysis metadata
        df['occ_registry_date'] = datetime.now().isoformat()
        df['data_source'] = 'OCC_RBDMS_Orphan_Registry'
        
        return df


class AuthoritativeOrphanAnalyzer:
    """
    Orphan well analyzer using OCC as authoritative source, WellDatabase for technical data
    """
    
    def __init__(self, welldatabase_client=None):
        self.occ = OCCOrphanRegistry()
        self.wb_client = welldatabase_client
        
    def get_authoritative_orphan_list(self, force_refresh: bool = False) -> Tuple[List[str], pd.DataFrame]:
        """
        Get authoritative orphan well list from OCC with full context
        
        Args:
            force_refresh: If True, download fresh OCC data
            
        Returns:
            Tuple of (api_list, occ_context_dataframe)
        """
        
        logger.info("Getting authoritative orphan well list from OCC...")
        
        # Get API list for WellDatabase lookup
        api_list = self.occ.get_orphan_api_list(force_refresh)
        
        # Get full registry with context
        occ_context = self.occ.get_orphan_registry_with_context(force_refresh)
        
        logger.info(f"Authoritative orphan list: {len(api_list)} wells from OCC registry")
        
        return api_list, occ_context
    
    def hydrate_with_welldatabase(self, api_list: List[str]) -> List[Dict]:
        """
        Hydrate OCC orphan list with WellDatabase technical data
        
        Args:
            api_list: List of API numbers from OCC orphan registry
            
        Returns:
            List of well records with WellDatabase data
        """
        
        if not self.wb_client:
            logger.warning("No WellDatabase client provided - cannot hydrate technical data")
            return []
        
        logger.info(f"Hydrating {len(api_list)} orphan wells with WellDatabase technical data...")
        
        hydrated_wells = []
        
        for i, api in enumerate(api_list):
            if i % 50 == 0:
                logger.info(f"Hydrating well {i+1}/{len(api_list)}: {api}")
            
            try:
                # Look up well in WellDatabase
                well = self.wb_client.get_well_by_api(api)
                
                if well:
                    well['occ_orphan_confirmed'] = True
                    well['data_source'] = 'OCC_Registry + WellDatabase'
                    hydrated_wells.append(well)
                else:
                    # Well in OCC but not found in WellDatabase
                    logger.warning(f"Orphan well {api} not found in WellDatabase")
                    hydrated_wells.append({
                        'api_10': api,
                        'wellName': f'OCC_ORPHAN_{api}',
                        'occ_orphan_confirmed': True,
                        'welldatabase_found': False,
                        'data_source': 'OCC_Registry_Only'
                    })
                    
            except Exception as e:
                logger.error(f"Error hydrating well {api}: {e}")
                continue
        
        logger.info(f"Successfully hydrated {len(hydrated_wells)} orphan wells")
        
        return hydrated_wells
    
    def analyze_coverage_comparison(self) -> Dict:
        """
        Compare OCC orphan registry vs WellDatabase status-based filtering
        
        Returns:
            Dict with comparison statistics
        """
        
        logger.info("Analyzing coverage comparison: OCC vs WellDatabase filtering...")
        
        # Get OCC authoritative list
        occ_api_list, occ_context = self.get_authoritative_orphan_list()
        
        comparison = {
            'occ_orphan_count': len(occ_api_list),
            'occ_source': 'Oklahoma Corporation Commission RBDMS Registry',
            'analysis_date': datetime.now().isoformat(),
            'coverage_analysis': {
                'authoritative_source': 'OCC is the legal authority for orphan well designation in Oklahoma',
                'recommended_method': 'Use OCC registry as inclusion list, WellDatabase for technical hydration',
                'risk_of_wb_only': 'Status-based filtering may miss 20-50% of actual orphaned wells'
            }
        }
        
        # If WellDatabase client available, compare with status filtering
        if self.wb_client:
            try:
                orphan_statuses = ["Orphaned - Completed - Not Active", "Orphaned - Shut In"]
                wb_result = self.wb_client.get_orphaned_wells(
                    state_id=35,
                    orphan_statuses=orphan_statuses,
                    page_size=1  # Just get count
                )
                
                wb_count = wb_result.get('total', 0)
                
                comparison['welldatabase_status_count'] = wb_count
                comparison['coverage_gap'] = {
                    'occ_authoritative': len(occ_api_list),
                    'wb_status_filtering': wb_count,
                    'methodology_difference': abs(len(occ_api_list) - wb_count),
                    'recommended_source': 'OCC (authoritative regulatory data)'
                }
                
            except Exception as e:
                logger.error(f"Error comparing with WellDatabase: {e}")
        
        return comparison


# Example usage and validation functions
def validate_occ_methodology():
    """Validate the OCC-based methodology"""
    
    print("🔍 VALIDATING OCC-BASED ORPHAN IDENTIFICATION")
    print("=" * 60)
    
    # Initialize OCC registry
    occ = OCCOrphanRegistry()
    
    try:
        # Download and analyze OCC data
        df = occ.download_occ_orphan_registry()
        df = occ.normalize_api_numbers(df)
        
        print(f"✅ Successfully downloaded OCC orphan registry")
        print(f"   Total orphan wells: {len(df)}")
        print(f"   Data source: Oklahoma Corporation Commission")
        print(f"   Registry fields: {list(df.columns)}")
        
        # Show sample data
        print(f"\n📋 Sample orphan wells from OCC registry:")
        for i, row in df.head(5).iterrows():
            api = row.get('api_10', 'Unknown')
            print(f"   {i+1}. API: {api}")
        
        # Get API list
        api_list = occ.get_orphan_api_list()
        print(f"\n🎯 Generated {len(api_list)} unique API numbers for WellDatabase lookup")
        
        return True
        
    except Exception as e:
        print(f"❌ Error validating OCC methodology: {e}")
        return False


if __name__ == "__main__":
    validate_occ_methodology()