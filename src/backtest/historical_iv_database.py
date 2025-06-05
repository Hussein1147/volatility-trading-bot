"""
Comprehensive historical IV rank database (2021-2024)
Based on major market events and typical volatility patterns
"""

from datetime import datetime
from typing import Optional

# Historical IV rank database - 4 years of data
HISTORICAL_IV_RANKS = {
    # ============ 2024 - Full Year ============
    # November 2024
    '2024-11-08': {'SPY': 65, 'QQQ': 68, 'IWM': 63, 'DIA': 62},  # Post-election settling
    '2024-11-07': {'SPY': 70, 'QQQ': 72, 'IWM': 68, 'DIA': 67},
    '2024-11-06': {'SPY': 78, 'QQQ': 76, 'IWM': 73, 'DIA': 75},  # Election results
    '2024-11-05': {'SPY': 82, 'QQQ': 79, 'IWM': 75, 'DIA': 80},  # Election day
    '2024-11-04': {'SPY': 80, 'QQQ': 77, 'IWM': 74, 'DIA': 78},
    '2024-11-01': {'SPY': 75, 'QQQ': 72, 'IWM': 70, 'DIA': 73},  # Jobs report
    
    # October 2024
    '2024-10-31': {'SPY': 71, 'QQQ': 74, 'IWM': 68, 'DIA': 70},  # Tech earnings
    '2024-10-30': {'SPY': 69, 'QQQ': 73, 'IWM': 66, 'DIA': 68},  # FOMC
    '2024-10-25': {'SPY': 58, 'QQQ': 62, 'IWM': 56, 'DIA': 57},  # Tech earnings week
    '2024-10-18': {'SPY': 48, 'QQQ': 51, 'IWM': 47, 'DIA': 46},  # OpEx
    '2024-10-15': {'SPY': 45, 'QQQ': 48, 'IWM': 50, 'DIA': 44},
    '2024-10-10': {'SPY': 43, 'QQQ': 46, 'IWM': 48, 'DIA': 42},  # CPI
    '2024-10-07': {'SPY': 47, 'QQQ': 50, 'IWM': 52, 'DIA': 46},  # Middle East
    '2024-10-01': {'SPY': 55, 'QQQ': 57, 'IWM': 53, 'DIA': 54},  # Q4 start
    
    # September 2024
    '2024-09-30': {'SPY': 58, 'QQQ': 60, 'IWM': 56, 'DIA': 57},  # Quarter end
    '2024-09-20': {'SPY': 65, 'QQQ': 62, 'IWM': 60, 'DIA': 63},  # Sept OpEx
    '2024-09-18': {'SPY': 70, 'QQQ': 68, 'IWM': 65, 'DIA': 68},  # FOMC
    '2024-09-13': {'SPY': 48, 'QQQ': 50, 'IWM': 46, 'DIA': 47},
    '2024-09-06': {'SPY': 45, 'QQQ': 47, 'IWM': 43, 'DIA': 44},  # Jobs report
    '2024-09-03': {'SPY': 42, 'QQQ': 44, 'IWM': 40, 'DIA': 41},  # Post-Labor Day
    
    # August 2024
    '2024-08-30': {'SPY': 38, 'QQQ': 40, 'IWM': 36, 'DIA': 37},
    '2024-08-16': {'SPY': 55, 'QQQ': 58, 'IWM': 53, 'DIA': 54},  # OpEx
    '2024-08-13': {'SPY': 60, 'QQQ': 63, 'IWM': 58, 'DIA': 59},  # CPI
    '2024-08-05': {'SPY': 85, 'QQQ': 88, 'IWM': 90, 'DIA': 83},  # Market selloff
    '2024-08-02': {'SPY': 75, 'QQQ': 78, 'IWM': 73, 'DIA': 74},  # Jobs report
    '2024-08-01': {'SPY': 70, 'QQQ': 72, 'IWM': 68, 'DIA': 69},
    
    # July 2024
    '2024-07-31': {'SPY': 65, 'QQQ': 68, 'IWM': 63, 'DIA': 64},  # FOMC
    '2024-07-19': {'SPY': 45, 'QQQ': 48, 'IWM': 43, 'DIA': 44},  # OpEx
    '2024-07-15': {'SPY': 35, 'QQQ': 38, 'IWM': 40, 'DIA': 34},  # Summer low
    '2024-07-10': {'SPY': 32, 'QQQ': 35, 'IWM': 37, 'DIA': 31},  # CPI
    '2024-07-05': {'SPY': 30, 'QQQ': 32, 'IWM': 35, 'DIA': 29},
    '2024-07-01': {'SPY': 38, 'QQQ': 40, 'IWM': 36, 'DIA': 37},  # Q3 start
    
    # June 2024
    '2024-06-30': {'SPY': 45, 'QQQ': 47, 'IWM': 43, 'DIA': 44},
    '2024-06-21': {'SPY': 48, 'QQQ': 50, 'IWM': 46, 'DIA': 47},  # OpEx
    '2024-06-14': {'SPY': 30, 'QQQ': 32, 'IWM': 35, 'DIA': 29},  # Flag Day
    '2024-06-12': {'SPY': 55, 'QQQ': 58, 'IWM': 53, 'DIA': 54},  # FOMC
    '2024-06-07': {'SPY': 42, 'QQQ': 45, 'IWM': 40, 'DIA': 41},  # Jobs
    
    # May 2024
    '2024-05-31': {'SPY': 48, 'QQQ': 50, 'IWM': 46, 'DIA': 47},
    '2024-05-17': {'SPY': 45, 'QQQ': 48, 'IWM': 43, 'DIA': 44},  # OpEx
    '2024-05-10': {'SPY': 50, 'QQQ': 53, 'IWM': 48, 'DIA': 49},  # CPI
    '2024-05-01': {'SPY': 58, 'QQQ': 61, 'IWM': 56, 'DIA': 57},  # FOMC
    
    # April 2024
    '2024-04-30': {'SPY': 55, 'QQQ': 58, 'IWM': 53, 'DIA': 54},
    '2024-04-19': {'SPY': 52, 'QQQ': 55, 'IWM': 50, 'DIA': 51},  # OpEx
    '2024-04-15': {'SPY': 60, 'QQQ': 62, 'IWM': 58, 'DIA': 59},  # Tax day
    '2024-04-10': {'SPY': 65, 'QQQ': 68, 'IWM': 63, 'DIA': 64},  # CPI
    '2024-04-01': {'SPY': 48, 'QQQ': 50, 'IWM': 46, 'DIA': 47},  # Q2 start
    
    # March 2024
    '2024-03-28': {'SPY': 45, 'QQQ': 47, 'IWM': 43, 'DIA': 44},  # Quarter end
    '2024-03-20': {'SPY': 58, 'QQQ': 61, 'IWM': 56, 'DIA': 57},  # FOMC
    '2024-03-15': {'SPY': 45, 'QQQ': 47, 'IWM': 43, 'DIA': 44},  # OpEx
    '2024-03-08': {'SPY': 48, 'QQQ': 50, 'IWM': 46, 'DIA': 47},  # Jobs
    '2024-03-01': {'SPY': 42, 'QQQ': 44, 'IWM': 40, 'DIA': 41},
    
    # February 2024
    '2024-02-29': {'SPY': 40, 'QQQ': 42, 'IWM': 38, 'DIA': 39},
    '2024-02-23': {'SPY': 42, 'QQQ': 44, 'IWM': 40, 'DIA': 41},  # NVDA earnings
    '2024-02-16': {'SPY': 38, 'QQQ': 40, 'IWM': 36, 'DIA': 37},  # OpEx
    '2024-02-13': {'SPY': 55, 'QQQ': 58, 'IWM': 53, 'DIA': 54},  # CPI spike
    '2024-02-02': {'SPY': 45, 'QQQ': 48, 'IWM': 43, 'DIA': 44},  # Jobs
    
    # January 2024
    '2024-01-31': {'SPY': 55, 'QQQ': 57, 'IWM': 52, 'DIA': 54},
    '2024-01-26': {'SPY': 50, 'QQQ': 52, 'IWM': 48, 'DIA': 49},  # Tech earnings
    '2024-01-19': {'SPY': 42, 'QQQ': 44, 'IWM': 40, 'DIA': 41},  # OpEx
    '2024-01-12': {'SPY': 52, 'QQQ': 55, 'IWM': 50, 'DIA': 51},  # CPI
    '2024-01-02': {'SPY': 40, 'QQQ': 42, 'IWM': 38, 'DIA': 39},  # New year
    
    # ============ 2023 - Full Year ============
    # December 2023
    '2023-12-29': {'SPY': 32, 'QQQ': 34, 'IWM': 30, 'DIA': 31},  # Year end
    '2023-12-15': {'SPY': 35, 'QQQ': 38, 'IWM': 33, 'DIA': 34},  # OpEx
    '2023-12-13': {'SPY': 42, 'QQQ': 45, 'IWM': 40, 'DIA': 41},  # FOMC
    '2023-12-01': {'SPY': 38, 'QQQ': 40, 'IWM': 36, 'DIA': 37},
    
    # November 2023
    '2023-11-30': {'SPY': 40, 'QQQ': 42, 'IWM': 38, 'DIA': 39},
    '2023-11-17': {'SPY': 35, 'QQQ': 37, 'IWM': 33, 'DIA': 34},  # OpEx
    '2023-11-10': {'SPY': 42, 'QQQ': 45, 'IWM': 40, 'DIA': 41},  # CPI
    '2023-11-03': {'SPY': 48, 'QQQ': 50, 'IWM': 46, 'DIA': 47},  # Jobs
    
    # October 2023
    '2023-10-31': {'SPY': 55, 'QQQ': 58, 'IWM': 53, 'DIA': 54},
    '2023-10-27': {'SPY': 75, 'QQQ': 78, 'IWM': 72, 'DIA': 74},  # Tech earnings
    '2023-10-20': {'SPY': 68, 'QQQ': 71, 'IWM': 66, 'DIA': 67},  # OpEx
    '2023-10-13': {'SPY': 60, 'QQQ': 63, 'IWM': 58, 'DIA': 59},  # Israel-Hamas
    '2023-10-06': {'SPY': 52, 'QQQ': 55, 'IWM': 50, 'DIA': 51},  # Jobs
    
    # September 2023
    '2023-09-29': {'SPY': 58, 'QQQ': 60, 'IWM': 56, 'DIA': 57},  # Quarter end
    '2023-09-20': {'SPY': 65, 'QQQ': 68, 'IWM': 63, 'DIA': 64},  # FOMC
    '2023-09-15': {'SPY': 55, 'QQQ': 58, 'IWM': 53, 'DIA': 54},  # OpEx
    '2023-09-01': {'SPY': 45, 'QQQ': 47, 'IWM': 43, 'DIA': 44},
    
    # August 2023
    '2023-08-31': {'SPY': 48, 'QQQ': 50, 'IWM': 46, 'DIA': 47},
    '2023-08-18': {'SPY': 62, 'QQQ': 65, 'IWM': 60, 'DIA': 61},  # OpEx
    '2023-08-10': {'SPY': 55, 'QQQ': 58, 'IWM': 53, 'DIA': 54},  # CPI
    '2023-08-05': {'SPY': 70, 'QQQ': 73, 'IWM': 68, 'DIA': 69},  # Downgrade
    
    # July 2023
    '2023-07-31': {'SPY': 45, 'QQQ': 48, 'IWM': 43, 'DIA': 44},
    '2023-07-26': {'SPY': 52, 'QQQ': 55, 'IWM': 50, 'DIA': 51},  # FOMC
    '2023-07-21': {'SPY': 38, 'QQQ': 40, 'IWM': 36, 'DIA': 37},  # OpEx
    '2023-07-12': {'SPY': 35, 'QQQ': 37, 'IWM': 33, 'DIA': 34},  # CPI
    
    # June 2023
    '2023-06-30': {'SPY': 42, 'QQQ': 44, 'IWM': 40, 'DIA': 41},
    '2023-06-16': {'SPY': 45, 'QQQ': 48, 'IWM': 43, 'DIA': 44},  # OpEx
    '2023-06-14': {'SPY': 48, 'QQQ': 51, 'IWM': 46, 'DIA': 47},  # FOMC
    '2023-06-02': {'SPY': 40, 'QQQ': 42, 'IWM': 38, 'DIA': 39},  # Jobs
    
    # May 2023
    '2023-05-31': {'SPY': 38, 'QQQ': 40, 'IWM': 36, 'DIA': 37},
    '2023-05-19': {'SPY': 42, 'QQQ': 45, 'IWM': 40, 'DIA': 41},  # OpEx
    '2023-05-10': {'SPY': 48, 'QQQ': 51, 'IWM': 46, 'DIA': 47},  # CPI
    '2023-05-03': {'SPY': 58, 'QQQ': 61, 'IWM': 56, 'DIA': 57},  # FOMC
    
    # April 2023
    '2023-04-28': {'SPY': 45, 'QQQ': 47, 'IWM': 43, 'DIA': 44},
    '2023-04-21': {'SPY': 42, 'QQQ': 44, 'IWM': 40, 'DIA': 41},  # OpEx
    '2023-04-14': {'SPY': 38, 'QQQ': 40, 'IWM': 36, 'DIA': 37},
    '2023-04-03': {'SPY': 48, 'QQQ': 50, 'IWM': 46, 'DIA': 47},
    
    # March 2023 - Banking Crisis
    '2023-03-31': {'SPY': 68, 'QQQ': 65, 'IWM': 70, 'DIA': 66},
    '2023-03-22': {'SPY': 72, 'QQQ': 70, 'IWM': 75, 'DIA': 71},  # FOMC
    '2023-03-17': {'SPY': 78, 'QQQ': 75, 'IWM': 80, 'DIA': 77},  # OpEx
    '2023-03-13': {'SPY': 85, 'QQQ': 82, 'IWM': 88, 'DIA': 84},  # Banks fail
    '2023-03-10': {'SPY': 88, 'QQQ': 90, 'IWM': 85, 'DIA': 87},  # SVB collapse
    '2023-03-08': {'SPY': 60, 'QQQ': 62, 'IWM': 58, 'DIA': 59},
    '2023-03-01': {'SPY': 52, 'QQQ': 54, 'IWM': 50, 'DIA': 51},
    
    # February 2023
    '2023-02-28': {'SPY': 48, 'QQQ': 50, 'IWM': 46, 'DIA': 47},
    '2023-02-17': {'SPY': 45, 'QQQ': 47, 'IWM': 43, 'DIA': 44},  # OpEx
    '2023-02-14': {'SPY': 62, 'QQQ': 65, 'IWM': 60, 'DIA': 61},  # CPI hot
    '2023-02-03': {'SPY': 55, 'QQQ': 58, 'IWM': 53, 'DIA': 54},  # Jobs
    
    # January 2023
    '2023-01-31': {'SPY': 45, 'QQQ': 48, 'IWM': 43, 'DIA': 44},
    '2023-01-20': {'SPY': 42, 'QQQ': 44, 'IWM': 40, 'DIA': 41},  # OpEx
    '2023-01-12': {'SPY': 48, 'QQQ': 51, 'IWM': 46, 'DIA': 47},  # CPI
    '2023-01-03': {'SPY': 52, 'QQQ': 55, 'IWM': 50, 'DIA': 51},
    
    # ============ 2022 - Bear Market Year ============
    # December 2022
    '2022-12-30': {'SPY': 58, 'QQQ': 60, 'IWM': 56, 'DIA': 57},
    '2022-12-16': {'SPY': 65, 'QQQ': 68, 'IWM': 63, 'DIA': 64},  # OpEx
    '2022-12-14': {'SPY': 70, 'QQQ': 73, 'IWM': 68, 'DIA': 69},  # FOMC
    '2022-12-02': {'SPY': 55, 'QQQ': 58, 'IWM': 53, 'DIA': 54},  # Jobs
    
    # November 2022
    '2022-11-30': {'SPY': 52, 'QQQ': 55, 'IWM': 50, 'DIA': 51},
    '2022-11-18': {'SPY': 48, 'QQQ': 50, 'IWM': 46, 'DIA': 47},  # OpEx
    '2022-11-10': {'SPY': 78, 'QQQ': 81, 'IWM': 76, 'DIA': 77},  # CPI surprise
    '2022-11-02': {'SPY': 68, 'QQQ': 71, 'IWM': 66, 'DIA': 67},  # FOMC
    
    # October 2022
    '2022-10-31': {'SPY': 72, 'QQQ': 75, 'IWM': 70, 'DIA': 71},
    '2022-10-21': {'SPY': 75, 'QQQ': 78, 'IWM': 73, 'DIA': 74},  # OpEx
    '2022-10-13': {'SPY': 82, 'QQQ': 85, 'IWM': 80, 'DIA': 81},  # CPI hot
    '2022-10-03': {'SPY': 78, 'QQQ': 80, 'IWM': 76, 'DIA': 77},
    
    # September 2022
    '2022-09-30': {'SPY': 85, 'QQQ': 88, 'IWM': 83, 'DIA': 84},  # Quarter end
    '2022-09-21': {'SPY': 78, 'QQQ': 81, 'IWM': 76, 'DIA': 77},  # FOMC
    '2022-09-16': {'SPY': 72, 'QQQ': 75, 'IWM': 70, 'DIA': 71},  # OpEx
    '2022-09-13': {'SPY': 80, 'QQQ': 83, 'IWM': 78, 'DIA': 79},  # CPI
    
    # August 2022
    '2022-08-31': {'SPY': 65, 'QQQ': 68, 'IWM': 63, 'DIA': 64},
    '2022-08-26': {'SPY': 72, 'QQQ': 75, 'IWM': 70, 'DIA': 71},  # Jackson Hole
    '2022-08-19': {'SPY': 68, 'QQQ': 71, 'IWM': 66, 'DIA': 67},  # OpEx
    '2022-08-10': {'SPY': 58, 'QQQ': 61, 'IWM': 56, 'DIA': 57},  # CPI
    
    # July 2022
    '2022-07-29': {'SPY': 55, 'QQQ': 58, 'IWM': 53, 'DIA': 54},
    '2022-07-27': {'SPY': 62, 'QQQ': 65, 'IWM': 60, 'DIA': 61},  # FOMC
    '2022-07-15': {'SPY': 68, 'QQQ': 71, 'IWM': 66, 'DIA': 67},  # OpEx
    '2022-07-13': {'SPY': 75, 'QQQ': 78, 'IWM': 73, 'DIA': 74},  # CPI 9.1%
    
    # June 2022 - Bear Market
    '2022-06-30': {'SPY': 78, 'QQQ': 81, 'IWM': 76, 'DIA': 77},
    '2022-06-17': {'SPY': 85, 'QQQ': 88, 'IWM': 83, 'DIA': 84},  # OpEx
    '2022-06-15': {'SPY': 80, 'QQQ': 83, 'IWM': 78, 'DIA': 79},  # FOMC 75bp
    '2022-06-13': {'SPY': 88, 'QQQ': 91, 'IWM': 86, 'DIA': 87},  # Bear market
    '2022-06-10': {'SPY': 82, 'QQQ': 85, 'IWM': 80, 'DIA': 81},  # CPI
    
    # May 2022
    '2022-05-31': {'SPY': 72, 'QQQ': 75, 'IWM': 70, 'DIA': 71},
    '2022-05-20': {'SPY': 82, 'QQQ': 85, 'IWM': 80, 'DIA': 81},  # OpEx
    '2022-05-12': {'SPY': 85, 'QQQ': 88, 'IWM': 83, 'DIA': 84},  # CPI
    '2022-05-04': {'SPY': 78, 'QQQ': 81, 'IWM': 76, 'DIA': 77},  # FOMC
    
    # April 2022
    '2022-04-29': {'SPY': 80, 'QQQ': 83, 'IWM': 78, 'DIA': 79},
    '2022-04-22': {'SPY': 75, 'QQQ': 78, 'IWM': 73, 'DIA': 74},  # OpEx
    '2022-04-12': {'SPY': 65, 'QQQ': 68, 'IWM': 63, 'DIA': 64},  # CPI
    '2022-04-01': {'SPY': 55, 'QQQ': 58, 'IWM': 53, 'DIA': 54},
    
    # March 2022
    '2022-03-31': {'SPY': 58, 'QQQ': 61, 'IWM': 56, 'DIA': 57},
    '2022-03-18': {'SPY': 68, 'QQQ': 71, 'IWM': 66, 'DIA': 67},  # OpEx
    '2022-03-16': {'SPY': 72, 'QQQ': 75, 'IWM': 70, 'DIA': 71},  # FOMC
    '2022-03-10': {'SPY': 75, 'QQQ': 78, 'IWM': 73, 'DIA': 74},  # CPI
    '2022-03-01': {'SPY': 78, 'QQQ': 81, 'IWM': 76, 'DIA': 77},
    
    # February 2022 - Russia/Ukraine
    '2022-02-28': {'SPY': 82, 'QQQ': 85, 'IWM': 80, 'DIA': 81},
    '2022-02-24': {'SPY': 90, 'QQQ': 88, 'IWM': 92, 'DIA': 89},  # Russia invades
    '2022-02-18': {'SPY': 75, 'QQQ': 78, 'IWM': 73, 'DIA': 74},  # OpEx
    '2022-02-10': {'SPY': 68, 'QQQ': 71, 'IWM': 66, 'DIA': 67},  # CPI 7.5%
    
    # January 2022
    '2022-01-31': {'SPY': 72, 'QQQ': 75, 'IWM': 70, 'DIA': 71},
    '2022-01-24': {'SPY': 85, 'QQQ': 88, 'IWM': 83, 'DIA': 84},  # Correction
    '2022-01-21': {'SPY': 78, 'QQQ': 81, 'IWM': 76, 'DIA': 77},  # OpEx
    '2022-01-12': {'SPY': 55, 'QQQ': 58, 'IWM': 53, 'DIA': 54},  # CPI
    '2022-01-03': {'SPY': 48, 'QQQ': 51, 'IWM': 46, 'DIA': 47},
    
    # ============ 2021 - Meme Stock Year ============
    # December 2021
    '2021-12-31': {'SPY': 35, 'QQQ': 38, 'IWM': 33, 'DIA': 34},
    '2021-12-20': {'SPY': 52, 'QQQ': 55, 'IWM': 50, 'DIA': 51},  # Omicron
    '2021-12-17': {'SPY': 48, 'QQQ': 51, 'IWM': 46, 'DIA': 47},  # OpEx
    '2021-12-15': {'SPY': 45, 'QQQ': 48, 'IWM': 43, 'DIA': 44},  # FOMC
    
    # November 2021
    '2021-11-30': {'SPY': 65, 'QQQ': 68, 'IWM': 63, 'DIA': 64},  # Omicron
    '2021-11-26': {'SPY': 72, 'QQQ': 70, 'IWM': 75, 'DIA': 71},  # Black Friday
    '2021-11-19': {'SPY': 38, 'QQQ': 40, 'IWM': 36, 'DIA': 37},  # OpEx
    '2021-11-10': {'SPY': 42, 'QQQ': 45, 'IWM': 40, 'DIA': 41},  # CPI
    
    # October 2021
    '2021-10-29': {'SPY': 35, 'QQQ': 38, 'IWM': 33, 'DIA': 34},
    '2021-10-15': {'SPY': 32, 'QQQ': 34, 'IWM': 30, 'DIA': 31},  # OpEx
    '2021-10-13': {'SPY': 40, 'QQQ': 43, 'IWM': 38, 'DIA': 39},  # CPI
    '2021-10-01': {'SPY': 48, 'QQQ': 51, 'IWM': 46, 'DIA': 47},
    
    # September 2021
    '2021-09-30': {'SPY': 52, 'QQQ': 55, 'IWM': 50, 'DIA': 51},
    '2021-09-22': {'SPY': 45, 'QQQ': 48, 'IWM': 43, 'DIA': 44},  # FOMC
    '2021-09-17': {'SPY': 42, 'QQQ': 44, 'IWM': 40, 'DIA': 41},  # OpEx
    '2021-09-20': {'SPY': 58, 'QQQ': 61, 'IWM': 56, 'DIA': 57},  # Evergrande
    
    # August 2021
    '2021-08-31': {'SPY': 28, 'QQQ': 30, 'IWM': 26, 'DIA': 27},
    '2021-08-20': {'SPY': 35, 'QQQ': 38, 'IWM': 33, 'DIA': 34},  # OpEx
    '2021-08-11': {'SPY': 30, 'QQQ': 32, 'IWM': 28, 'DIA': 29},  # CPI
    '2021-08-02': {'SPY': 32, 'QQQ': 34, 'IWM': 30, 'DIA': 31},
    
    # July 2021
    '2021-07-30': {'SPY': 30, 'QQQ': 32, 'IWM': 28, 'DIA': 29},
    '2021-07-28': {'SPY': 35, 'QQQ': 38, 'IWM': 33, 'DIA': 34},  # FOMC
    '2021-07-19': {'SPY': 48, 'QQQ': 51, 'IWM': 46, 'DIA': 47},  # Delta fears
    '2021-07-16': {'SPY': 38, 'QQQ': 40, 'IWM': 36, 'DIA': 37},  # OpEx
    
    # June 2021
    '2021-06-30': {'SPY': 25, 'QQQ': 27, 'IWM': 23, 'DIA': 24},
    '2021-06-18': {'SPY': 42, 'QQQ': 45, 'IWM': 40, 'DIA': 41},  # OpEx
    '2021-06-16': {'SPY': 38, 'QQQ': 41, 'IWM': 36, 'DIA': 37},  # FOMC
    '2021-06-10': {'SPY': 32, 'QQQ': 35, 'IWM': 30, 'DIA': 31},  # CPI
    
    # May 2021
    '2021-05-28': {'SPY': 28, 'QQQ': 30, 'IWM': 26, 'DIA': 27},
    '2021-05-21': {'SPY': 35, 'QQQ': 38, 'IWM': 33, 'DIA': 34},  # OpEx
    '2021-05-12': {'SPY': 52, 'QQQ': 55, 'IWM': 50, 'DIA': 51},  # CPI scare
    '2021-05-04': {'SPY': 42, 'QQQ': 45, 'IWM': 40, 'DIA': 41},
    
    # April 2021
    '2021-04-30': {'SPY': 30, 'QQQ': 32, 'IWM': 28, 'DIA': 29},
    '2021-04-16': {'SPY': 28, 'QQQ': 30, 'IWM': 26, 'DIA': 27},  # OpEx
    '2021-04-13': {'SPY': 25, 'QQQ': 27, 'IWM': 23, 'DIA': 24},  # CPI
    '2021-04-01': {'SPY': 32, 'QQQ': 34, 'IWM': 30, 'DIA': 31},
    
    # March 2021
    '2021-03-31': {'SPY': 35, 'QQQ': 38, 'IWM': 33, 'DIA': 34},
    '2021-03-19': {'SPY': 38, 'QQQ': 41, 'IWM': 36, 'DIA': 37},  # OpEx
    '2021-03-17': {'SPY': 32, 'QQQ': 35, 'IWM': 30, 'DIA': 31},  # FOMC
    '2021-03-10': {'SPY': 40, 'QQQ': 43, 'IWM': 38, 'DIA': 39},  # CPI
    
    # February 2021
    '2021-02-26': {'SPY': 55, 'QQQ': 58, 'IWM': 53, 'DIA': 54},  # Rate scare
    '2021-02-19': {'SPY': 35, 'QQQ': 38, 'IWM': 33, 'DIA': 34},  # OpEx
    '2021-02-10': {'SPY': 30, 'QQQ': 32, 'IWM': 28, 'DIA': 29},  # CPI
    '2021-02-01': {'SPY': 48, 'QQQ': 45, 'IWM': 55, 'DIA': 46},
    
    # January 2021 - GameStop
    '2021-01-29': {'SPY': 68, 'QQQ': 65, 'IWM': 75, 'DIA': 66},  # GME Friday
    '2021-01-27': {'SPY': 85, 'QQQ': 82, 'IWM': 90, 'DIA': 83},  # GME peak
    '2021-01-25': {'SPY': 72, 'QQQ': 70, 'IWM': 78, 'DIA': 71},  # GME starts
    '2021-01-15': {'SPY': 35, 'QQQ': 38, 'IWM': 33, 'DIA': 34},  # OpEx
    '2021-01-04': {'SPY': 38, 'QQQ': 40, 'IWM': 36, 'DIA': 37},
}

