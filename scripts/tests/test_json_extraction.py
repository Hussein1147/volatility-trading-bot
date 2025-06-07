#!/usr/bin/env python3
"""
Test JSON extraction from Claude response
"""

import re
import json

# Sample from actual Claude response
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
    "confidence_score": 85,
    "confidence_factors": {
      "iv_rank": 75,
      "technical_alignment": 85,
      "market_structure": 80,
      "event_risk": 90,
      "strike_quality": 85
    },
    "recommended_contracts": 10,
    "max_risk_dollars": 5000,
    "risk_percentage": 5.0
  },
  "exit_plan": {
    "profit_targets": [
      {"percentage": 50, "contracts_to_close": "40%"},
      {"percentage": 75, "contracts_to_close": "40%"},
      {"percentage": 90, "contracts_to_close": "remaining"}
    ],
    "stop_loss": "150% of credit",
    "time_stop": "21 DTE for PRIMARY only",
    "delta_stop": 0.30
  },
  "risk_checks": {
    "directional_filter_passed": true,
    "iv_rank_sufficient": true,
    "spread_quality_ok": true,
    "event_blackout_clear": true,
    "portfolio_delta_ok": true
  },
  "reasoning": "Excellent setup for iron condor deployment. IV rank of 75% triggers the ≥65 threshold for dual-sided strategy."
}
```
Additional text after JSON'''

print("Testing different regex patterns:\n")

# Pattern 1: Original pattern
pattern1 = r'```json\s*(.*?)\s*```'
match1 = re.search(pattern1, content, re.DOTALL)
print(f"Pattern 1 match: {bool(match1)}")
if match1:
    print(f"  Extracted length: {len(match1.group(1).strip())}")

# Pattern 2: With newlines
pattern2 = r'```json\s*\n(.*?)\n```'
match2 = re.search(pattern2, content, re.DOTALL)
print(f"Pattern 2 match: {bool(match2)}")
if match2:
    print(f"  Extracted length: {len(match2.group(1).strip())}")

# Pattern 3: More flexible
pattern3 = r'```json\s*\n?(.*?)\n?```'
match3 = re.search(pattern3, content, re.DOTALL)
print(f"Pattern 3 match: {bool(match3)}")
if match3:
    json_str = match3.group(1).strip()
    print(f"  Extracted length: {len(json_str)}")
    try:
        data = json.loads(json_str)
        print(f"  ✅ Valid JSON! should_trade={data['should_trade']}")
    except Exception as e:
        print(f"  ❌ Invalid JSON: {e}")
        print(f"  First 100 chars: {json_str[:100]}")

# Pattern 4: Just extract between braces
start = content.find('{')
end = content.rfind('}')
if start != -1 and end != -1:
    json_str = content[start:end+1]
    print(f"\nDirect extraction between {{ }}: length={len(json_str)}")
    try:
        data = json.loads(json_str)
        print(f"  ✅ Valid JSON! should_trade={data['should_trade']}")
    except Exception as e:
        print(f"  ❌ Invalid JSON: {e}")