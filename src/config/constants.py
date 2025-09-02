"""Constants for well analysis and categorization"""

# Oklahoma State ID
OKLAHOMA_STATE_ID = 35

# Orphan Well Status Codes
ORPHAN_STATUSES = [
    "Orphaned - Completed - Not Active",
    "Orphaned - Shut In"
]

# Production Thresholds (MCF/month)
PRODUCTION_THRESHOLDS = {
    'HIGH_CONSISTENT': 4000,      # MCF/month for consistent high production
    'SURGE_PEAK': 20000,          # MCF/month for surge identification
    'VIABLE_MINIMUM': 1000,       # MCF/month minimum viable production
    'ANALYSIS_MONTHS': 24         # Months to analyze for recent production
}

# Reactivation Categories
REACTIVATION_CATEGORIES = {
    'HIGH_POTENTIAL': {
        'name': '🏆 HIGH POTENTIAL - Consistent 4k+ MCF',
        'score': 95,
        'min_score': 90
    },
    'SURGE_POTENTIAL': {
        'name': '⚡ SURGE POTENTIAL - Recent 20k+ MCF peaks',
        'score': 85,
        'min_score': 80
    },
    'DECLINING_VIABLE': {
        'name': '📈 DECLINING BUT VIABLE - 1k-4k MCF range',
        'score': 70,
        'min_score': 65
    },
    'SPORADIC_STRONG': {
        'name': '🔍 SPORADIC BUT STRONG HISTORY',
        'score': 60,
        'min_score': 50
    },
    'SPORADIC_MODERATE': {
        'name': '🔍 SPORADIC MODERATE HISTORY',
        'score': 40,
        'min_score': 30
    },
    'LOW_POTENTIAL': {
        'name': '❌ LOW REACTIVATION POTENTIAL',
        'score': 20,
        'min_score': 0
    },
    'NO_PRODUCTION': {
        'name': '❌ NO HISTORICAL PRODUCTION',
        'score': 0,
        'min_score': 0
    },
    'NO_DATA': {
        'name': '❌ NO PRODUCTION DATA',
        'score': 0,
        'min_score': 0
    }
}

# Business Priority Thresholds
BUSINESS_PRIORITY = {
    'IMMEDIATE': 85,    # Fast-track to Phase 1
    'HIGH': 70,        # Include in Phase 2
    'MODERATE': 50,    # Conditional targets
    'LOW': 20         # Low priority
}

# Production Data Fields
PRODUCTION_FIELDS = {
    'gas_primary': 'wellGas',
    'gas_fallback': 'totalGas',
    'oil_primary': 'wellOil',
    'oil_fallback': 'totalOil',
    'water': 'wellWater',
    'date': 'reportDate',
    'month': 'reportMonth',
    'year': 'reportYear',
    'operator': 'operator',
    'days': 'days'
}

# Export Formats
EXPORT_FORMATS = ['csv', 'json', 'xlsx']

# Date Ranges for Analysis
DATE_RANGES = {
    'RECENT': ('2020-01-01', '2024-12-31'),
    'HISTORICAL': ('2010-01-01', '2019-12-31'),  
    'LEGACY': ('2000-01-01', '2009-12-31'),
    'ALL_TIME': ('1990-01-01', '2024-12-31')
}