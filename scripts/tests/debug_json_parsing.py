#!/usr/bin/env python3
"""
Debug JSON parsing issue
"""

import re
import json

# Sample Claude response
content = '''```json
{
  "should_trade": true,
  "symbol": "SPY",
  "strategy": "iron_condor",
  "book_type": "PRIMARY",
  "entry": {
    "put_short_strike": 405,
    "put_long_strike": 400,
    "call_short_strike": 495,
    "call_long_strike": 500,
    "target_delta": 0.15,
    "expiration_date": "2024-02-16",
    "dte": 45
  },
  "sizing": {
    "confidence_score": 85
  },
  "reasoning": "Test"
}
```'''

print("Original content:")
print(content[:100] + "...")
print()

# Try the regex
json_match = re.search(r'```json\s*(.*?)\s*```', content, re.DOTALL)
if json_match:
    json_str = json_match.group(1).strip()
    print(f"Extracted JSON string length: {len(json_str)}")
    print(f"First 50 chars: {json_str[:50]}...")
    print()
    
    try:
        data = json.loads(json_str)
        print("✅ JSON parsed successfully!")
        print(f"should_trade: {data.get('should_trade')}")
    except Exception as e:
        print(f"❌ JSON parse error: {e}")
else:
    print("❌ No JSON match found")