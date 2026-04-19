import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

@pytest.fixture
def mock_price_df():
    """正常な価格履歴データのモック"""
    dates = [datetime.now() - timedelta(days=i) for i in range(250, 0, -1)]
    # 基本的に上昇トレンドのデータ
    base_price = 1000
    prices = [base_price + (i * 2) + np.random.normal(0, 5) for i in range(250)]
    volumes = [10000 + np.random.randint(-1000, 1000) for _ in range(250)]
    
    df = pd.DataFrame({
        "Open": prices,
        "High": [p + 5 for p in prices],
        "Low": [p - 5 for p in prices],
        "Close": prices,
        "Volume": volumes
    }, index=dates)
    return df

@pytest.fixture
def mock_fundamental_data():
    """正常なファンダメンタルデータのモック"""
    return {
        "name": "Dummy Stock",
        "per": 15.0,
        "pbr": 1.2,
        "roe": 10.0,
        "dividend_yield": 3.5,
        "payout_ratio": 30.0,
        "op_income_growth_avg": 5.0,
        "market_cap": 500_000_000_000, # 5000億円
        "sector": "Technology",
        "news_headlines": ["Positive news 1", "Market expansion"],
        "next_earnings_date": (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
    }

@pytest.fixture
def mock_macro_data():
    """正常なマクロデータのモック"""
    from models import MacroResult
    return MacroResult(
        vix=18.5,
        vix_mode="normal",
        passed=True,
        market_below_ma75=False,
        us10y=4.2,
        usdjpy_trend=0.5,
        nasdaq_below_ma75=False,
        strong_sectors=["Technology"],
        weak_sectors=["Energy"]
    )
