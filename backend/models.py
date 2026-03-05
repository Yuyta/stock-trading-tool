from pydantic import BaseModel
from typing import Optional, List


class AnalyzeRequest(BaseModel):
    symbol: str
    timeframe: str = "1d"
    jquants_refresh_token: Optional[str] = None
    gemini_api_key: Optional[str] = None


class MacroResult(BaseModel):
    vix: Optional[float] = None
    vix_mode: str = "unknown"  # normal, caution, emergency
    oil_sigma: Optional[float] = None
    gold_sigma: Optional[float] = None
    commodity_alert: bool = False
    market_below_ma75: Optional[bool] = None
    passed: bool = True
    block_reason: Optional[str] = None


class FundamentalResult(BaseModel):
    growth_score: float = 0
    valuation_score: float = 0
    sub_total: float = 0
    op_income_growth_avg: Optional[float] = None
    per: Optional[float] = None
    pbr: Optional[float] = None
    roe: Optional[float] = None
    reasons: List[str] = []


class TechnicalResult(BaseModel):
    score: float = 0
    ema5: Optional[float] = None
    ema20: Optional[float] = None
    ema75: Optional[float] = None
    current_price: Optional[float] = None
    golden_cross: bool = False
    above_ema75: bool = False
    rsi: Optional[float] = None
    volume_surge: bool = False
    volume_ratio: Optional[float] = None
    reasons: List[str] = []


class QualitativeResult(BaseModel):
    score: float = 0
    sentiment: str = "neutral"
    news_analyzed: bool = False
    reasons: List[str] = []


class RiskInfo(BaseModel):
    liquidity_ok: Optional[bool] = None
    avg_daily_volume: Optional[float] = None
    trailing_stop_7pct: Optional[float] = None
    trailing_stop_from_high_10pct: Optional[float] = None


class AnalysisResult(BaseModel):
    symbol: str
    signal: str
    total_score: Optional[float] = None
    macro: MacroResult
    fundamental: Optional[FundamentalResult] = None
    technical: Optional[TechnicalResult] = None
    qualitative: Optional[QualitativeResult] = None
    risk: Optional[RiskInfo] = None
    error: Optional[str] = None
