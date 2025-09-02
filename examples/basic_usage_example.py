#!/usr/bin/env python3
"""
Basic usage example for WellDatabase API client
Demonstrates orphaned well identification and analysis
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.api.client import WellDatabaseClient
from src.analysis.reactivation import ReactivationAnalyzer
from src.config.constants import ORPHAN_STATUSES, OKLAHOMA_STATE_ID

def basic_api_example():
    """Basic example of using the WellDatabase API client"""
    
    print("🔧 BASIC WELLDATABASE API USAGE EXAMPLE")
    print("=" * 50)
    
    # Initialize the client
    try:
        client = WellDatabaseClient()
        print("✅ API client initialized")
        
        # Health check
        if client.health_check():
            print("✅ API connection verified")
        else:
            print("❌ API connection failed")
            return
            
    except Exception as e:
        print(f"❌ Failed to initialize client: {e}")
        return
    
    # Example 1: Find a specific well by API number
    print(f"\n📍 EXAMPLE 1: Find specific well")
    print("-" * 30)
    
    api_number = "35-039-21577-0000"
    well = client.get_well_by_api(api_number)
    
    target_well = well
    if target_well:
        api10 = well.get('api10') or well.get('apI10') or 'Unknown'
        print(f"✅ Found: {target_well.get('wellName','Unknown')} ({api10})")
        print(f"   Status: {target_well.get('status', target_well.get('wellStatus','Unknown'))}")
        print(f"   Operator: {target_well.get('operator', target_well.get('currentOperator', 'Unknown'))}")
        print(f"   County: {target_well.get('county', 'Unknown')}")
    else:
        print(f"❌ Well not found: {api_number}")
    
    # Example 2: Find orphaned wells in Oklahoma
    print(f"\n🎯 EXAMPLE 2: Find orphaned wells")
    print("-" * 30)
    
    try:
        orphan_wells = client.get_orphaned_wells(
            state_id=OKLAHOMA_STATE_ID,
            orphan_statuses=ORPHAN_STATUSES,
            page_size=5  # Just get a few examples
        )
        
        wells = orphan_wells.get('data', [])
        total = orphan_wells.get('total', 0)
        
        print(f"✅ Found {total:,} orphaned wells in Oklahoma")
        print(f"   Showing first {len(wells)} wells:")
        
        for i, ow in enumerate(wells, 1):
            print(f"   {i}. {ow.get('wellName','Unknown')} ({ow.get('api10', ow.get('apI10','Unknown'))})")
            print(f"      Status: {ow.get('status', ow.get('wellStatus','Unknown'))}")
            print(f"      County: {ow.get('county', 'Unknown')}")
            
    except Exception as e:
        print(f"❌ Error finding orphaned wells: {e}")
    
    # Example 3: Analyze a well for reactivation potential
    print(f"\n🏆 EXAMPLE 3: Reactivation analysis")
    print("-" * 30)
    
    if target_well:  # Use the well we found in Example 1
        try:
            # Get production data
            print(f"   Getting production data for {target_well.get('wellName','Unknown')}...")
            production_data = client.get_production_data(
                [target_well['wellId']], 
                '1990-01-01', 
                '2024-12-31',
                page_size=1000
            )
            production_records = production_data.get('data', [])
            # Check for any non-zero gas
            nonzero = [r for r in production_records if (r.get('wellGas') or r.get('totalGas') or 0) > 0]
            print(f"   ✅ /production/search returned {len(production_records)} rows; non-zero: {len(nonzero)}")
            
            # Analyze for reactivation potential
            analyzer = ReactivationAnalyzer()
            analysis = analyzer.analyze_well(production_records, target_well)
            
            print(f"   🎯 REACTIVATION ASSESSMENT:")
            print(f"      Category: {analysis['category_name']}")
            print(f"      Score: {analysis['reactivation_score']}/100")
            print(f"      Priority: {analysis['business_recommendations']['priority']}")
            print(f"      Analysis: {analysis['analysis']}")
            
        except Exception as e:
            print(f"   ❌ Error in reactivation analysis: {e}")
    
    # Close the client
    client.close()
    print(f"\n✅ Example completed successfully!")

if __name__ == "__main__":
    basic_api_example()