#!/usr/bin/env python3
"""
Manual Orphaned Well Reactivation Analyzer
For when you have production data from other sources (OCC, etc.)
"""

import pandas as pd
from datetime import datetime
from pathlib import Path
import json

class ManualReactivationAnalyzer:
    """Analyze wells using manually provided production data"""
    
    def __init__(self, output_dir="output/manual_reactivation"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Production thresholds for categorization
        self.thresholds = {
            'high_consistent': 4000,      # MCF/month consistent production
            'surge_peak': 20000,          # MCF/month for surge identification
            'viable_minimum': 1000,       # MCF/month minimum viable
            'analysis_months': 24         # Months to analyze before orphaning
        }
    
    def analyze_well_from_data(self, well_info, production_data):
        """
        Analyze a single well using manually provided production data
        
        well_info: dict with well details (name, api, status, etc.)
        production_data: list of dicts with {date, gas_mcf, oil_bbl} or CSV file path
        """
        
        print(f"🔍 ANALYZING: {well_info.get('name', 'Unknown')} ({well_info.get('api', 'Unknown')})")
        print("=" * 60)
        
        # Load production data
        if isinstance(production_data, str):
            # CSV file path
            df = pd.read_csv(production_data)
        elif isinstance(production_data, list):
            # List of production records
            df = pd.DataFrame(production_data)
        else:
            print("❌ Invalid production data format")
            return None
        
        # Ensure required columns exist
        if 'gas_mcf' not in df.columns or 'date' not in df.columns:
            print("❌ Production data must have 'date' and 'gas_mcf' columns")
            return None
        
        # Clean and process data
        df['date'] = pd.to_datetime(df['date'])
        df['gas_mcf'] = pd.to_numeric(df['gas_mcf'], errors='coerce').fillna(0)
        df = df[df['gas_mcf'] > 0].sort_values('date')  # Remove zero production
        
        if df.empty:
            return {
                'category': 'NO_PRODUCTION',
                'category_name': '❌ NO HISTORICAL PRODUCTION',
                'reactivation_score': 0,
                'analysis': 'No positive production months found'
            }
        
        # Get recent production (last 24 months of data)
        recent_df = df.tail(self.thresholds['analysis_months'])
        
        # Calculate key metrics
        total_months = len(df)
        recent_months = len(recent_df)
        max_production = df['gas_mcf'].max()
        recent_max = recent_df['gas_mcf'].max() if not recent_df.empty else 0
        recent_avg = recent_df['gas_mcf'].mean() if not recent_df.empty else 0
        
        # Last 6 months specifically
        last_6_months = df.tail(6)
        last_6_avg = last_6_months['gas_mcf'].mean() if not last_6_months.empty else 0
        
        # Count months above thresholds
        consistent_4k_months = len(recent_df[recent_df['gas_mcf'] >= self.thresholds['high_consistent']])
        surge_months = len(recent_df[recent_df['gas_mcf'] >= self.thresholds['surge_peak']])
        viable_months = len(recent_df[recent_df['gas_mcf'] >= self.thresholds['viable_minimum']])
        
        # Calculate production timeline
        first_production = df['date'].min()
        last_production = df['date'].max()
        production_span_years = (last_production - first_production).days / 365.25
        
        # Analyze recent trends (last 12 months vs previous 12)
        if len(df) >= 24:
            last_12 = df.tail(12)['gas_mcf'].mean()
            prev_12 = df.iloc[-24:-12]['gas_mcf'].mean() if len(df) >= 24 else 0
            trend = "↗️ INCREASING" if last_12 > prev_12 * 1.1 else "↘️ DECLINING" if last_12 < prev_12 * 0.9 else "➡️ STABLE"
        else:
            trend = "📊 INSUFFICIENT DATA"
        
        # Print detailed analysis
        print(f"📊 PRODUCTION METRICS:")
        print(f"   Total producing months: {total_months}")
        print(f"   Production span: {production_span_years:.1f} years ({first_production.strftime('%Y-%m')} to {last_production.strftime('%Y-%m')})")
        print(f"   Max monthly production: {max_production:,.0f} MCF")
        print(f"   Recent months analyzed: {recent_months}")
        print(f"   Recent max: {recent_max:,.0f} MCF")
        print(f"   Recent average: {recent_avg:,.0f} MCF")
        print(f"   Last 6 months average: {last_6_avg:,.0f} MCF")
        print(f"   Production trend: {trend}")
        
        print(f"\n📋 THRESHOLD ANALYSIS:")
        print(f"   Months above 4k MCF: {consistent_4k_months}/{recent_months}")
        print(f"   Months above 20k MCF: {surge_months}/{recent_months}")
        print(f"   Months above 1k MCF: {viable_months}/{recent_months}")
        
        # Categorization logic
        category_analysis = {
            'total_months': total_months,
            'recent_months_analyzed': recent_months,
            'max_production_ever': max_production,
            'recent_max_production': recent_max,
            'recent_avg_production': recent_avg,
            'last_6_months_avg': last_6_avg,
            'months_above_4k': consistent_4k_months,
            'months_above_20k': surge_months,
            'months_above_1k': viable_months,
            'production_span_years': production_span_years,
            'trend': trend
        }
        
        # Decision tree for categorization
        if consistent_4k_months >= 6 and recent_avg >= self.thresholds['high_consistent']:
            result = {
                'category': 'HIGH_POTENTIAL',
                'category_name': '🏆 HIGH POTENTIAL - Consistent 4k+ MCF',
                'reactivation_score': 95,
                'analysis': f"Consistent high production: {consistent_4k_months} months above 4k MCF, recent avg: {recent_avg:,.0f}",
                'metrics': category_analysis
            }
        elif surge_months >= 1 and recent_max >= self.thresholds['surge_peak']:
            result = {
                'category': 'SURGE_POTENTIAL',
                'category_name': '⚡ SURGE POTENTIAL - Recent 20k+ MCF peaks',
                'reactivation_score': 85,
                'analysis': f"Strong recent peaks: {surge_months} months above 20k MCF, max: {recent_max:,.0f}",
                'metrics': category_analysis
            }
        elif viable_months >= 3 and recent_avg >= self.thresholds['viable_minimum']:
            result = {
                'category': 'DECLINING_VIABLE',
                'category_name': '📈 DECLINING BUT VIABLE - 1k-4k MCF range',
                'reactivation_score': 70,
                'analysis': f"Viable production: {viable_months} months above 1k MCF, recent avg: {recent_avg:,.0f}",
                'metrics': category_analysis
            }
        elif max_production >= self.thresholds['surge_peak']:
            result = {
                'category': 'SPORADIC_STRONG',
                'category_name': '🔍 SPORADIC BUT STRONG HISTORY',
                'reactivation_score': 60,
                'analysis': f"Historical strength: Max {max_production:,.0f} MCF, recent performance variable",
                'metrics': category_analysis
            }
        elif max_production >= self.thresholds['viable_minimum']:
            result = {
                'category': 'SPORADIC_MODERATE',
                'category_name': '🔍 SPORADIC MODERATE HISTORY',
                'reactivation_score': 40,
                'analysis': f"Moderate history: Max {max_production:,.0f} MCF, limited recent activity",
                'metrics': category_analysis
            }
        else:
            result = {
                'category': 'LOW_POTENTIAL',
                'category_name': '❌ LOW REACTIVATION POTENTIAL',
                'reactivation_score': 20,
                'analysis': f"Limited production: Max {max_production:,.0f} MCF, poor recent performance",
                'metrics': category_analysis
            }
        
        # Print categorization result
        print(f"\n🎯 REACTIVATION ASSESSMENT:")
        print(f"   Category: {result['category_name']}")
        print(f"   Score: {result['reactivation_score']}/100")
        print(f"   Analysis: {result['analysis']}")
        
        # Business recommendations
        print(f"\n💡 BUSINESS RECOMMENDATIONS:")
        if result['reactivation_score'] >= 85:
            print(f"   🎯 HIGH PRIORITY TARGET - Proceed to Phase 1 field survey immediately")
            print(f"   💰 Strong reactivation potential - consider fast-track acquisition")
            print(f"   🔬 Minimal reservoir validation needed - historical data supports viability")
        elif result['reactivation_score'] >= 70:
            print(f"   📊 SOLID CANDIDATE - Include in Phase 2 reservoir validation")
            print(f"   🔍 Worth detailed technical assessment")
            print(f"   💼 Good addition to portfolio mix")
        elif result['reactivation_score'] >= 50:
            print(f"   ⚠️  CONDITIONAL TARGET - Requires careful Phase 2 analysis")
            print(f"   🔬 Need reservoir engineering validation")
            print(f"   💵 Lower priority unless exceptional circumstances")
        else:
            print(f"   ❌ LOW PRIORITY - Consider only if part of package deal")
            print(f"   📉 Reactivation risk high")
        
        # Export detailed analysis
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save well analysis
        well_result = {
            **well_info,
            **result,
            'analysis_date': timestamp
        }
        
        analysis_file = self.output_dir / f"well_analysis_{well_info.get('api', 'unknown').replace('-', '')}_{timestamp}.json"
        with open(analysis_file, 'w') as f:
            json.dump(well_result, f, indent=2, default=str)
        
        # Save production data
        production_file = self.output_dir / f"production_data_{well_info.get('api', 'unknown').replace('-', '')}_{timestamp}.csv"
        df.to_csv(production_file, index=False)
        
        print(f"\n💾 EXPORTS:")
        print(f"   Analysis: {analysis_file}")
        print(f"   Production Data: {production_file}")
        
        return result

def create_sample_data():
    """Create sample production data based on the well in your screenshot"""
    
    # Sample data that matches what you showed in the screenshot
    sample_production = [
        {'date': '2010-01', 'gas_mcf': 15000},
        {'date': '2010-02', 'gas_mcf': 18000},
        {'date': '2010-03', 'gas_mcf': 22000},  # Surge month
        {'date': '2010-04', 'gas_mcf': 19000},
        {'date': '2010-05', 'gas_mcf': 16000},
        {'date': '2010-06', 'gas_mcf': 14000},
        {'date': '2010-07', 'gas_mcf': 12000},
        {'date': '2010-08', 'gas_mcf': 11000},
        {'date': '2010-09', 'gas_mcf': 9000},
        {'date': '2010-10', 'gas_mcf': 8000},
        {'date': '2010-11', 'gas_mcf': 7000},
        {'date': '2010-12', 'gas_mcf': 6000},
        {'date': '2011-01', 'gas_mcf': 5500},
        {'date': '2011-02', 'gas_mcf': 5000},
        {'date': '2011-03', 'gas_mcf': 4500},
        {'date': '2011-04', 'gas_mcf': 4000},
        {'date': '2011-05', 'gas_mcf': 3500},
        {'date': '2011-06', 'gas_mcf': 3000},
        {'date': '2011-07', 'gas_mcf': 2500},
        {'date': '2011-08', 'gas_mcf': 2000},
        {'date': '2011-09', 'gas_mcf': 1500},
        {'date': '2011-10', 'gas_mcf': 1000},
        {'date': '2011-11', 'gas_mcf': 500},
        {'date': '2011-12', 'gas_mcf': 0}  # Well orphaned
    ]
    
    return sample_production

def main():
    """Demo the manual reactivation analyzer"""
    
    print("🔥 MANUAL ORPHANED WELL REACTIVATION ANALYZER")
    print("=" * 70)
    print("For wells with production data from OCC or other sources")
    print("=" * 70)
    
    analyzer = ManualReactivationAnalyzer()
    
    # Sample well info
    well_info = {
        'name': 'NEWCOMB 18-3',
        'api': '35-039-21577-0000',
        'status': 'Orphaned - Shut In',
        'operator': '4 OF US RESOURCES',
        'county': 'CUSTER',
        'state': 'OKLAHOMA'
    }
    
    # Use sample production data
    production_data = create_sample_data()
    
    # Analyze the well
    result = analyzer.analyze_well_from_data(well_info, production_data)
    
    print(f"\n🎯 ANALYSIS COMPLETE!")
    print(f"   This framework can now be used with real production data from OCC records")
    print(f"   or any other source where you can extract monthly MCF values.")

if __name__ == "__main__":
    main()