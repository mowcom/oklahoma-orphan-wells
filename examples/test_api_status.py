#!/usr/bin/env python3
"""Test API endpoints to confirm what's working"""

import httpx
import json
from datetime import datetime

# API Configuration
API_KEY = "6ipnW2sRTSqVPmsUnUDjDKrlMjVtk7iiyccMcQGztMdeHn7D2RSsQIiS6z6sGTPO"
BASE_URL = "https://app.welldatabase.com/api/v2"

headers = {
    'Content-Type': 'application/json',
    'User-Agent': 'API Status Test',
    'Api-Key': API_KEY
}

def test_basic_endpoints():
    """Test basic API endpoints to see what's working"""
    
    print(f"🔍 API STATUS CHECK - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    tests = [
        {
            'name': 'Well Search',
            'method': 'POST',
            'endpoint': '/wells/search',
            'data': {
                'Filters': {'Api10': ['3500921739']},
                'PageSize': 1,
                'PageOffset': 0
            }
        },
        {
            'name': 'Status List',
            'method': 'GET', 
            'endpoint': '/status',
            'data': None
        },
        {
            'name': 'Counties List',
            'method': 'GET',
            'endpoint': '/counties', 
            'data': None
        },
        {
            'name': 'Operators List',
            'method': 'GET',
            'endpoint': '/operators',
            'data': None
        },
        {
            'name': 'Well Summary Export',
            'method': 'POST',
            'endpoint': '/wellSummary/search',
            'data': {
                'Filters': {'StateIds': {'Included': [35]}},
                'PageSize': 1,
                'PageOffset': 0
            }
        }
    ]
    
    results = []
    
    for test in tests:
        print(f"\n🔄 Testing: {test['name']}")
        print(f"   {test['method']} {BASE_URL}{test['endpoint']}")
        
        try:
            if test['method'] == 'POST':
                response = httpx.post(
                    f"{BASE_URL}{test['endpoint']}", 
                    headers=headers, 
                    json=test['data'],
                    timeout=30
                )
            else:
                response = httpx.get(
                    f"{BASE_URL}{test['endpoint']}", 
                    headers=headers,
                    timeout=30
                )
            
            status = response.status_code
            print(f"   Status: {status}")
            
            if status == 200:
                try:
                    data = response.json()
                    if isinstance(data, dict):
                        keys = list(data.keys())
                        total = data.get('total', len(data.get('data', [])))
                        print(f"   ✅ SUCCESS - Keys: {keys[:3]}... Total: {total}")
                    elif isinstance(data, list):
                        print(f"   ✅ SUCCESS - Array with {len(data)} items")
                    else:
                        print(f"   ✅ SUCCESS - Response type: {type(data)}")
                        
                    results.append({'test': test['name'], 'status': 'SUCCESS', 'code': status})
                    
                except Exception as e:
                    print(f"   ✅ SUCCESS - But JSON parse error: {e}")
                    results.append({'test': test['name'], 'status': 'SUCCESS*', 'code': status})
                    
            elif status == 401:
                print(f"   🔐 UNAUTHORIZED - API key issue")
                results.append({'test': test['name'], 'status': 'UNAUTHORIZED', 'code': status})
                
            elif status == 403:
                print(f"   ⛔ FORBIDDEN - Permission denied")
                results.append({'test': test['name'], 'status': 'FORBIDDEN', 'code': status})
                
            elif status == 404:
                print(f"   🔍 NOT FOUND - Endpoint doesn't exist")
                results.append({'test': test['name'], 'status': 'NOT_FOUND', 'code': status})
                
            elif status == 429:
                print(f"   ⏱️  RATE LIMITED - Too many requests")
                results.append({'test': test['name'], 'status': 'RATE_LIMITED', 'code': status})
                
            else:
                print(f"   ❌ ERROR - HTTP {status}")
                results.append({'test': test['name'], 'status': 'ERROR', 'code': status})
                
        except httpx.TimeoutException:
            print(f"   ⏱️  TIMEOUT - Request took too long")
            results.append({'test': test['name'], 'status': 'TIMEOUT', 'code': 'TIMEOUT'})
            
        except httpx.ConnectError:
            print(f"   🌐 CONNECTION ERROR - Cannot reach server")
            results.append({'test': test['name'], 'status': 'CONNECTION_ERROR', 'code': 'CONN_ERR'})
            
        except Exception as e:
            print(f"   ❌ EXCEPTION - {e}")
            results.append({'test': test['name'], 'status': 'EXCEPTION', 'code': str(e)[:20]})
    
    print(f"\n📊 SUMMARY:")
    print("=" * 30)
    success_count = len([r for r in results if 'SUCCESS' in r['status']])
    print(f"   Working endpoints: {success_count}/{len(results)}")
    
    for result in results:
        status_emoji = {
            'SUCCESS': '✅',
            'SUCCESS*': '✅', 
            'UNAUTHORIZED': '🔐',
            'FORBIDDEN': '⛔',
            'NOT_FOUND': '🔍',
            'RATE_LIMITED': '⏱️',
            'ERROR': '❌',
            'TIMEOUT': '⏱️',
            'CONNECTION_ERROR': '🌐',
            'EXCEPTION': '❌'
        }
        
        emoji = status_emoji.get(result['status'], '❓')
        print(f"   {emoji} {result['test']}: {result['status']}")
    
    return results

def test_our_specific_well():
    """Test access to our specific well data"""
    print(f"\n🎯 TESTING ACCESS TO DELHI 1-18 WELL")
    print("=" * 40)
    
    try:
        data = {
            'Filters': {'Api10': ['3500921739']},
            'PageSize': 1,
            'PageOffset': 0
        }
        
        response = httpx.post(f"{BASE_URL}/wells/search", headers=headers, json=data, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            if result.get('data') and len(result['data']) > 0:
                well = result['data'][0]
                print(f"✅ Well found: {well.get('wellName')}")
                print(f"   API: {well.get('apI10')}")
                print(f"   Status: {well.get('wellStatus')}")
                print(f"   Operator: {well.get('currentOperator')}")
                print(f"   Well ID: {well.get('wellId')}")
                return True
            else:
                print("❌ Well not found in results")
                return False
        else:
            print(f"❌ HTTP {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    # Test basic endpoints
    results = test_basic_endpoints()
    
    # Test our specific well
    well_access = test_our_specific_well()
    
    # Overall status
    print(f"\n🎯 OVERALL API STATUS:")
    success_rate = len([r for r in results if 'SUCCESS' in r['status']]) / len(results) * 100
    
    if success_rate >= 80:
        print(f"   ✅ API is working well ({success_rate:.0f}% success rate)")
    elif success_rate >= 50:
        print(f"   ⚠️  API has some issues ({success_rate:.0f}% success rate)")
    else:
        print(f"   ❌ API has major problems ({success_rate:.0f}% success rate)")
    
    if well_access:
        print(f"   ✅ Your test well is accessible")
    else:
        print(f"   ❌ Your test well is not accessible")
        
    print(f"\n💡 File downloads likely require different authentication or endpoint")