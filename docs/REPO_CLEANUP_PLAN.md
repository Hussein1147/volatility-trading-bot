# Repository Cleanup Plan

## Current Structure Analysis

### Test/Debug Scripts (to organize)
- `scripts/` - Mixed production and test scripts
- `scripts/data_verification/` - 14 test files
- `scripts/tests/` - 6 test files  
- `tests/` - 3 test files
- Multiple test files scattered in root scripts folder

### Duplicate Functionality
- Multiple backtest test scripts doing similar things
- Several Alpaca test scripts with overlapping functionality
- Debug scripts that could be consolidated

### Proposed Organization

```
volatility-trading-bot/
├── src/                    # Core application code (KEEP AS IS)
│   ├── backtest/          # Backtesting engine
│   ├── core/              # Trading logic
│   ├── data/              # Database/data handling
│   └── ui/                # Dashboard code
├── scripts/               # Executable scripts
│   ├── production/        # Production-ready scripts
│   │   ├── run_backtest.py
│   │   ├── run_dashboard.py
│   │   └── verify_system.py
│   └── examples/          # Example configurations
│       └── backtest_config_example.py
├── tests/                 # All test files
│   ├── unit/              # Unit tests
│   ├── integration/       # Integration tests
│   │   ├── alpaca/        # Alpaca-specific tests
│   │   ├── tastytrade/    # TastyTrade tests
│   │   └── polygon/       # Polygon tests
│   └── utils/             # Test utilities
├── data/                  # Data storage (KEEP AS IS)
├── docs/                  # Documentation (KEEP AS IS)
├── deployment/            # Deployment scripts (KEEP AS IS)
└── sql/                   # Database scripts (KEEP AS IS)
```

## Files to Move/Organize

### Move to tests/integration/alpaca/
- scripts/data_verification/test_alpaca_*.py
- scripts/tests/test_alpaca_*.py
- scripts/verify_alpaca_data.py
- scripts/check_alpaca_iv_data.py

### Move to tests/integration/backtest/
- scripts/data_verification/test_backtest_*.py
- scripts/tests/test_backtest_*.py
- scripts/debug_backtest_flow.py
- scripts/test_real_iv_backtest.py

### Move to tests/integration/api/
- scripts/test_tastytrade_data.py
- scripts/test_polygon_tastytrade_options.py
- scripts/test_free_options_apis.py

### Move to tests/unit/
- tests/test_core.py
- tests/test_simple.py
- tests/test_suite.py

### Move to scripts/production/
- run_backtest.py (from root)
- run_dashboard.py (from root)
- scripts/verify_system.py

### Keep in scripts/examples/
- scripts/backtest_config_example.py

## Files to Consider Removing (after backup)
- Redundant test files that do the same thing
- Old debug scripts that are no longer needed
- Temporary test outputs

## Critical Files to Preserve
- All src/ code
- Configuration files (.env example, requirements.txt)
- Documentation
- Database schemas
- Deployment scripts