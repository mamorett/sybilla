#!/usr/bin/env python3
"""
Oracle Log Structure Tester
This will show you exactly what your Oracle logs look like
"""

import asyncio
import os
import sys
from datetime import datetime, timedelta

# Add your project path so we can import oracle_client
sys.path.append('.')

async def test_oracle_direct():
    """Test Oracle client directly to see log structure"""
    try:
        # Import your oracle client
        from oracle_client import OracleLogsClient
        
        print("🔍 Testing Oracle client directly...")
        
        client = OracleLogsClient()
        
        # Test basic query
        start_time = datetime.utcnow() - timedelta(hours=1)
        end_time = datetime.utcnow()
        
        base_query = client._build_base_query()
        base_query += " | limit 5"  # Just get 5 logs to see structure
        
        print(f"🔍 Query: {base_query}")
        print(f"🔍 Time range: {start_time} to {end_time}")
        
        oracle_logs = await client._execute_oracle_query(base_query, start_time, end_time)
        
        print(f"\n📊 Found {len(oracle_logs)} logs")
        
        if oracle_logs:
            print(f"\n🔍 FIRST LOG STRUCTURE:")
            print("="*50)
            first_log = oracle_logs[0]
            print(f"Type: {type(first_log)}")
            print(f"Keys: {list(first_log.keys()) if isinstance(first_log, dict) else 'Not a dict'}")
            print(f"Full structure:")
            import json
            print(json.dumps(first_log, indent=2, default=str))
            
            # Try to parse it
            print(f"\n🔍 PARSING TEST:")
            entry = client._parse_oracle_log_entry(first_log)
            if entry:
                print(f"✅ Parsed successfully:")
                print(f"  IP: {entry.ip}")
                print(f"  Country: {entry.country}")
                print(f"  City: {entry.city}")
                print(f"  Sensor: {entry.sensor}")
                print(f"  ISP: {entry.isp}")
            else:
                print(f"❌ Parsing failed")
        else:
            print("❌ No logs returned - check your Oracle connection and query")
            
    except Exception as e:
        print(f"❌ Oracle test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_oracle_direct())
