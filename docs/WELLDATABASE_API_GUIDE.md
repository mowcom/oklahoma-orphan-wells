# 📚 WellDatabase API Developer Guide

**Complete guide for working with the WellDatabase API v2 for orphaned well analysis and production data extraction**

---

## 🔑 Authentication & Setup

### API Configuration
```python
API_KEY = "your-api-key-here"
BASE_URL = "https://app.welldatabase.com/api/v2"

headers = {
    'Content-Type': 'application/json',
    'Api-Key': API_KEY,
    'User-Agent': 'Your-Application-Name'
}
```

### Rate Limiting
- **Trial Account**: 10,000 requests, 10M data points
- **Timeout Recommendations**: 30s for search, 120s+ for exports
- **Pagination**: Use `PageSize` (max 1000) and `PageOffset`

---

## 🎯 Core Endpoints Overview

### **1. Wells Search (`/wells/search`)**
**Purpose**: Find and filter wells by criteria  
**When to Use**: Initial well discovery, filtering by status/location  
**Response Speed**: Fast (< 5 seconds)  
**Data Volume**: Limited by PageSize  

```python
search_data = {
    'Filters': {
        'StateIds': {'Included': [35]},  # Oklahoma
        'WellStatus': ['Orphaned - Shut In'],
        'Api10': ['3503921577']  # Specific well
    },
    'PageSize': 100,
    'PageOffset': 0
}
```

### **2. Production Search (`/production/search`)**
**Purpose**: Get detailed monthly production records  
**When to Use**: Historical production analysis, time-series data  
**Response Speed**: Moderate (10-30 seconds)  
**Data Volume**: Can be very large (millions of records)  

```python
production_data = {
    'WellIds': ['ce812c6a-915b-4f15-96bd-e65e17b87b66'],
    'StartDate': '2010-01-01',
    'EndDate': '2024-12-31'
}
```

### **3. Production Export (`/production/export`)**
**Purpose**: Bulk export of production data  
**When to Use**: Large datasets, CSV downloads, comprehensive analysis  
**Response Speed**: Slow (60-300 seconds)  
**Data Volume**: Unlimited (returns ZIP file)  

```python
export_data = {
    "ExportFormat": "csv",
    "Filters": {
        "InfinityIds": ["ce812c6a-915b-4f15-96bd-e65e17b87b66"]
    },
    "Fields": ["reportDate", "wellGas", "totalGas", "wellOil"]
}
```

### **4. Production Aggregate (`/production/aggregate`)**
**Purpose**: Summarized/aggregated production metrics  
**When to Use**: Summary statistics, performance overviews  
**Response Speed**: Variable  
**Data Volume**: Condensed summaries  

⚠️ **Currently experiencing 500 errors - needs debugging**

---

## 🔍 Data Access Patterns

### **Pattern 1: Well Discovery → Production Analysis**
```python
# 1. Find wells
wells = search_wells(filters)

# 2. Get production for each
for well in wells:
    production = get_production_data(well['wellId'])
    analysis = analyze_production(production)
```

### **Pattern 2: Bulk Export → CSV Analysis**
```python
# 1. Export large datasets
export_request = create_export_request(well_ids, date_range)
zip_file = download_export(export_request)

# 2. Process CSV files
production_df = pd.read_csv(extracted_csv)
analysis = perform_bulk_analysis(production_df)
```

### **Pattern 3: Targeted Well Analysis**
```python
# 1. Specific well lookup
well = find_well_by_api(api_number)

# 2. Detailed production history
production = get_full_production_history(well['wellId'])
categorization = categorize_reactivation_potential(production)
```

---

## ⚡ Performance Optimization

### **Search Endpoint Optimization**
- **Use specific filters** to reduce result sets
- **Paginate large results** instead of increasing PageSize
- **Cache well lookups** by API number

### **Production Data Optimization**
- **Limit date ranges** for initial testing
- **Use targeted well lists** instead of state-wide searches
- **Implement retry logic** for timeouts

### **Export Optimization**
- **Batch multiple wells** in single export request
- **Use field filtering** to reduce data volume
- **Implement async processing** for large exports

---

