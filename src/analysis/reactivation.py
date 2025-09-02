"""Reactivation potential analysis for orphaned wells"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta

from ..config.constants import (
    PRODUCTION_THRESHOLDS, REACTIVATION_CATEGORIES, 
    BUSINESS_PRIORITY, PRODUCTION_FIELDS
)

class ReactivationAnalyzer:
    """Analyze wells for reactivation potential based on historical production"""
    
    def __init__(self, thresholds: Dict = None):
        self.thresholds = thresholds or PRODUCTION_THRESHOLDS
    
    def analyze_well(self, production_records: List[Dict], well_info: Dict = None) -> Dict:
        """
        Analyze a single well for reactivation potential
        
        Args:
            production_records: List of production records from API
            well_info: Basic well information (name, API, etc.)
            
        Returns:
            Dict containing categorization, score, and analysis details
        """
        
        if not production_records:
            return self._create_result('NO_DATA', 0, 'No production data available')
        
        # Convert to DataFrame and clean data
        df = self._prepare_production_data(production_records)
        
        if df.empty:
            return self._create_result('NO_PRODUCTION', 0, 'No positive production months found')
        
        # Calculate production metrics
        metrics = self._calculate_production_metrics(df)
        
        # Categorize reactivation potential
        category, score, analysis = self._categorize_reactivation_potential(df, metrics)
        
        # Add business recommendations
        recommendations = self._generate_business_recommendations(score, category)
        
        return {
            'category': category,
            'category_name': REACTIVATION_CATEGORIES[category]['name'],
            'reactivation_score': score,
            'analysis': analysis,
            'metrics': metrics,
            'business_recommendations': recommendations,
            'well_info': well_info or {},
            'analysis_date': datetime.now().isoformat()
        }
    
    def _prepare_production_data(self, production_records: List[Dict]) -> pd.DataFrame:
        """Clean and prepare production data for analysis"""
        
        df = pd.DataFrame(production_records)
        
        if df.empty:
            return df
        
        # Extract gas production (primary field first, fallback second)
        gas_primary = PRODUCTION_FIELDS['gas_primary']
        gas_fallback = PRODUCTION_FIELDS['gas_fallback']
        
        # Try primary field first, then fallback
        if gas_primary in df.columns:
            gas_values = df[gas_primary]
        elif gas_fallback in df.columns:
            gas_values = df[gas_fallback]
        else:
            gas_values = pd.Series([0] * len(df))
        
        df['gas_mcf'] = pd.to_numeric(gas_values, errors='coerce').fillna(0)
        
        # Extract oil production
        oil_primary = PRODUCTION_FIELDS['oil_primary']
        oil_fallback = PRODUCTION_FIELDS['oil_fallback']
        
        # Try primary field first, then fallback
        if oil_primary in df.columns:
            oil_values = df[oil_primary]
        elif oil_fallback in df.columns:
            oil_values = df[oil_fallback]
        else:
            oil_values = pd.Series([0] * len(df))
        
        df['oil_bbl'] = pd.to_numeric(oil_values, errors='coerce').fillna(0)
        
        # Parse dates
        if PRODUCTION_FIELDS['date'] in df.columns:
            df['production_date'] = pd.to_datetime(df[PRODUCTION_FIELDS['date']], errors='coerce')
        elif PRODUCTION_FIELDS['year'] in df.columns and PRODUCTION_FIELDS['month'] in df.columns:
            df['production_date'] = pd.to_datetime(
                df[[PRODUCTION_FIELDS['year'], PRODUCTION_FIELDS['month']]].assign(day=1)
            )
        else:
            # No date information available
            return pd.DataFrame()
        
        # Remove zero production months and invalid dates
        df = df[
            (df['gas_mcf'] > 0) & 
            df['production_date'].notna()
        ].sort_values('production_date')
        
        return df
    
    def _calculate_production_metrics(self, df: pd.DataFrame) -> Dict:
        """Calculate key production metrics for analysis"""
        
        if df.empty:
            return {}
        
        # Basic metrics
        total_months = len(df)
        max_production = df['gas_mcf'].max()
        total_production = df['gas_mcf'].sum()
        avg_production = df['gas_mcf'].mean()
        
        # Date range
        first_production = df['production_date'].min()
        last_production = df['production_date'].max()
        production_span_years = (last_production - first_production).days / 365.25
        
        # Recent production (last 24 months of data)
        analysis_months = self.thresholds.get('ANALYSIS_MONTHS', 24)
        recent_df = df.tail(analysis_months)
        recent_months = len(recent_df)
        recent_max = recent_df['gas_mcf'].max() if not recent_df.empty else 0
        recent_avg = recent_df['gas_mcf'].mean() if not recent_df.empty else 0
        
        # Last 6 months specifically
        last_6_months = df.tail(6)
        last_6_avg = last_6_months['gas_mcf'].mean() if not last_6_months.empty else 0
        
        # Threshold analysis
        consistent_4k_months = len(recent_df[recent_df['gas_mcf'] >= self.thresholds.get('HIGH_CONSISTENT', 4000)])
        surge_months = len(recent_df[recent_df['gas_mcf'] >= self.thresholds.get('SURGE_PEAK', 20000)])
        viable_months = len(recent_df[recent_df['gas_mcf'] >= self.thresholds.get('VIABLE_MINIMUM', 1000)])
        
        # Production trend analysis
        trend = self._analyze_production_trend(df)
        
        return {
            'total_months': total_months,
            'max_production_ever': max_production,
            'total_production': total_production,
            'avg_production': avg_production,
            'first_production_date': first_production,
            'last_production_date': last_production,
            'production_span_years': production_span_years,
            'recent_months_analyzed': recent_months,
            'recent_max_production': recent_max,
            'recent_avg_production': recent_avg,
            'last_6_months_avg': last_6_avg,
            'months_above_4k': consistent_4k_months,
            'months_above_20k': surge_months,
            'months_above_1k': viable_months,
            'production_trend': trend
        }
    
    def _analyze_production_trend(self, df: pd.DataFrame) -> str:
        """Analyze production trend over time"""
        
        if len(df) < 12:
            return "INSUFFICIENT_DATA"
        
        # Compare last 12 months vs previous 12 months
        if len(df) >= 24:
            last_12 = df.tail(12)['gas_mcf'].mean()
            prev_12 = df.iloc[-24:-12]['gas_mcf'].mean()
            
            if last_12 > prev_12 * 1.1:
                return "INCREASING"
            elif last_12 < prev_12 * 0.9:
                return "DECLINING"
            else:
                return "STABLE"
        
        # Simple trend analysis for shorter datasets
        first_half = df.head(len(df)//2)['gas_mcf'].mean()
        second_half = df.tail(len(df)//2)['gas_mcf'].mean()
        
        if second_half > first_half * 1.1:
            return "INCREASING"
        elif second_half < first_half * 0.9:
            return "DECLINING"
        else:
            return "STABLE"
    
    def _categorize_reactivation_potential(self, df: pd.DataFrame, metrics: Dict) -> Tuple[str, int, str]:
        """Categorize well based on reactivation potential"""
        
        # Extract key metrics for decision making
        consistent_4k = metrics.get('months_above_4k', 0)
        surge_months = metrics.get('months_above_20k', 0)
        viable_months = metrics.get('months_above_1k', 0)
        recent_avg = metrics.get('recent_avg_production', 0)
        recent_max = metrics.get('recent_max_production', 0)
        max_ever = metrics.get('max_production_ever', 0)
        
        # Decision tree for categorization
        if consistent_4k >= 6 and recent_avg >= self.thresholds.get('HIGH_CONSISTENT', 4000):
            return ('HIGH_POTENTIAL', 95, 
                   f"Consistent high production: {consistent_4k} months above 4k MCF, recent avg: {recent_avg:,.0f}")
        
        elif surge_months >= 1 and recent_max >= self.thresholds.get('SURGE_PEAK', 20000):
            return ('SURGE_POTENTIAL', 85,
                   f"Strong recent peaks: {surge_months} months above 20k MCF, max: {recent_max:,.0f}")
        
        elif viable_months >= 3 and recent_avg >= self.thresholds.get('VIABLE_MINIMUM', 1000):
            return ('DECLINING_VIABLE', 70,
                   f"Viable production: {viable_months} months above 1k MCF, recent avg: {recent_avg:,.0f}")
        
        elif max_ever >= self.thresholds.get('SURGE_PEAK', 20000):
            return ('SPORADIC_STRONG', 60,
                   f"Historical strength: Max {max_ever:,.0f} MCF, recent performance variable")
        
        elif max_ever >= self.thresholds.get('VIABLE_MINIMUM', 1000):
            return ('SPORADIC_MODERATE', 40,
                   f"Moderate history: Max {max_ever:,.0f} MCF, limited recent activity")
        
        else:
            return ('LOW_POTENTIAL', 20,
                   f"Limited production: Max {max_ever:,.0f} MCF, poor recent performance")
    
    def _generate_business_recommendations(self, score: int, category: str) -> Dict:
        """Generate business recommendations based on score and category"""
        
        if score >= BUSINESS_PRIORITY['IMMEDIATE']:
            return {
                'priority': 'IMMEDIATE',
                'action': 'Fast-track to Phase 1 field survey',
                'timeline': 'Within 30 days',
                'investment': 'High confidence - consider fast-track acquisition',
                'risk_level': 'Low',
                'next_steps': [
                    'Schedule immediate site visit',
                    'Begin landowner contact',
                    'Prepare acquisition offer',
                    'Minimal reservoir validation needed'
                ]
            }
        
        elif score >= BUSINESS_PRIORITY['HIGH']:
            return {
                'priority': 'HIGH',
                'action': 'Include in Phase 2 reservoir validation',
                'timeline': 'Within 60 days',
                'investment': 'Worth detailed technical assessment',
                'risk_level': 'Low-Medium',
                'next_steps': [
                    'Field survey in next batch',
                    'Reservoir engineering review',
                    'Infrastructure assessment',
                    'Economic modeling'
                ]
            }
        
        elif score >= BUSINESS_PRIORITY['MODERATE']:
            return {
                'priority': 'MODERATE',
                'action': 'Conditional target - requires Phase 2 analysis',
                'timeline': 'Within 90 days',
                'investment': 'Lower priority unless exceptional circumstances',
                'risk_level': 'Medium',
                'next_steps': [
                    'Include in batch analysis',
                    'Detailed reservoir validation required',
                    'Economic sensitivity analysis',
                    'Consider as part of package deal'
                ]
            }
        
        else:
            return {
                'priority': 'LOW',
                'action': 'Consider only if part of package deal',
                'timeline': 'No immediate action',
                'investment': 'High risk - avoid individual acquisition',
                'risk_level': 'High',
                'next_steps': [
                    'Monitor for status changes',
                    'Consider for package deals only',
                    'Low priority for resources'
                ]
            }
    
    def _create_result(self, category: str, score: int, analysis: str) -> Dict:
        """Create standardized result dictionary"""
        
        return {
            'category': category,
            'category_name': REACTIVATION_CATEGORIES[category]['name'],
            'reactivation_score': score,
            'analysis': analysis,
            'metrics': {},
            'business_recommendations': self._generate_business_recommendations(score, category),
            'analysis_date': datetime.now().isoformat()
        }
    
    def batch_analyze_wells(self, wells_production_data: List[Tuple[Dict, List[Dict]]]) -> List[Dict]:
        """
        Analyze multiple wells in batch
        
        Args:
            wells_production_data: List of (well_info, production_records) tuples
            
        Returns:
            List of analysis results
        """
        
        results = []
        
        for well_info, production_records in wells_production_data:
            result = self.analyze_well(production_records, well_info)
            results.append(result)
        
        return results
    
    def generate_summary_report(self, analysis_results: List[Dict]) -> Dict:
        """Generate summary report from batch analysis results"""
        
        if not analysis_results:
            return {'error': 'No analysis results provided'}
        
        total_wells = len(analysis_results)
        
        # Category breakdown
        category_counts = {}
        score_distribution = []
        
        for result in analysis_results:
            category = result.get('category', 'UNKNOWN')
            score = result.get('reactivation_score', 0)
            
            category_counts[category] = category_counts.get(category, 0) + 1
            score_distribution.append(score)
        
        # Priority targets
        immediate_targets = [r for r in analysis_results if r.get('reactivation_score', 0) >= BUSINESS_PRIORITY['IMMEDIATE']]
        high_targets = [r for r in analysis_results if BUSINESS_PRIORITY['HIGH'] <= r.get('reactivation_score', 0) < BUSINESS_PRIORITY['IMMEDIATE']]
        
        return {
            'total_wells_analyzed': total_wells,
            'category_breakdown': category_counts,
            'score_statistics': {
                'mean': np.mean(score_distribution),
                'median': np.median(score_distribution),
                'max': np.max(score_distribution),
                'min': np.min(score_distribution)
            },
            'priority_targets': {
                'immediate_count': len(immediate_targets),
                'high_count': len(high_targets),
                'immediate_wells': [r.get('well_info', {}).get('api', 'Unknown') for r in immediate_targets[:10]],
                'high_wells': [r.get('well_info', {}).get('api', 'Unknown') for r in high_targets[:10]]
            },
            'analysis_date': datetime.now().isoformat()
        }