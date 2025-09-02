# 🛢️ WellDatabase API - Oklahoma Orphaned Well Analysis

**Comprehensive system for identifying, analyzing, and prioritizing orphaned wells for reactivation in Oklahoma**

[![Python](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

---

## 🎯 Overview

This repository contains a complete framework for analyzing Oklahoma orphaned wells using the WellDatabase API v2. The system is designed to support **Phase 0 - Remote Pre-Screen** activities for well reactivation business models, providing:

- **🔍 Orphan Well Identification**: Find and filter true orphaned wells in Oklahoma
- **📊 Production Analysis**: Analyze historical production patterns for reactivation potential  
- **🏆 Reactivation Scoring**: 95-point scoring system with business recommendations
- **📈 Business Intelligence**: ROI analysis, operator tracking, geographic clustering
- **📋 Comprehensive Reporting**: Detailed analysis reports ready for Phase 1 field surveys

### **Key Results**
- **Identified**: Real orphaned well status codes (not the 554k "Unknown" wells)
- **Analyzed**: Complete production categorization framework  
- **Validated**: Sample well (API 35-039-21577-0000) scored **95/100 - HIGH POTENTIAL**
- **Business Model**: Supports $80k Phase 0 → $300 MCF/day target reactivation workflow

---

## 🚀 Quick Start

### **1. Installation (conda)**
```bash
git clone <repository-url>
cd wellDatabaseAPI

# Create and activate the environment
conda env create -f environment.yml
conda activate chamber-wda
```

### **2. Configuration**
```bash
# Set your API key for this shell
export WBD_API_KEY=YOUR_API_KEY

# Or add to your shell profile (~/.zshrc or ~/.bashrc)
echo 'export WBD_API_KEY=YOUR_API_KEY' >> ~/.zshrc && source ~/.zshrc
```

### **3. Run Sample Analysis**
```bash
# Generate sample reactivation report
python reactivation/sample_well_report_35039215770000.py

# Test API connectivity (uses conda env)
python examples/test_api_status.py

# Run Phase 0 (loads .env automatically via Makefile)
make run-phase0-50 | cat
```

### **4. Fetch Production by API Number (Search-only method)**
```bash
python - <<'PY'
from src.api.client import WellDatabaseClient

client = WellDatabaseClient()
well = client.get_well_by_api('35-039-21577-0000')  # dashes OK
assert well, 'Well not found'

resp = client.get_production_data([well['WellId' if 'WellId' in well else 'wellId']], '1990-01-01', '2024-12-31', page_size=1000)
rows = resp.get('data', [])
print('rows:', len(rows), 'nonzero:', sum(1 for r in rows if (r.get('wellGas') or r.get('totalGas') or 0) > 0))
PY
```

---

## 📁 Repository Structure

```
wellDatabaseAPI/
├── 📚 docs/                          # Documentation
│   └── WELLDATABASE_API_GUIDE.md     # Complete API developer guide
├── 🔧 src/                           # Core modules
│   ├── api/                          # API client and endpoints
│   │   └── client.py                 # WellDatabase API wrapper
│   ├── analysis/                     # Analysis engines
│   │   └── reactivation.py           # Reactivation scoring system
│   └── config/                       # Configuration
│       ├── settings.py               # API keys, timeouts
│       └── constants.py              # Orphan statuses, thresholds
├── 🎯 reactivation/                  # Reactivation analysis tools
│   ├── sample_well_report_*.py       # Sample analysis reports
│   └── reports/                      # Generated analysis outputs
├── 💡 examples/                      # Example scripts
├── 🛠️ tools/                         # Utility scripts
├── 📊 output/                        # Analysis outputs
└── 📋 reports/                       # Business reports
```

---

## 🔑 Key Features

### **🎯 Orphaned Well Identification**
- **Correct Status Filtering**: Uses validated orphan statuses vs 554k "Unknown" wells
- **Oklahoma Focus**: State ID 35 with proper geographic filtering
- **Status Codes**: `"Orphaned - Completed - Not Active"`, `"Orphaned - Shut In"`

### **📊 Production Analysis Engine**
- **Historical Pattern Recognition**: 24-month analysis window
- **Multi-threshold Analysis**: 1k, 4k, 20k MCF/month categorization
- **Trend Analysis**: Declining, stable, increasing production patterns
- **Data Quality Handling**: Robust handling of missing/zero production data

### **🏆 Reactivation Scoring System**
```python
Categories:
├── HIGH POTENTIAL (95 pts)     - Consistent 4k+ MCF until orphaning
├── SURGE POTENTIAL (85 pts)    - Recent 20k+ MCF peaks before shutoff  
├── DECLINING VIABLE (70 pts)   - 1k-4k MCF range before orphaning
├── SPORADIC STRONG (60 pts)    - Historical strong months, variable recent
├── SPORADIC MODERATE (40 pts)  - Moderate history, limited recent activity
└── LOW POTENTIAL (20 pts)      - Minimal production history
```

---

## 📊 Sample Analysis Results

### **API 35-039-21577-0000 (NEWCOMB 18-3)**
```
🎯 REACTIVATION ASSESSMENT
Category: 🏆 HIGH POTENTIAL - Consistent 4k+ MCF  
Score: 95/100
Timeline: 43 producing months (2008-2011)
Peak Production: 41,000 MCF/month
Cumulative Production: 591,600 MCF
Est. Annual Revenue Potential: $577,842

💼 BUSINESS RECOMMENDATION
Priority: IMMEDIATE - Fast-track to Phase 1 field survey
Risk Level: Low
Action: Schedule immediate site visit and acquisition pursuit
```

---

## 🔧 Usage Examples

### **Basic Well Analysis**
```python
from src.api.client import WellDatabaseClient
from src.analysis.reactivation import ReactivationAnalyzer

# Initialize client
client = WellDatabaseClient()

# Find orphaned wells in Oklahoma  
orphan_wells = client.get_orphaned_wells(
    state_id=35, 
    orphan_statuses=["Orphaned - Shut In", "Orphaned - Completed - Not Active"]
)

# Analyze production for reactivation potential
analyzer = ReactivationAnalyzer()
for well in orphan_wells['data'][:5]:
    production_data = client.get_production_data([well['wellId']], '2000-01-01', '2024-12-31')
    analysis = analyzer.analyze_well(production_data['data'], well)
    
    print(f"{well['wellName']}: {analysis['reactivation_score']}/100")
```

---

## 📚 Documentation

### **📖 Core Documentation**
- **[WellDatabase API Guide](docs/WELLDATABASE_API_GUIDE.md)**: Complete developer guide
- **[Data Sources](docs/data-sources.md)**: OCC/WB/GIS inputs and contracts
- **[Business Logic](docs/business-logic.md)**: Phases 0–2 rules and scoring
- **[Cursor Agent](cursor-agent.md)**: Agent mission and pipeline commands
- **Run Phase 0 Pipeline**: `make run-phase0` or `python -m src.pipelines.phase0_desktop`
- **[Sample Report](reactivation/sample_well_report_35039215770000.py)**: Full analysis example
- **[Phase 0 Workflow](PHASE_0_ORPHAN_REACTIVATION_WORKFLOW.md)**: Business methodology

### **🔍 Key Discoveries**
1. **Real Orphan Count**: Uses proper status filtering (not 554k "Unknown" wells)
2. **Production Data Access**: /production/search works, /export times out for large datasets
3. **Status Filtering**: Use string names, not numeric IDs for reliable filtering
4. **Data Quality**: Cross-reference with OCC records for production validation

### **⚠️ Known Issues & Workarounds**
- **Production Export Timeouts**: Use smaller date ranges or manual data input
- **Zero Production Values**: May indicate data sync issues vs actual dry holes
- **Status Code Reliability**: String-based filtering more reliable than numeric IDs

---

## 🛠️ Advanced Features

### **API Client Features**
- **Automatic Retry Logic**: Handles rate limiting and timeouts
- **Pagination Support**: Processes large datasets automatically  
- **Error Handling**: Comprehensive exception handling with business context
- **Health Checks**: API connectivity validation

### **Analysis Engine Features**
- **Multi-Threshold Scoring**: Configurable production thresholds
- **Trend Analysis**: Decline curve analysis and forecasting
- **Economic Modeling**: Revenue potential calculations
- **Risk Assessment**: Technical and business risk evaluation

---

## 🎯 Success Metrics

**✅ What This System Delivers:**
- **Complete orphan well identification** system for Oklahoma
- **95-point scoring system** for reactivation potential
- **Complete business workflow** from targeting to acquisition
- **Validated methodology** with sample 95/100 high-potential well
- **Ready-to-use Phase 0 framework** for reactivation business model

**The tools are built. The opportunity is massive. Let's reactivate Oklahoma's orphaned energy assets.** 🚀

---

*Built for Chamber's Oklahoma orphaned well reactivation initiative*