import duckdb
import json
import re
from datetime import datetime, timezone
from fastapi import FastAPI, Query
from huggingface_hub import hf_hub_url
from typing import Optional
import threading
import gc

app = FastAPI()

# ===== RESULT CACHE =====
result_cache = {}
cache_timestamps = {}
CACHE_TTL = 300  # 5 minutes

def get_cached(key):
    if key in result_cache:
        if (datetime.now().timestamp() - cache_timestamps.get(key, 0)) < CACHE_TTL:
            return result_cache[key]
    return None

def set_cache(key, value):
    if len(result_cache) >= 500:
        oldest = min(cache_timestamps, key=cache_timestamps.get)
        del result_cache[oldest]
        del cache_timestamps[oldest]
    result_cache[key] = value
    cache_timestamps[key] = datetime.now().timestamp()

# ===== Thread-local connection =====
thread_local = threading.local()

def get_db_connection():
    """Get thread-local DuckDB connection"""
    if not hasattr(thread_local, "connection") or thread_local.connection is None:
        try:
            thread_local.connection = duckdb.connect()
            thread_local.connection.execute("PRAGMA memory_limit='4GB'")  # CHANGE 1
            thread_local.connection.execute("PRAGMA temp_directory='/tmp'")
            thread_local.connection.execute("PRAGMA read_only=true")  # CHANGE 2
            thread_local.connection.execute("PRAGMA threads=4")  # CHANGE 2
        except Exception as e:
            print(f"Error creating connection: {e}")
            thread_local.connection = duckdb.connect()
    return thread_local.connection

# index_map.json load karein
try:
    with open("index_map.json", "r") as f:
        index_map = json.load(f)
except:
    index_map = []

REPO_ID = "tfqdeadlo/850MindData"

# ===== HELPER FUNCTIONS ===== (SAME - NO CHANGE)
def format_address(address):
    """Format address from string to structured object"""
    if not address:
        return {"full_address": "N/A", "landmark": "", "village_city": "", "district": "", "state": "", "pincode": ""}
    
    address = str(address).strip()
    
    # Clean the address
    clean_address = address.replace('!-!-', ', ').replace('!!', ', ').replace('!', ', ')
    clean_address = re.sub(r'\s+', ' ', clean_address).strip()
    
    # Split by comma
    parts = [p.strip() for p in clean_address.split(',') if p.strip()]
    
    if not parts:
        return {
            "full_address": address,
            "landmark": address,
            "village_city": "",
            "district": "",
            "state": "",
            "pincode": ""
        }
    
    # If only one part, try to extract pincode and state
    if len(parts) == 1:
        pincode = ''
        state = ''
        single_part = parts[0]
        
        # Extract pincode (6 digits)
        pincode_match = re.search(r'\b(\d{6})\b', single_part)
        if pincode_match:
            pincode = pincode_match.group(1)
            single_part = single_part.replace(pincode, '').strip()
        
        # Extract state
        states = ['BIHAR', 'UTTAR PRADESH', 'DELHI', 'MAHARASHTRA', 'WEST BENGAL', 
                  'TAMIL NADU', 'KARNATAKA', 'GUJARAT', 'RAJASTHAN', 'PUNJAB', 'HARYANA',
                  'KERALA', 'ANDHRA PRADESH', 'TELANGANA', 'ODISHA', 'MADHYA PRADESH',
                  'UTTARAKHAND', 'CHHATTISGARH', 'JHARKHAND', 'ASSAM']
        
        for st in states:
            if st in single_part.upper():
                state = st.title()
                single_part = single_part.replace(st, '').strip()
                break
        
        single_part = re.sub(r'^[\s\-]+|[\s\-]+$', '', single_part)
        
        return {
            "full_address": address,
            "landmark": single_part if single_part else address,
            "village_city": "",
            "district": "",
            "state": state,
            "pincode": pincode
        }
    
    # Multiple parts
    result = {
        "full_address": clean_address,
        "landmark": parts[0] if len(parts) > 0 else '',
        "village_city": parts[1] if len(parts) > 1 else '',
        "district": parts[2] if len(parts) > 2 else '',
        "state": parts[3] if len(parts) > 3 else '',
        "pincode": parts[4] if len(parts) > 4 else ''
    }
    
    # Try to extract pincode and state if not found
    if not result['state'] or not result['pincode']:
        full_text = ' '.join(parts)
        
        if not result['pincode']:
            pincode_match = re.search(r'\b(\d{6})\b', full_text)
            if pincode_match:
                result['pincode'] = pincode_match.group(1)
        
        if not result['state']:
            states = ['BIHAR', 'UTTAR PRADESH', 'DELHI', 'MAHARASHTRA', 'WEST BENGAL', 
                      'TAMIL NADU', 'KARNATAKA', 'GUJARAT', 'RAJASTHAN', 'PUNJAB', 'HARYANA',
                      'KERALA', 'ANDHRA PRADESH', 'TELANGANA', 'ODISHA', 'MADHYA PRADESH',
                      'UTTARAKHAND', 'CHHATTISGARH', 'JHARKHAND', 'ASSAM']
            
            for st in states:
                if st in full_text.upper():
                    result['state'] = st.title()
                    break
    
    return result

