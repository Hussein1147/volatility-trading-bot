"""
Unit tests for synthetic option pricing
"""

import pytest
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from src.engines.synthetic_pricer import SyntheticOptionPricer


class TestSyntheticOptionPricer:
    """Test Black-Scholes option pricing implementation"""
    
    @pytest.fixture
    def pricer(self):
        """Create a pricer instance"""
        return SyntheticOptionPricer(risk_free_rate=0.0)
    
    def test_call_put_parity(self, pricer):
        """Test put-call parity relationship"""
        # Set up test parameters
        S = 100  # Spot price
        K = 100  # Strike price
        T = 0.25  # 3 months
        sigma = 0.20  # 20% volatility
        
        # Price call and put
        call_price = pricer._black_scholes_price(S, K, T, sigma, 'call')
        put_price = pricer._black_scholes_price(S, K, T, sigma, 'put')
        
        # Put-call parity: C - P = S - K * exp(-rT)
        # With r=0: C - P = S - K
        parity_diff = call_price - put_price
        expected_diff = S - K * np.exp(-pricer.r * T)
        
        assert abs(parity_diff - expected_diff) < 0.01, \
            f"Put-call parity violated: {parity_diff} vs {expected_diff}"
    
    def test_price_boundaries(self, pricer):
        """Test option prices are within valid boundaries"""
        S = 100
        T = 0.25
        sigma = 0.20
        
        # Test various strikes
        for K in [80, 90, 100, 110, 120]:
            call_price = pricer._black_scholes_price(S, K, T, sigma, 'call')
            put_price = pricer._black_scholes_price(S, K, T, sigma, 'put')
            
            # Call price bounds: max(S - K, 0) <= C <= S
            assert call_price >= max(S - K, 0), f"Call price {call_price} below intrinsic value"
            assert call_price <= S, f"Call price {call_price} above spot price"
            
            # Put price bounds: max(K - S, 0) <= P <= K
            assert put_price >= max(K - S, 0), f"Put price {put_price} below intrinsic value"
            assert put_price <= K, f"Put price {put_price} above strike"
    
    def test_delta_bounds(self, pricer):
        """Test delta values are within valid range"""
        S = 100
        T = 0.25
        sigma = 0.20
        
        for K in [80, 90, 100, 110, 120]:
            call_delta = pricer._black_scholes_delta(S, K, T, sigma, 'call')
            put_delta = pricer._black_scholes_delta(S, K, T, sigma, 'put')
            
            # Call delta: 0 <= delta <= 1
            assert 0 <= call_delta <= 1, f"Call delta {call_delta} out of bounds"
            
            # Put delta: -1 <= delta <= 0
            assert -1 <= put_delta <= 0, f"Put delta {put_delta} out of bounds"
            
            # Put-call delta relationship: call_delta - put_delta = 1
            assert abs((call_delta - put_delta) - 1) < 0.001, \
                f"Delta parity violated: {call_delta} - {put_delta} != 1"
    
    def test_spread_pricing_consistency(self, pricer):
        """Test spread pricing is consistent with individual options"""
        date = pd.Timestamp('2024-01-15')
        expiry = pd.Timestamp('2024-02-15')
        S = 100
        iv = 0.20
        
        # Put spread
        put_strikes = (95, 90)
        put_spread_price = pricer.price_spread(date, S, put_strikes, expiry, iv)
        
        # Price individual options
        T = (expiry - date).days / 365.0
        short_put = pricer._black_scholes_price(S, put_strikes[0], T, iv, 'put')
        long_put = pricer._black_scholes_price(S, put_strikes[1], T, iv, 'put')
        expected_spread = short_put - long_put
        
        assert abs(put_spread_price - expected_spread) < 0.01, \
            f"Put spread price {put_spread_price} != {expected_spread}"
        
        # Call spread
        call_strikes = (105, 110)
        call_spread_price = pricer.price_spread(date, S, call_strikes, expiry, iv)
        
        short_call = pricer._black_scholes_price(S, call_strikes[0], T, iv, 'call')
        long_call = pricer._black_scholes_price(S, call_strikes[1], T, iv, 'call')
        expected_spread = short_call - long_call
        
        assert abs(call_spread_price - expected_spread) < 0.01, \
            f"Call spread price {call_spread_price} != {expected_spread}"
    
    def test_spread_delta_calculation(self, pricer):
        """Test spread delta calculations"""
        date = pd.Timestamp('2024-01-15')
        expiry = pd.Timestamp('2024-02-15')
        S = 100
        iv = 0.20
        
        # Put spread deltas
        put_strikes = (95, 90)
        short_delta, long_delta = pricer.calc_delta(date, S, put_strikes, expiry, iv)
        
        # Both should be negative for puts
        assert short_delta < 0, f"Short put delta {short_delta} should be negative"
        assert long_delta < 0, f"Long put delta {long_delta} should be negative"
        
        # Short strike (higher) should have larger delta (less negative)
        assert short_delta > long_delta, \
            f"Short put delta {short_delta} should be > long put delta {long_delta}"
        
        # Net delta should be positive (we're short the higher strike)
        net_delta = short_delta + long_delta
        assert net_delta < 0, f"Put spread net delta {net_delta} should be negative"
    
    def test_expired_options(self, pricer):
        """Test pricing of expired options"""
        date = pd.Timestamp('2024-02-15')
        expiry = pd.Timestamp('2024-02-15')  # Same day = expired
        iv = 0.20
        
        # ITM put spread
        S = 90
        put_strikes = (95, 90)
        spread_value = pricer.price_spread(date, S, put_strikes, expiry, iv)
        
        # Should equal intrinsic value
        expected = pricer._intrinsic_value_spread(S, put_strikes)
        assert abs(spread_value - expected) < 0.01, \
            f"Expired spread value {spread_value} != intrinsic {expected}"
        
        # OTM call spread
        S = 100
        call_strikes = (105, 110)
        spread_value = pricer.price_spread(date, S, call_strikes, expiry, iv)
        
        # Should be worthless
        assert abs(spread_value) < 0.01, \
            f"OTM expired spread should be worthless, got {spread_value}"
    
    def test_iv_caching(self, pricer):
        """Test IV caching functionality"""
        # Cache some IVs
        pricer.cache_iv('SPY', 0.18)
        pricer.cache_iv('QQQ', 0.22)
        
        # Retrieve cached values
        assert pricer.get_cached_iv('SPY') == 0.18
        assert pricer.get_cached_iv('QQQ') == 0.22
        assert pricer.get_cached_iv('IWM') is None
    
    def test_iv_estimation(self, pricer):
        """Test IV estimation from market conditions"""
        # Test with VIX
        iv = pricer.estimate_iv_from_market_conditions('SPY', vix=20)
        assert abs(iv - 0.20) < 0.01, f"SPY IV with VIX=20 should be ~0.20, got {iv}"
        
        # Test with historical vol
        iv = pricer.estimate_iv_from_market_conditions('QQQ', historical_vol=0.25)
        assert abs(iv - 0.25) < 0.01, f"IV from hist vol should match, got {iv}"
        
        # Test caching
        iv2 = pricer.estimate_iv_from_market_conditions('QQQ')
        assert iv2 == iv, "Should return cached IV"
    
    def test_price_symmetry(self, pricer):
        """Test pricing symmetry properties"""
        date = pd.Timestamp('2024-01-15')
        expiry = pd.Timestamp('2024-02-15')
        S = 100
        iv = 0.20
        width = 5
        
        # Equidistant OTM spreads should have similar values
        put_strikes = (S - 10, S - 10 - width)  # 90/85 put spread
        call_strikes = (S + 10, S + 10 + width)  # 110/115 call spread
        
        put_value = pricer.price_spread(date, S, put_strikes, expiry, iv)
        call_value = pricer.price_spread(date, S, call_strikes, expiry, iv)
        
        # Values should be relatively close (not exact due to skew in real markets)
        assert abs(put_value - call_value) / put_value < 0.20, \
            f"Symmetric spreads too different: put={put_value}, call={call_value}"


