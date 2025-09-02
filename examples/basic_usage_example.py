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
    
    if well:
        print(f"✅ Found: {well['wellName']} ({well['apI10']})")
        print(f"   Status: {well['wellStatus']}")
        print(f"   Operator: {well.get('currentOperator', 'Unknown')}")
        print(f"   County: {well.get('county', 'Unknown')}")
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
        
        for i, well in enumerate(wells, 1):
            print(f"   {i}. {well['wellName']} ({well['apI10']})")
            print(f"      Status: {well['wellStatus']}")
            print(f"      County: {well.get('county', 'Unknown')}")
            
    except Exception as e:
        print(f"❌ Error finding orphaned wells: {e}")
    
    # Example 3: Analyze a well for reactivation potential
    print(f"\n🏆 EXAMPLE 3: Reactivation analysis")
    print("-" * 30)
    
    if well:  # Use the well we found in Example 1
        try:
            # Get production data
            print(f"   Getting production data for {well['wellName']}...")
            production_data = client.get_production_data(
                [well['wellId']], 
                '2000-01-01', 
                '2024-12-31'
            )
            
            production_records = production_data.get('data', [])
            print(f"   ✅ Found {len(production_records)} production records")
            
            # Analyze for reactivation potential
            analyzer = ReactivationAnalyzer()
            analysis = analyzer.analyze_well(production_records, well)
            
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