def extract_operator(circle):
    """Extract operator from circle"""
    if not circle:
        return 'Unknown'
    
    circle_upper = str(circle).upper()
    if 'JIO' in circle_upper:
        return 'Jio'
    elif 'AIRTEL' in circle_upper:
        return 'Airtel'
    elif 'VODAFONE' in circle_upper or 'VI' in circle_upper:
        return 'Vodafone Idea (Vi)'
    elif 'BSNL' in circle_upper:
        return 'BSNL'
    
    return circle.split()[0] if circle else 'Unknown'

def extract_state(address):
    """Extract state from address"""
    if not address:
        return 'Unknown'
    
    address = str(address)
    
    states = ['BIHAR', 'UTTAR PRADESH', 'DELHI', 'MAHARASHTRA', 'WEST BENGAL', 
              'TAMIL NADU', 'KARNATAKA', 'GUJARAT', 'RAJASTHAN', 'PUNJAB', 'HARYANA',
              'KERALA', 'ANDHRA PRADESH', 'TELANGANA', 'ODISHA', 'MADHYA PRADESH',
              'UTTARAKHAND', 'CHHATTISGARH', 'JHARKHAND', 'ASSAM']
    
    address_upper = address.upper()
    for state in states:
        if state in address_upper:
            return state.title()
    
    return 'Unknown'

# ===== SEARCH FUNCTION ===== (WITH CACHE)
def search_mobile_number(m, con):
    """Search a mobile number and return results"""
    m_str = str(m)
    
    # ===== CACHE CHECK ===== (CHANGE 4)
    cache_key = f"mobile:{m_str}"
    cached = get_cached(cache_key)
    if cached is not None:
        return cached
    
    # Find files to scan
    files_to_scan = []
    for i in range(len(index_map)):
        curr_start = index_map[i]["start_mobile"]
        next_start = index_map[i+1]["start_mobile"] if i+1 < len(index_map) else "0"
        
        low = min(curr_start, next_start)
        high = max(curr_start, next_start)
        
        if low <= m <= high or m.startswith(curr_start[:4]): 
            files_to_scan.append(index_map[i]["file"])

    safety_parts = [
        "data/Hi-Tek_Part_851.parquet", 
        "data/Hi-Tek_Part_850.parquet"
    ]
    files_to_scan = list(dict.fromkeys(files_to_scan + safety_parts))[:10]
    
    all_results = []
    columns = ['mobile', 'name', 'fname', 'address', 'alt', 'circle', 'id', 'email']
    
    for f_name in files_to_scan:
        try:
            file_url = hf_hub_url(repo_id=REPO_ID, filename=f_name, repo_type="dataset")
            query = f"SELECT * FROM read_parquet('{file_url}') WHERE CAST(mobile AS VARCHAR) = '{m}'"
            result = con.execute(query).fetchall()
            
            if result:
                for row in result:
                    row_dict = dict(zip(columns, row))
                    all_results.append({
                        "name": row_dict.get('name', 'N/A'),
                        "father_name": row_dict.get('fname', 'N/A'),
                        "address": format_address(row_dict.get('address', '')),
                        "alternate_number": row_dict.get('alt', 'N/A'),
                        "circle": row_dict.get('circle', 'N/A'),
                        "operator": extract_operator(row_dict.get('circle', '')),
                        "state": extract_state(row_dict.get('address', '')),
                        "email": row_dict.get('email', None),
                        "id": row_dict.get('id', 'N/A')
                    })
            del result
        except Exception as e:
            print(f"Error in {f_name}: {e}")
            continue
    
    gc.collect()
    
    # ===== CACHE SAVE ===== (CHANGE 4)
    set_cache(cache_key, all_results)
    return all_results

# ===== SEARCH WITH ALTERNATE NUMBERS =====
def search_with_alternates(m, con):
    """Search main number + all alternate numbers and combine results"""
    all_final_results = []
    processed_numbers = set()
    numbers_to_search = [m]
    
    # 3 levels deep
    for level in range(3):
        current_numbers = numbers_to_search.copy()
        numbers_to_search = []
        
        for num in current_numbers:
            if num in processed_numbers:
                continue
            processed_numbers.add(num)
            
            # Search this number
            results = search_mobile_number(num, con)
            if results:
                all_final_results.extend(results)
                
                # Collect alternate numbers
                for result in results:
                    alt = result.get('alternate_number')
                    if alt and alt != 'N/A' and len(str(alt)) == 10:
                        alt_str = str(alt)
                        if alt_str not in processed_numbers and alt_str not in numbers_to_search:
                            numbers_to_search.append(alt_str)
    
    return all_final_results

# ===== SEARCH FUNCTIONS =====