## 🎯 Orphaned Well Identification

### **Correct Status Codes**
```python
# ✅ Confirmed orphan statuses
orphan_statuses = [
    "Orphaned - Completed - Not Active",
    "Orphaned - Shut In"
]

# ❌ Avoid these (too broad)
avoid_statuses = [
    "Unknown",  # 554k+ wells, not actually orphaned
    21319, 21333, 21381, 2942, 42  # Status IDs don't work reliably
]
```

### **Oklahoma Orphan Search**
```python
orphan_search = {
    'Filters': {
        'StateIds': {'Included': [35]},  # Oklahoma
        'WellStatus': orphan_statuses
    },
    'PageSize': 100,
    'PageOffset': 0
}
```

---

## 📊 Production Data Structure

### **Key Fields in Production Records**
```python
production_record = {
    'id': 'unique-record-id',
    'wellId': 'well-identifier',
    'reportDate': '2010-03-01T00:00:00',
    'reportMonth': 3,
    'reportYear': 2010,
    
    # Gas Production (MCF)
    'wellGas': 15000,      # ✅ Use this first
    'totalGas': 15000,     # Backup if wellGas is null
    'wellDailyGas': 500,   # Daily rate
    
    # Oil Production (BBL)  
    'wellOil': 250,        # ✅ Use this first
    'totalOil': 250,       # Backup if wellOil is null
    'wellDailyOil': 8,     # Daily rate
    
    # Water & Other
    'wellWater': 100,
    'days': 31,            # Days in reporting period
    'operator': 'COMPANY NAME'
}
```

### **Production Data Quality Issues**
- **Zero values are common** (shut-in periods, data gaps)
- **Multiple records per month** possible (operator changes)
- **Historical data gaps** before 2000
- **Inconsistent reporting** across operators

---

## 🛠️ Common Issues & Solutions

### **Issue 1: All Production Values Are Zero**
**Symptoms**: Production search returns records but all gas/oil = 0  
**Possible Causes**:
- Well was never completed
- Data sync issues between OCC and WellDatabase
- Looking at wrong time period
- Well ID mismatch

**Solutions**:
```python
# Try different date ranges
ranges = [
    ('2020-01-01', '2024-12-31'),  # Recent
    ('2010-01-01', '2019-12-31'),  # Historical
    ('2000-01-01', '2009-12-31')   # Legacy
]

# Check both gas and oil
for record in production_data:
    gas = record.get('wellGas') or record.get('totalGas') or 0
    oil = record.get('wellOil') or record.get('totalOil') or 0
    if gas > 0 or oil > 0:
        print(f"Production found: {record['reportDate']}")
```

### **Issue 2: Export Timeouts**
**Symptoms**: 504 Gateway Timeout on /production/export  
**Solutions**:
- Reduce date range
- Filter by specific wells only
- Use pagination approach
- Implement async processing

### **Issue 3: Status Filtering Not Working**
**Symptoms**: Same well count for different statuses  
**Solutions**:
```python
# Use string names, not numeric IDs
'WellStatus': ['Orphaned - Shut In']  # ✅ Correct

# Not this
'WellStatusIds': {'Included': [21319]}  # ❌ Unreliable
```

### **Issue 4: API Rate Limiting**
**Symptoms**: 429 Too Many Requests  
**Solutions**:
```python
import time

def api_request_with_backoff(url, data, max_retries=3):
    for attempt in range(max_retries):
        response = httpx.post(url, headers=headers, json=data)
        
        if response.status_code == 429:
            wait_time = 2 ** attempt  # Exponential backoff
            time.sleep(wait_time)
            continue
            
        return response
    
    raise Exception("Max retries exceeded")
```

---

## 🔬 Production Analysis Patterns

