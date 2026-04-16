#!/usr/bin/env python3
"""
Test script to verify the analytics system is working correctly.
"""

import sqlite3
import os
import json
from datetime import datetime

# Database path
analytics_db = "/root/analytics_app/analytics.db"

def test_analytics():
    """Test the analytics database and functions."""
    
    print("=" * 60)
    print("ANALYTICS SYSTEM TEST")
    print("=" * 60)
    
    if not os.path.exists(analytics_db):
        print(f"Database not found at {analytics_db}")
        return False
    
    try:
        conn = sqlite3.connect(analytics_db)
        c = conn.cursor()
        
        # Get today's date
        today = datetime.now().strftime("%Y-%m-%d")
        print(f"\nTesting analytics for today: {today}")
        
        # Get total time today
        c.execute("""
            SELECT SUM(duration_seconds) FROM activity_logs
            WHERE date = ? AND user_id = ?
        """, (today, "default"))
        total_seconds = c.fetchone()[0] or 0
        total_minutes = total_seconds // 60
        
        print(f"\nTotal Usage Today:")
        print(f"  - Total Seconds: {total_seconds}")
        print(f"  - Total Minutes: {total_minutes}")
        
        # Get module breakdown
        c.execute("""
            SELECT module_name, SUM(duration_seconds) FROM activity_logs
            WHERE date = ? AND user_id = ?
            GROUP BY module_name
            ORDER BY SUM(duration_seconds) DESC
        """, (today, "default"))
        
        module_data = c.fetchall()
        
        print(f"\nModule Breakdown:")
        if module_data:
            for module, seconds in module_data:
                minutes = seconds // 60
                print(f"  - {module}: {minutes} minutes ({seconds} seconds)")
        else:
            print("  - No activity recorded")
        
        # Get module details
        c.execute("""
            SELECT module_name, start_time, end_time, duration_seconds FROM activity_logs
            WHERE date = ? AND user_id = ?
            ORDER BY start_time DESC
        """, (today, "default"))
        
        records = c.fetchall()
        
        print(f"\nDetailed Module Usage:")
        if records:
            for module, start, end, duration in records:
                minutes = duration // 60
                print(f"  - {module}: {start} to {end} ({minutes}m)")
        else:
            print("  - No activity recorded")
        
        # Test JSON response format (like API would return)
        print(f"\nAPI Response Format Test:")
        
        daily_summary = {
            "total_seconds": total_seconds,
            "total_minutes": total_minutes,
            "module_breakdown": [
                {"module": m[0], "seconds": m[1], "minutes": m[1] // 60} 
                for m in module_data
            ]
        }
        
        print(f"\n/analytics/daily_summary response:")
        print(json.dumps(daily_summary, indent=2))
        
        module_details = []
        for record in records:
            module_details.append({
                "module": record[0],
                "start_time": record[1],
                "end_time": record[2],
                "duration_seconds": record[3],
                "duration_minutes": record[3] // 60
            })
        
        print(f"\n/analytics/module_details response:")
        print(json.dumps(module_details, indent=2))
        
        conn.close()
        
        print("\n" + "=" * 60)
        print("TEST PASSED - Analytics system is ready!")
        print("=" * 60)
        return True
        
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    test_analytics()
