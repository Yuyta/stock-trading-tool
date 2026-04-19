import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from main import app
from models import AnalysisResult, MacroResult

client = TestClient(app)

def test_health_check():
    """ヘルスチェックエンドポイントのテスト"""
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

def test_analyze_endpoint_success():
    """分析エンドポイントの正常系テスト（ロジックはモック）"""
    mock_result = {
        "symbol": "AAPL",
        "signal": "Buy",
        "trade_style": "swing",
        "total_score": 65.0,
        "max_score": 100.0,
        "analysis_mode": "標準モード",
        "macro": {"vix": 20.0, "passed": True},
        "chart_data": [],
        "reliability_rating": "normal"
    }
    
    with patch("main.analyze", return_value=mock_result):
        response = client.post(
            "/api/analyze",
            json={"symbol": "AAPL", "trade_style": "swing", "timeframe": "1d"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["symbol"] == "AAPL"
        assert data["signal"] == "Buy"

def test_search_endpoint_success():
    """銘柄検索エンドポイントの正常系テスト"""
    mock_search_data = {
        "results": [
            {"symbol": "7203.T", "name": "Toyota Motor", "exchange": "TYO", "type": "EQUITY"}
        ]
    }
    
    with patch("yfinance.Search") as mock_search:
        # yfinance.Search().quotes をモック
        mock_instance = mock_search.return_value
        mock_instance.quotes = [
            {"symbol": "7203.T", "shortname": "Toyota Motor", "exchange": "TYO", "quoteType": "EQUITY"}
        ]
        
        response = client.get("/api/search?q=7203")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["results"]) >= 1
        assert data["results"][0]["symbol"] == "7203.T"
