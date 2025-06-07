# Fixed: Claude's Analysis Not Populated in Saved Results

## Problem
When loading saved backtest runs in the dashboard, Claude's analyses were not being displayed even though trades were shown. The "Claude Analyses" tab showed "No analyses found for this run".

## Root Cause
The backtest engine was generating Claude analyses during the run but not saving them to the database. The analyses were being tracked internally but not persisted when saving the backtest results.

## Solution Implemented

1. **Added analysis tracking in BacktestEngine** (`backtest_engine.py`):
   - Added `self.all_analyses = []` list to track all analyses
   - Created `pending_analysis` to temporarily store analysis data
   - Updated analysis data with strike info when trades are executed
   - Also captured analyses that don't result in trades (low confidence)

2. **Modified dashboard to save analyses** (`backtest_dashboard.py`):
   - After backtest completes, iterate through `engine.all_analyses`
   - Save each analysis to database using `backtest_db.save_analysis()`
   - Links analyses to the run_id for later retrieval

3. **Database schema already supported this** (`backtest_db.py`):
   - `backtest_analyses` table was already created
   - Methods `save_analysis()` and `get_run_analyses()` were ready

## Testing
- Created test script `test_analysis_saving.py` to verify functionality
- Confirmed analyses are now saved and loaded correctly
- Old runs (before fix) show 0 analyses, new runs show proper count

## Usage
No changes needed to use the feature. Simply:
1. Run a backtest as normal
2. Go to "Saved Results" tab
3. Select a run
4. Click "Claude Analyses" tab to see all AI analyses

## Benefits
- Complete audit trail of AI decision making
- Can review Claude's reasoning for both trades taken and passed
- Helps identify patterns in successful vs unsuccessful analyses
- Provides transparency into the AI's decision process