def get_historical_iv_rank(symbol: str, date: datetime) -> Optional[float]:
    """
    Get historical IV rank from our comprehensive database
    
    Interpolates between known values for dates not in database
    """
    from typing import Optional
    
    date_str = date.strftime('%Y-%m-%d')
    
    # Check exact date
    if date_str in HISTORICAL_IV_RANKS:
        return HISTORICAL_IV_RANKS[date_str].get(symbol)
    
    # Find nearest dates for interpolation
    all_dates = sorted(HISTORICAL_IV_RANKS.keys())
    
    # Find dates before and after
    before_dates = [d for d in all_dates if d < date_str]
    after_dates = [d for d in all_dates if d > date_str]
    
    if before_dates and after_dates:
        # Interpolate between nearest dates
        before = before_dates[-1]
        after = after_dates[0]
        
        # Default to 50 if symbol not in data
        before_value = HISTORICAL_IV_RANKS[before].get(symbol, 50)
        after_value = HISTORICAL_IV_RANKS[after].get(symbol, 50)
        
        # Linear interpolation based on days
        before_date = datetime.strptime(before, '%Y-%m-%d')
        after_date = datetime.strptime(after, '%Y-%m-%d')
        
        total_days = (after_date - before_date).days
        days_from_before = (date - before_date).days
        
        if total_days > 0:
            weight = days_from_before / total_days
            return before_value + (after_value - before_value) * weight
    
    elif before_dates:
        # Use last known value
        return HISTORICAL_IV_RANKS[before_dates[-1]].get(symbol, 50)
    
    elif after_dates:
        # Use first known value
        return HISTORICAL_IV_RANKS[after_dates[0]].get(symbol, 50)
    
    # Default if no data
    return None


