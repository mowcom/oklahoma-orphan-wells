#!/usr/bin/env python3
"""
Sample Reactivation Report for API 35-039-21577-0000 (NEWCOMB 18-3)
Demonstrates the complete reactivation analysis workflow
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

import pandas as pd
import json
from datetime import datetime
from pathlib import Path

from src.analysis.reactivation import ReactivationAnalyzer
from src.config.constants import REACTIVATION_CATEGORIES

def create_sample_production_data():
    """
    Create realistic production data based on typical Oklahoma well patterns
    This represents what would come from WellDatabase API or OCC records
    """
    
    # Sample production data pattern: Strong initial production with natural decline
    sample_production = [
        # Initial high production period (2008-2009)
        {'reportDate': '2008-04-01T00:00:00', 'reportYear': 2008, 'reportMonth': 4, 'wellGas': 28000, 'totalGas': 28000, 'operator': 'NEWCOMB ENERGY LLC'},
        {'reportDate': '2008-05-01T00:00:00', 'reportYear': 2008, 'reportMonth': 5, 'wellGas': 32000, 'totalGas': 32000, 'operator': 'NEWCOMB ENERGY LLC'},
        {'reportDate': '2008-06-01T00:00:00', 'reportYear': 2008, 'reportMonth': 6, 'wellGas': 35000, 'totalGas': 35000, 'operator': 'NEWCOMB ENERGY LLC'},
        {'reportDate': '2008-07-01T00:00:00', 'reportYear': 2008, 'reportMonth': 7, 'wellGas': 38000, 'totalGas': 38000, 'operator': 'NEWCOMB ENERGY LLC'},
        {'reportDate': '2008-08-01T00:00:00', 'reportYear': 2008, 'reportMonth': 8, 'wellGas': 41000, 'totalGas': 41000, 'operator': 'NEWCOMB ENERGY LLC'},  # Peak month
        {'reportDate': '2008-09-01T00:00:00', 'reportYear': 2008, 'reportMonth': 9, 'wellGas': 36000, 'totalGas': 36000, 'operator': 'NEWCOMB ENERGY LLC'},
        {'reportDate': '2008-10-01T00:00:00', 'reportYear': 2008, 'reportMonth': 10, 'wellGas': 33000, 'totalGas': 33000, 'operator': 'NEWCOMB ENERGY LLC'},
        {'reportDate': '2008-11-01T00:00:00', 'reportYear': 2008, 'reportMonth': 11, 'wellGas': 29000, 'totalGas': 29000, 'operator': 'NEWCOMB ENERGY LLC'},
        {'reportDate': '2008-12-01T00:00:00', 'reportYear': 2008, 'reportMonth': 12, 'wellGas': 26000, 'totalGas': 26000, 'operator': 'NEWCOMB ENERGY LLC'},
        
        # Continued strong production (2009)
        {'reportDate': '2009-01-01T00:00:00', 'reportYear': 2009, 'reportMonth': 1, 'wellGas': 24000, 'totalGas': 24000, 'operator': 'NEWCOMB ENERGY LLC'},
        {'reportDate': '2009-02-01T00:00:00', 'reportYear': 2009, 'reportMonth': 2, 'wellGas': 22000, 'totalGas': 22000, 'operator': 'NEWCOMB ENERGY LLC'},
        {'reportDate': '2009-03-01T00:00:00', 'reportYear': 2009, 'reportMonth': 3, 'wellGas': 21000, 'totalGas': 21000, 'operator': 'NEWCOMB ENERGY LLC'},
        {'reportDate': '2009-04-01T00:00:00', 'reportYear': 2009, 'reportMonth': 4, 'wellGas': 19000, 'totalGas': 19000, 'operator': 'NEWCOMB ENERGY LLC'},
        {'reportDate': '2009-05-01T00:00:00', 'reportYear': 2009, 'reportMonth': 5, 'wellGas': 18000, 'totalGas': 18000, 'operator': 'NEWCOMB ENERGY LLC'},
        {'reportDate': '2009-06-01T00:00:00', 'reportYear': 2009, 'reportMonth': 6, 'wellGas': 16000, 'totalGas': 16000, 'operator': 'NEWCOMB ENERGY LLC'},
        {'reportDate': '2009-07-01T00:00:00', 'reportYear': 2009, 'reportMonth': 7, 'wellGas': 15000, 'totalGas': 15000, 'operator': 'NEWCOMB ENERGY LLC'},
        {'reportDate': '2009-08-01T00:00:00', 'reportYear': 2009, 'reportMonth': 8, 'wellGas': 14000, 'totalGas': 14000, 'operator': 'NEWCOMB ENERGY LLC'},
        {'reportDate': '2009-09-01T00:00:00', 'reportYear': 2009, 'reportMonth': 9, 'wellGas': 13000, 'totalGas': 13000, 'operator': 'NEWCOMB ENERGY LLC'},
        {'reportDate': '2009-10-01T00:00:00', 'reportYear': 2009, 'reportMonth': 10, 'wellGas': 12000, 'totalGas': 12000, 'operator': 'NEWCOMB ENERGY LLC'},
        {'reportDate': '2009-11-01T00:00:00', 'reportYear': 2009, 'reportMonth': 11, 'wellGas': 11000, 'totalGas': 11000, 'operator': 'NEWCOMB ENERGY LLC'},
        {'reportDate': '2009-12-01T00:00:00', 'reportYear': 2009, 'reportMonth': 12, 'wellGas': 10000, 'totalGas': 10000, 'operator': 'NEWCOMB ENERGY LLC'},
        
        # Natural decline period (2010-2011)
        {'reportDate': '2010-01-01T00:00:00', 'reportYear': 2010, 'reportMonth': 1, 'wellGas': 9500, 'totalGas': 9500, 'operator': 'NEWCOMB ENERGY LLC'},
        {'reportDate': '2010-02-01T00:00:00', 'reportYear': 2010, 'reportMonth': 2, 'wellGas': 8800, 'totalGas': 8800, 'operator': 'NEWCOMB ENERGY LLC'},
        {'reportDate': '2010-03-01T00:00:00', 'reportYear': 2010, 'reportMonth': 3, 'wellGas': 8200, 'totalGas': 8200, 'operator': 'NEWCOMB ENERGY LLC'},
        {'reportDate': '2010-04-01T00:00:00', 'reportYear': 2010, 'reportMonth': 4, 'wellGas': 7600, 'totalGas': 7600, 'operator': 'NEWCOMB ENERGY LLC'},
        {'reportDate': '2010-05-01T00:00:00', 'reportYear': 2010, 'reportMonth': 5, 'wellGas': 7000, 'totalGas': 7000, 'operator': 'NEWCOMB ENERGY LLC'},
        {'reportDate': '2010-06-01T00:00:00', 'reportYear': 2010, 'reportMonth': 6, 'wellGas': 6500, 'totalGas': 6500, 'operator': 'NEWCOMB ENERGY LLC'},
        {'reportDate': '2010-07-01T00:00:00', 'reportYear': 2010, 'reportMonth': 7, 'wellGas': 6000, 'totalGas': 6000, 'operator': 'NEWCOMB ENERGY LLC'},
        {'reportDate': '2010-08-01T00:00:00', 'reportYear': 2010, 'reportMonth': 8, 'wellGas': 5500, 'totalGas': 5500, 'operator': 'NEWCOMB ENERGY LLC'},
        {'reportDate': '2010-09-01T00:00:00', 'reportYear': 2010, 'reportMonth': 9, 'wellGas': 5000, 'totalGas': 5000, 'operator': 'NEWCOMB ENERGY LLC'},
        {'reportDate': '2010-10-01T00:00:00', 'reportYear': 2010, 'reportMonth': 10, 'wellGas': 4500, 'totalGas': 4500, 'operator': 'NEWCOMB ENERGY LLC'},
        {'reportDate': '2010-11-01T00:00:00', 'reportYear': 2010, 'reportMonth': 11, 'wellGas': 4200, 'totalGas': 4200, 'operator': 'NEWCOMB ENERGY LLC'},
        {'reportDate': '2010-12-01T00:00:00', 'reportYear': 2010, 'reportMonth': 12, 'wellGas': 3800, 'totalGas': 3800, 'operator': 'NEWCOMB ENERGY LLC'},
        
        # Final producing period before orphaning (2011)
        {'reportDate': '2011-01-01T00:00:00', 'reportYear': 2011, 'reportMonth': 1, 'wellGas': 3500, 'totalGas': 3500, 'operator': '4 OF US RESOURCES'},
        {'reportDate': '2011-02-01T00:00:00', 'reportYear': 2011, 'reportMonth': 2, 'wellGas': 3200, 'totalGas': 3200, 'operator': '4 OF US RESOURCES'},
        {'reportDate': '2011-03-01T00:00:00', 'reportYear': 2011, 'reportMonth': 3, 'wellGas': 2900, 'totalGas': 2900, 'operator': '4 OF US RESOURCES'},
        {'reportDate': '2011-04-01T00:00:00', 'reportYear': 2011, 'reportMonth': 4, 'wellGas': 2600, 'totalGas': 2600, 'operator': '4 OF US RESOURCES'},
        {'reportDate': '2011-05-01T00:00:00', 'reportYear': 2011, 'reportMonth': 5, 'wellGas': 2300, 'totalGas': 2300, 'operator': '4 OF US RESOURCES'},
        {'reportDate': '2011-06-01T00:00:00', 'reportYear': 2011, 'reportMonth': 6, 'wellGas': 2000, 'totalGas': 2000, 'operator': '4 OF US RESOURCES'},
        {'reportDate': '2011-07-01T00:00:00', 'reportYear': 2011, 'reportMonth': 7, 'wellGas': 1800, 'totalGas': 1800, 'operator': '4 OF US RESOURCES'},
        {'reportDate': '2011-08-01T00:00:00', 'reportYear': 2011, 'reportMonth': 8, 'wellGas': 1500, 'totalGas': 1500, 'operator': '4 OF US RESOURCES'},
        {'reportDate': '2011-09-01T00:00:00', 'reportYear': 2011, 'reportMonth': 9, 'wellGas': 1200, 'totalGas': 1200, 'operator': '4 OF US RESOURCES'},
        {'reportDate': '2011-10-01T00:00:00', 'reportYear': 2011, 'reportMonth': 10, 'wellGas': 1000, 'totalGas': 1000, 'operator': '4 OF US RESOURCES'},
        # Well went orphaned after October 2011
    ]
    
    return sample_production

def generate_sample_report():
    """Generate comprehensive sample reactivation report"""
    
    print("🔥 SAMPLE REACTIVATION REPORT")
    print("=" * 80)
    print("API Number: 35-039-21577-0000 (NEWCOMB 18-3)")
    print("Analysis Date:", datetime.now().strftime("%B %d, %Y"))
    print("=" * 80)
    
    # Well information
    well_info = {
        'name': 'NEWCOMB 18-3',
        'api': '35-039-21577-0000',
        'api_10': '3503921577',
        'status': 'Orphaned - Shut In',
        'current_operator': '4 OF US RESOURCES',
        'previous_operators': ['NEWCOMB ENERGY LLC', '4 OF US RESOURCES'],
        'county': 'CUSTER',
        'state': 'OKLAHOMA',
        'spud_date': '2008-03-15',
        'completion_date': '2008-03-28',
        'total_depth': 12450,
        'latitude': 35.123456,
        'longitude': -98.654321,
        'lease_name': 'NEWCOMB 18-3',
        'field': 'WEATHERFORD'
    }
    
    # Get sample production data
    production_data = create_sample_production_data()
    
    # Initialize analyzer and analyze well
    analyzer = ReactivationAnalyzer()
    result = analyzer.analyze_well(production_data, well_info)
    
    # Print detailed analysis
    print("\n🎯 REACTIVATION ASSESSMENT")
    print("-" * 40)
    print(f"Category: {result['category_name']}")
    print(f"Reactivation Score: {result['reactivation_score']}/100")
    print(f"Analysis: {result['analysis']}")
    
    print(f"\n📊 PRODUCTION METRICS")
    print("-" * 40)
    metrics = result['metrics']
    print(f"Total Producing Months: {metrics.get('total_months', 0)}")
    print(f"Production Timespan: {metrics.get('production_span_years', 0):.1f} years")
    print(f"First Production: {metrics.get('first_production_date', 'Unknown').strftime('%B %Y') if metrics.get('first_production_date') else 'Unknown'}")
    print(f"Last Production: {metrics.get('last_production_date', 'Unknown').strftime('%B %Y') if metrics.get('last_production_date') else 'Unknown'}")
    print(f"Peak Monthly Production: {metrics.get('max_production_ever', 0):,.0f} MCF")
    print(f"Total Cumulative Production: {metrics.get('total_production', 0):,.0f} MCF")
    print(f"Average Monthly Production: {metrics.get('avg_production', 0):,.0f} MCF")
    print(f"Production Trend: {metrics.get('production_trend', 'Unknown')}")
    
    print(f"\n📋 THRESHOLD ANALYSIS")
    print("-" * 40)
    print(f"Recent months analyzed: {metrics.get('recent_months_analyzed', 0)}")
    print(f"Months above 4,000 MCF: {metrics.get('months_above_4k', 0)}")
    print(f"Months above 20,000 MCF: {metrics.get('months_above_20k', 0)}")
    print(f"Months above 1,000 MCF: {metrics.get('months_above_1k', 0)}")
    print(f"Recent average production: {metrics.get('recent_avg_production', 0):,.0f} MCF/month")
    print(f"Recent maximum production: {metrics.get('recent_max_production', 0):,.0f} MCF/month")
    
    print(f"\n💼 BUSINESS RECOMMENDATIONS")
    print("-" * 40)
    recommendations = result['business_recommendations']
    print(f"Priority Level: {recommendations['priority']}")
    print(f"Recommended Action: {recommendations['action']}")
    print(f"Timeline: {recommendations['timeline']}")
    print(f"Investment Assessment: {recommendations['investment']}")
    print(f"Risk Level: {recommendations['risk_level']}")
    
    print(f"\nNext Steps:")
    for i, step in enumerate(recommendations['next_steps'], 1):
        print(f"   {i}. {step}")
    
    print(f"\n🗺️  WELL DETAILS")
    print("-" * 40)
    print(f"Well Name: {well_info['name']}")
    print(f"API Number: {well_info['api']}")
    print(f"Current Status: {well_info['status']}")
    print(f"Current Operator: {well_info['current_operator']}")
    print(f"Location: {well_info['county']} County, {well_info['state']}")
    print(f"Spud Date: {well_info['spud_date']}")
    print(f"Completion Date: {well_info['completion_date']}")
    print(f"Total Depth: {well_info['total_depth']:,} feet")
    print(f"Field: {well_info['field']}")
    
    print(f"\n📈 PRODUCTION TIMELINE")
    print("-" * 40)
    
    # Create production summary by year
    df = pd.DataFrame(production_data)
    df['gas_mcf'] = df['wellGas']
    df['year'] = df['reportYear']
    
    yearly_summary = df.groupby('year').agg({
        'gas_mcf': ['sum', 'mean', 'max', 'count']
    }).round(0)
    
    yearly_summary.columns = ['Annual_Total', 'Monthly_Avg', 'Monthly_Max', 'Months_Produced']
    
    print("Year    Annual Total    Monthly Avg    Monthly Max    Months")
    print("-" * 60)
    for year, row in yearly_summary.iterrows():
        print(f"{year}    {row['Annual_Total']:>9,.0f} MCF   {row['Monthly_Avg']:>7,.0f} MCF   {row['Monthly_Max']:>7,.0f} MCF      {row['Months_Produced']:.0f}")
    
    print(f"\n🎯 REACTIVATION OPPORTUNITY ANALYSIS")
    print("-" * 40)
    
    total_production = metrics.get('total_production', 0)
    avg_monthly = metrics.get('avg_production', 0)
    
    # Economic assessment (simplified)
    estimated_reserves = avg_monthly * 12  # Rough estimate for remaining annual potential
    gas_price_per_mcf = 3.50  # Assumed price
    annual_revenue_potential = estimated_reserves * gas_price_per_mcf
    
    print(f"Cumulative Historical Production: {total_production:,.0f} MCF")
    print(f"Average Monthly Rate: {avg_monthly:,.0f} MCF")
    print(f"Estimated Annual Potential: {estimated_reserves:,.0f} MCF")
    print(f"Est. Annual Revenue Potential: ${annual_revenue_potential:,.0f} (@ ${gas_price_per_mcf:.2f}/MCF)")
    
    # Operator change analysis
    print(f"\n🏢 OPERATOR CHANGE HISTORY")
    print("-" * 40)
    print("2008-2010: NEWCOMB ENERGY LLC (Peak production period)")
    print("2011:      4 OF US RESOURCES (Final production, then orphaned)")
    print("\n💡 Analysis: Well became orphaned after operator change, suggesting")
    print("    financial distress rather than reservoir depletion")
    
    # Risk factors
    print(f"\n⚠️  RISK FACTORS TO CONSIDER")
    print("-" * 40)
    print("• Well has been shut-in since 2011 (13+ years)")
    print("• Wellbore condition unknown - may require workover")
    print("• Surface equipment likely deteriorated")
    print("• Title/ownership may be complex due to orphan status")
    print("• Infrastructure (pipelines, roads) condition uncertain")
    
    # Competitive advantages  
    print(f"\n✅ COMPETITIVE ADVANTAGES")
    print("-" * 40)
    print("• Proven production history with 41,000+ MCF peak months")
    print("• 39-month production history demonstrates reservoir viability")
    print("• Existing wellbore - no drilling costs")
    print("• Established field with existing infrastructure")
    print("• Clear regulatory pathway for orphan well acquisition")
    
    # Export the analysis
    output_dir = Path("reactivation/reports")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Save detailed JSON report
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_file = output_dir / f"reactivation_analysis_{well_info['api'].replace('-', '')}_{timestamp}.json"
    
    with open(json_file, 'w') as f:
        json.dump(result, f, indent=2, default=str)
    
    # Save production data
    csv_file = output_dir / f"production_data_{well_info['api'].replace('-', '')}_{timestamp}.csv"
    pd.DataFrame(production_data).to_csv(csv_file, index=False)
    
    print(f"\n💾 REPORTS SAVED")
    print("-" * 40)
    print(f"Detailed Analysis: {json_file}")
    print(f"Production Data: {csv_file}")
    
    print(f"\n🎯 SUMMARY RECOMMENDATION")
    print("=" * 80)
    
    if result['reactivation_score'] >= 85:
        print("🟢 STRONG REACTIVATION CANDIDATE")
        print("   This well demonstrates excellent reactivation potential with")
        print("   strong historical production and clear economic viability.")
        print("   Recommend immediate Phase 1 field survey and acquisition pursuit.")
        
    elif result['reactivation_score'] >= 70:
        print("🟡 VIABLE REACTIVATION CANDIDATE") 
        print("   This well shows solid reactivation potential but requires")
        print("   detailed technical assessment in Phase 2.")
        
    else:
        print("🔴 MARGINAL REACTIVATION CANDIDATE")
        print("   This well presents higher risk and should only be considered")
        print("   as part of a larger package deal.")
    
    return result

if __name__ == "__main__":
    result = generate_sample_report()
    print(f"\n✅ Sample report generated successfully!")
    print(f"   Score: {result['reactivation_score']}/100")
    print(f"   Category: {result['category']}")