"""
Verify historical IV rank data is working correctly
"""

from datetime import datetime, timedelta
import pandas as pd
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.backtest.historical_iv_database import get_historical_iv_rank, HISTORICAL_IV_RANKS

def verify_iv_data():
    """Verify IV data availability and interpolation"""
    
    print("=" * 80)
    print("HISTORICAL IV RANK DATABASE VERIFICATION")
    print("=" * 80)
    
    # 1. Database summary
    all_dates = sorted(HISTORICAL_IV_RANKS.keys())
    print(f"\n1. Database Summary:")
    print(f"   Total data points: {len(all_dates)}")
    print(f"   Date range: {all_dates[0]} to {all_dates[-1]}")
    
    # Count by year
    years = {}
    for date in all_dates:
        year = date[:4]
        years[year] = years.get(year, 0) + 1
    
    print(f"\n   Data points by year:")
    for year in sorted(years.keys()):
        print(f"     {year}: {years[year]} days")
    
    # 2. Test specific dates
    print(f"\n2. Testing Specific Dates:")
    test_cases = [
        # Known high volatility events
        ('2024-08-05', "Market selloff"),
        ('2023-03-10', "SVB collapse"),
        ('2022-06-13', "Bear market"),
        ('2021-01-27', "GameStop peak"),
        
        # Interpolated dates
        ('2024-08-03', "Interpolated"),
        ('2023-06-25', "Interpolated"),
        
        # Edge cases
        ('2020-12-31', "Before data range"),
        ('2025-01-01', "After data range"),
    ]
    
    for date_str, description in test_cases:
        date = datetime.strptime(date_str, '%Y-%m-%d')
        
        print(f"\n   {date_str} ({description}):")
        for symbol in ['SPY', 'QQQ', 'IWM', 'DIA']:
            iv_rank = get_historical_iv_rank(symbol, date)
            if iv_rank is not None:
                print(f"     {symbol}: {iv_rank:.1f}")
            else:
                print(f"     {symbol}: No data")
    
    # 3. Test interpolation accuracy
    print(f"\n3. Testing Interpolation:")
    
    # Pick a date between two known points
    before_date = '2024-08-01'
    after_date = '2024-08-05'
    middle_date = datetime(2024, 8, 3)
    
    spy_before = HISTORICAL_IV_RANKS[before_date]['SPY']
    spy_after = HISTORICAL_IV_RANKS[after_date]['SPY']
    spy_interpolated = get_historical_iv_rank('SPY', middle_date)
    
    print(f"   SPY IV Rank:")
    print(f"     {before_date}: {spy_before}")
    print(f"     2024-08-03 (interpolated): {spy_interpolated:.1f}")
    print(f"     {after_date}: {spy_after}")
    print(f"     Expected (linear): {spy_before + (spy_after - spy_before) * 2/4:.1f}")
    
    # 4. Find periods with high IV
    print(f"\n4. High IV Periods (>80):")
    high_iv_periods = []
    
    for date_str, data in HISTORICAL_IV_RANKS.items():
        max_iv = max(data.values())
        if max_iv > 80:
            symbols = [f"{sym}:{val}" for sym, val in data.items() if val > 80]
            high_iv_periods.append((date_str, symbols))
    
    # Show first 10
    for date, symbols in high_iv_periods[:10]:
        print(f"   {date}: {', '.join(symbols)}")
    
    print(f"\n   Total high IV days: {len(high_iv_periods)}")
    
    # 5. Test for gaps
    print(f"\n5. Checking for Data Gaps:")
    
    date_objs = [datetime.strptime(d, '%Y-%m-%d') for d in all_dates]
    gaps = []
    
    for i in range(1, len(date_objs)):
        diff = (date_objs[i] - date_objs[i-1]).days
        if diff > 7:  # More than a week gap
            gaps.append((all_dates[i-1], all_dates[i], diff))
    
    if gaps:
        print(f"   Found {len(gaps)} gaps > 7 days:")
        for start, end, days in gaps[:5]:
            print(f"     {start} to {end}: {days} days")
    else:
        print("   No significant gaps found")
    
    # 6. Statistics
    print(f"\n6. IV Rank Statistics:")
    
    all_values = []
    for data in HISTORICAL_IV_RANKS.values():
        all_values.extend(data.values())
    
    df = pd.DataFrame(all_values, columns=['iv_rank'])
    
    print(f"   Overall statistics:")
    print(f"     Mean: {df['iv_rank'].mean():.1f}")
    print(f"     Median: {df['iv_rank'].median():.1f}")
    print(f"     Std Dev: {df['iv_rank'].std():.1f}")
    print(f"     Min: {df['iv_rank'].min()}")
    print(f"     Max: {df['iv_rank'].max()}")
    
    # Distribution
    print(f"\n   Distribution:")
    bins = [0, 30, 50, 70, 90, 100]
    labels = ['0-30 (Low)', '30-50 (Normal)', '50-70 (Elevated)', '70-90 (High)', '90-100 (Extreme)']
    
    df['bin'] = pd.cut(df['iv_rank'], bins=bins, labels=labels)
    distribution = df['bin'].value_counts().sort_index()
    
    for label, count in distribution.items():
        pct = (count / len(df)) * 100
        print(f"     {label}: {count} ({pct:.1f}%)")


if __name__ == "__main__":
    verify_iv_data()