@app.get("/search/{mobile}")
def search_by_mobile(mobile: str):
    m = str(mobile).strip()
    con = get_db_connection()
    
    try:
        # Search main + all alternate numbers
        results = search_with_alternates(m, con)
        
        if results:
            return {
                "success": True,
                "api_by": "@sauravsingh2111",
                "timestamp": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
                "mobile": m,
                "total_results": len(results),
                "results": results,
                "message": f"Found {len(results)} records for {m} (including alternate numbers)"
            }
        
        return {
            "success": False,
            "api_by": "@sauravsingh2111",
            "mobile": m,
            "message": f"No details found for {m}",
            "contact": "Please contact @sauravsingh2111 for support"
        }
    except Exception as e:
        print(f"Search error: {e}")
        return {
            "success": False,
            "api_by": "@sauravsingh2111",
            "mobile": m,
            "error": str(e),
            "message": "Error occurred during search"
        }

# ===== ID SEARCH ===== (WITH CACHE)
@app.get("/search/id/{id_value}")
def search_by_id(id_value: str):
    """Search ID and return ALL results"""
    search_id = str(id_value).strip()
    
    # ===== CACHE CHECK ===== (CHANGE 5)
    cache_key = f"id:{search_id}"
    cached = get_cached(cache_key)
    if cached is not None:
        return cached
    
    con = get_db_connection()
    
    all_results = []
    all_files = [item["file"] for item in index_map][:20]
    columns = ['mobile', 'name', 'fname', 'address', 'alt', 'circle', 'id', 'email']
    
    for f_name in all_files:
        try:
            file_url = hf_hub_url(repo_id=REPO_ID, filename=f_name, repo_type="dataset")
            query = f"SELECT * FROM read_parquet('{file_url}') WHERE CAST(id AS VARCHAR) = '{search_id}'"
            result = con.execute(query).fetchall()
            
            if result:
                for row in result:
                    row_dict = dict(zip(columns, row))
                    all_results.append({
                        "name": row_dict.get('name', 'N/A'),
                        "father_name": row_dict.get('fname', 'N/A'),
                        "address": format_address(row_dict.get('address', '')),
                        "alternate_number": row_dict.get('alt', 'N/A'),
                        "circle": row_dict.get('circle', 'N/A'),
                        "operator": extract_operator(row_dict.get('circle', '')),
                        "state": extract_state(row_dict.get('address', '')),
                        "email": row_dict.get('email', None),
                        "id": row_dict.get('id', 'N/A')
                    })
            del result
        except Exception as e:
            print(f"Error in {f_name}: {e}")
            continue
    
    if all_results:
        # Search alternate numbers
        alt_numbers = set()
        for result in all_results:
            alt = result.get('alternate_number')
            if alt and alt != 'N/A' and len(str(alt)) == 10:
                alt_numbers.add(str(alt))
        
        for alt_num in list(alt_numbers)[:3]:
            alt_results = search_mobile_number(alt_num, con)
            if alt_results:
                all_results.extend(alt_results)
        
        response = {
            "success": True,
            "api_by": "@sauravsingh2111",
            "timestamp": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
            "id": search_id,
            "total_results": len(all_results),
            "results": all_results,
            "message": f"Found {len(all_results)} records for ID {search_id}"
        }
    else:
        response = {
            "success": False,
            "api_by": "@sauravsingh2111",
            "id": search_id,
            "message": f"No details found for ID {search_id}",
            "contact": "Please contact @sauravsingh2111 for support"
        }
    
    # ===== CACHE SAVE ===== (CHANGE 5)
    set_cache(cache_key, response)
    return response

# ===== HEALTH AND STATUS ENDPOINTS =====
@app.get("/search/advanced")
def advanced_search(
    mobile: Optional[str] = Query(None),
    id: Optional[str] = Query(None),
    name: Optional[str] = Query(None),
    fname: Optional[str] = Query(None),
    circle: Optional[str] = Query(None),
    alt: Optional[str] = Query(None)
):
    if id:
        return search_by_id(id)
    if mobile:
        return search_by_mobile(mobile)
    
    return {
        "status": "error",
        "message": "Please use /search/{mobile} or /search/id/{id} for faster results."
    }

@app.get("/stats")
def get_stats():
    return {
        "status": "success",
        "total_files": len(index_map),
        "total_records": "~85 Crore",
        "cache_size": len(result_cache),
        "search_methods": ["mobile", "id"]
    }

@app.get("/health")
def health():
    return {"status": "healthy", "database": "connected", "cache_size": len(result_cache)}

@app.get("/clear-cache")
def clear_cache():
    """Clear the result cache"""
    global result_cache, cache_timestamps
    result_cache = {}
    cache_timestamps = {}
    return {
        "status": "success",
        "message": "Cache cleared",
        "api_by": "@sauravsingh2111"
    }

@app.get("/")
def home():
    return {
        "status": "online",
        "total_indexed": len(index_map),
        "cache_size": len(result_cache),
        "endpoints": {
            "search_by_mobile": "/search/{mobile}",
            "search_by_id": "/search/id/{id}",
            "stats": "/stats",
            "health": "/health",
            "clear_cache": "/clear-cache"
        }
    }

@app.on_event("shutdown")
def shutdown_event():
    if hasattr(thread_local, "connection"):
        try:
            thread_local.connection.close()
        except:
            pass