def test_spread_width_relationship():
    """Test that wider spreads have higher maximum value"""
    pricer = SyntheticOptionPricer()
    date = pd.Timestamp('2024-01-15')
    expiry = pd.Timestamp('2024-02-15')
    S = 100
    iv = 0.20
    
    # Compare $1 wide vs $5 wide put spreads
    narrow_spread = pricer.price_spread(date, S, (95, 94), expiry, iv)
    wide_spread = pricer.price_spread(date, S, (95, 90), expiry, iv)
    
    # Wider spread should have more value
    assert wide_spread > narrow_spread, \
        f"Wide spread {wide_spread} should be > narrow spread {narrow_spread}"
    
    # But not more than 5x (due to probability)
    assert wide_spread < narrow_spread * 5.5, \
        "Wide spread value seems too high relative to narrow"


def test_time_decay():
    """Test that option values decay over time"""
    pricer = SyntheticOptionPricer()
    S = 100
    strikes = (95, 90)
    iv = 0.20
    
    # Price spread at different times to expiry
    date1 = pd.Timestamp('2024-01-15')
    date2 = pd.Timestamp('2024-02-01')
    expiry = pd.Timestamp('2024-02-15')
    
    value1 = pricer.price_spread(date1, S, strikes, expiry, iv)
    value2 = pricer.price_spread(date2, S, strikes, expiry, iv)
    
    # Later date (less time) should have less value
    assert value2 < value1, \
        f"Spread value should decay: {value1} -> {value2}"