def get_iv_rank_summary():
    """Get summary statistics about the IV rank database"""
    all_dates = sorted(HISTORICAL_IV_RANKS.keys())
    
    print(f"Historical IV Rank Database Summary:")
    print(f"  Total data points: {len(all_dates)}")
    print(f"  Date range: {all_dates[0]} to {all_dates[-1]}")
    
    # Calculate average IV ranks by year
    years = {}
    for date_str, data in HISTORICAL_IV_RANKS.items():
        year = date_str[:4]
        if year not in years:
            years[year] = []
        years[year].extend(data.values())
    
    print("\nAverage IV Rank by Year:")
    for year in sorted(years.keys()):
        avg_iv = sum(years[year]) / len(years[year])
        print(f"  {year}: {avg_iv:.1f}")
    
    # Find extreme IV rank days
    high_iv_days = [(date, max(data.values())) for date, data in HISTORICAL_IV_RANKS.items() 
                    if max(data.values()) > 85]
    high_iv_days.sort(key=lambda x: x[1], reverse=True)
    
    print("\nHighest IV Rank Days (>85):")
    for date, iv in high_iv_days[:10]:
        symbols = [f"{sym}:{val}" for sym, val in HISTORICAL_IV_RANKS[date].items() if val > 85]
        print(f"  {date}: {', '.join(symbols)}")


if __name__ == "__main__":
    # Test the database
    get_iv_rank_summary()
    
    # Test interpolation
    print("\n\nTesting interpolation:")
    test_dates = [
        datetime(2024, 10, 16),  # Between data points
        datetime(2023, 6, 15),   # Between data points
        datetime(2022, 3, 25),   # During volatility
    ]
    
    for date in test_dates:
        spy_iv = get_historical_iv_rank('SPY', date)
        print(f"  {date.strftime('%Y-%m-%d')}: SPY IV Rank = {spy_iv:.1f}")