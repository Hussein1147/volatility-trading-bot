#!/usr/bin/env python3
"""Quick dashboard verification script"""

import requests
import webbrowser

print("🔍 Verifying dashboard status...")
print("-" * 40)

try:
    # Test connection
    response = requests.get("http://localhost:8501", timeout=5)
    print(f"✅ Dashboard is running on port 8501")
    print(f"✅ HTTP Status: {response.status_code}")
    print(f"✅ Server: {response.headers.get('Server', 'Unknown')}")
    print(f"✅ Content-Type: {response.headers.get('Content-Type', 'Unknown')}")
    
    # Check if it's actually Streamlit
    if "streamlit" in response.text.lower():
        print("✅ Streamlit app detected")
    
    print("\n🌐 Opening dashboard in your default browser...")
    webbrowser.open("http://localhost:8501")
    
    print("\n📝 If browser doesn't open, manually visit:")
    print("   http://localhost:8501")
    print("   http://127.0.0.1:8501")
    
except requests.exceptions.ConnectionError:
    print("❌ Cannot connect to dashboard on port 8501")
    print("   The dashboard may not be running.")
except Exception as e:
    print(f"❌ Error: {e}")