### **Reactivation Potential Scoring**
```python
def analyze_production_for_reactivation(production_records):
    """
    Score wells for reactivation potential based on historical production
    """
    df = pd.DataFrame(production_records)
    df['gas_mcf'] = pd.to_numeric(df['wellGas'], errors='coerce').fillna(0)
    df['date'] = pd.to_datetime(df['reportDate'])
    
    # Remove zero production months
    producing_months = df[df['gas_mcf'] > 0].sort_values('date')
    
    if producing_months.empty:
        return {'score': 0, 'category': 'NO_PRODUCTION'}
    
    # Calculate key metrics
    max_production = producing_months['gas_mcf'].max()
    recent_avg = producing_months.tail(24)['gas_mcf'].mean()
    consistent_months = len(producing_months[producing_months['gas_mcf'] >= 4000])
    
    # Scoring logic
    if consistent_months >= 6 and recent_avg >= 4000:
        return {'score': 95, 'category': 'HIGH_POTENTIAL'}
    elif max_production >= 20000 and recent_avg >= 1000:
        return {'score': 85, 'category': 'SURGE_POTENTIAL'}
    else:
        return {'score': 40, 'category': 'MODERATE_POTENTIAL'}
```

### **Production Trend Analysis**
```python
def analyze_production_trends(df):
    """
    Identify production trends and decline patterns
    """
    # Monthly aggregation
    monthly = df.groupby(['reportYear', 'reportMonth'])['gas_mcf'].sum()
    
    # Calculate decline rate
    if len(monthly) >= 12:
        first_year = monthly.head(12).mean()
        last_year = monthly.tail(12).mean()
        decline_rate = (first_year - last_year) / first_year * 100
        
        return {
            'decline_rate_percent': decline_rate,
            'trend': 'DECLINING' if decline_rate > 10 else 'STABLE'
        }
    
    return {'trend': 'INSUFFICIENT_DATA'}
```

---

## 📁 Code Organization Best Practices

### **Modular Structure**
```
src/
├── api/
│   ├── client.py          # API client wrapper
│   ├── wells.py           # Wells endpoint functions  
│   ├── production.py      # Production endpoint functions
│   └── exports.py         # Export handling
├── analysis/
│   ├── reactivation.py    # Reactivation scoring
│   ├── production.py      # Production analysis
│   └── trends.py          # Trend analysis
├── utils/
│   ├── data_cleaning.py   # Data preprocessing
│   ├── filters.py         # Filter helpers
│   └── retry.py           # Retry logic
└── config/
    ├── settings.py        # Configuration
    └── constants.py       # Status codes, thresholds
```

### **Error Handling Pattern**
```python
class WellDatabaseError(Exception):
    pass

class ProductionDataError(WellDatabaseError):
    pass

def safe_api_call(func, *args, **kwargs):
    try:
        return func(*args, **kwargs)
    except httpx.TimeoutException:
        raise WellDatabaseError("API timeout - try reducing data range")
    except httpx.ConnectError:  
        raise WellDatabaseError("Connection failed - check API key")
    except Exception as e:
        raise WellDatabaseError(f"Unexpected error: {e}")
```

---

## 🚀 Next Steps for Improvement

### **Immediate Improvements**
1. **Fix production/aggregate endpoint** - Debug 500 errors
2. **Implement proper retry logic** - Handle timeouts gracefully  
3. **Add production data validation** - Verify data quality
4. **Create caching layer** - Reduce redundant API calls

### **Advanced Features**
1. **Async processing** - Handle large datasets efficiently
2. **Data streaming** - Process exports in chunks
3. **Multi-state support** - Extend beyond Oklahoma
4. **Real-time monitoring** - Track API usage and errors

### **Data Quality Enhancements**  
1. **Cross-reference with OCC** - Validate production data
2. **Operator change tracking** - Identify acquisition opportunities
3. **Infrastructure mapping** - Add pipeline proximity data
4. **Economic modeling** - ROI calculations for reactivation

---

## 📞 Support & Resources

- **WellDatabase Support**: [https://support.welldatabase.com](https://support.welldatabase.com)
- **API Documentation**: [WellDatabase API Docs](https://support.welldatabase.com/knowledge/how-do-i-generate-exports-with-the-welldatabase-api)
- **Rate Limit Info**: Check your account dashboard
- **Status Codes**: Use `/status` endpoint for complete list

---

**💡 Remember**: The WellDatabase API is powerful but requires careful handling of timeouts, data volume, and rate limits. Always test with small datasets before scaling up!