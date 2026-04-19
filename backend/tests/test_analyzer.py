import pytest
from unittest.mock import patch, MagicMock
from analyzer import analyze
from models import AnalyzeRequest

def test_analyze_swing_success(mock_price_df, mock_fundamental_data, mock_macro_data):
    """スイングトレードモードの正常系テスト"""
    request = AnalyzeRequest(
        symbol="AAPL",
        trade_style="swing",
        timeframe="1d"
    )
    
    with patch("analyzer.fetch_price_history", return_value=mock_price_df), \
         patch("analyzer._analyze_macro", return_value=mock_macro_data), \
         patch("analyzer.fetch_fundamentals", return_value=mock_fundamental_data), \
         patch("analyzer.is_jp_stock", return_value=False):
        
        result = analyze(request)
        
        assert result.symbol == "AAPL"
        assert result.trade_style == "swing"
        assert result.signal in ["Strong Buy", "Buy", "Hold", "Sell / Avoid", "Watch"]
        assert result.total_score >= 0
        assert len(result.chart_data) > 0
        assert result.technical is not None
        assert result.fundamental is not None

def test_analyze_day_success(mock_price_df, mock_macro_data):
    """デイトレモードの正常系テスト"""
    request = AnalyzeRequest(
        symbol="7203",
        trade_style="day",
        timeframe="5m"
    )
    
    # デイトレではファンダメンタル指標が限定的になる
    mock_fund = {"name": "Toyota", "market_cap": 30_000_000_000_000}
    
    with patch("analyzer.fetch_price_history", return_value=mock_price_df), \
         patch("analyzer._analyze_macro", return_value=mock_macro_data), \
         patch("analyzer.fetch_fundamentals", return_value=mock_fund), \
         patch("analyzer.is_jp_stock", return_value=True):
        
        result = analyze(request)
        
        assert result.trade_style == "day"
        assert result.analysis_mode == "デイトレモード"
        assert result.fundamental.sub_total == 0 # デイトレはファンダ加点なし

def test_analyze_invalid_symbol():
    """無効な銘柄コードの場合の異常系テスト"""
    request = AnalyzeRequest(symbol="INVALID", trade_style="swing")
    
    with patch("analyzer.fetch_price_history", return_value=None):
        result = analyze(request)
        
        assert "のデータを取得できませんでした" in result.error
        assert result.signal == "見送り"

def test_analyze_vix_emergency(mock_price_df, mock_fundamental_data, mock_macro_data):
    """VIX緊急事態（マクロNG）の場合のテスト"""
    request = AnalyzeRequest(symbol="AAPL", trade_style="swing")
    
    # マクロを緊急事態に設定
    mock_macro_data.vix = 45.0
    mock_macro_data.vix_mode = "emergency"
    mock_macro_data.passed = False
    
    with patch("analyzer.fetch_price_history", return_value=mock_price_df), \
         patch("analyzer._analyze_macro", return_value=mock_macro_data), \
         patch("analyzer.fetch_fundamentals", return_value=mock_fundamental_data):
        
        result = analyze(request)
        # マクロNGでもスコアは計算されるが、シグナルに警告が出る、またはストッパーが発動する
        assert result.macro.vix_mode == "emergency"
        assert result.macro.passed is False
