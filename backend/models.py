from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class UserBase(BaseModel):
    username: str


class UserCreate(UserBase):
    password: str


class UserLogin(BaseModel):
    username: str
    password: str


class UserOut(UserBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: Optional[str] = None


class AnalyzeRequest(BaseModel):
    symbol: str
    timeframe: str = "1d"
    trade_style: str = "swing"  # "swing" (中長期) | "day" (デイトレ) | "long_hold" (長期保有・配当)
    jquants_refresh_token: Optional[str] = None
    gemini_api_key: Optional[str] = None
    is_jp_stock: bool = False

class ChartDataPoint(BaseModel):
    time: str
    price: float
    # 可視化用指標 (Overlay)
    ema5: Optional[float] = None
    ema20: Optional[float] = None
    ema75: Optional[float] = None
    ema200: Optional[float] = None
    bollinger_upper: Optional[float] = None
    bollinger_lower: Optional[float] = None


class MacroResult(BaseModel):
    vix: Optional[float] = None
    vix_mode: str = "unknown"  # normal, caution, emergency
    oil_sigma: Optional[float] = None
    gold_sigma: Optional[float] = None
    commodity_alert: bool = False
    market_below_ma75: Optional[bool] = None
    us10y: Optional[float] = None
    usdjpy_trend: float = 0
    nasdaq_below_ma75: Optional[bool] = None
    strong_sectors: List[str] = []
    weak_sectors: List[str] = []
    passed: bool = True
    block_reason: Optional[str] = None
    warnings: List[str] = []


class FundamentalResult(BaseModel):
    growth_score: float = 0
    valuation_score: float = 0
    sub_total: float = 0
    max_score: float = 50  # adjusts by data source
    op_income_growth_avg: Optional[float] = None
    per: Optional[float] = None
    pbr: Optional[float] = None
    roe: Optional[float] = None
    data_source: str = "yfinance"  # "J-Quants" | "yfinance" | "取得不可"
    reasons: List[str] = []


class TechnicalResult(BaseModel):
    score: float = 0
    ema5: Optional[float] = None
    ema20: Optional[float] = None
    ema75: Optional[float] = None
    ema200: Optional[float] = None
    current_price: Optional[float] = None
    golden_cross: bool = False
    above_ema75: bool = False
    rsi: Optional[float] = None
    bollinger_upper: Optional[float] = None
    bollinger_lower: Optional[float] = None
    macd: Optional[float] = None
    macd_signal: Optional[float] = None
    vwap: Optional[float] = None
    volume_surge: bool = False
    volume_ratio: Optional[float] = None
    reasons: List[str] = []


class QualitativeResult(BaseModel):
    score: float = 0
    max_score: float = 20  # 10-40 depending on style and Gemini
    sentiment: str = "neutral"
    news_analyzed: bool = False
    data_source: str = "キーワード"  # "Gemini AI" | "キーワード" | "なし"
    reasons: List[str] = []


class IncomeResult(BaseModel):
    score: float = 0
    max_score: float = 30
    dividend_yield: Optional[float] = None      # 配当利回り (%)
    five_year_avg_yield: Optional[float] = None # 5年平均配当利回り (%)
    payout_ratio: Optional[float] = None        # 配当性向 (%)
    graham_number: Optional[float] = None       # グレアム指数 (PER × PBR)
    data_source: str = "yfinance"
    reasons: List[str] = []


class RiskInfo(BaseModel):
    liquidity_ok: Optional[bool] = None
    avg_daily_volume: Optional[float] = None
    trailing_stop_base: Optional[float] = None
    trailing_stop_base_label: str = "損切り目安(−7%)"
    trailing_stop_high: Optional[float] = None
    trailing_stop_high_label: str = "高値から−10%"
    warnings: List[str] = []


class AccumulationResult(BaseModel):
    score: float = 0              # 先回りスコア (0〜40, クリップ済み)
    max_score: float = 40
    confidence: Optional[float] = None  # 確信度 (%) = 発火条件数 / 有効条件数
    signal_label: Optional[str] = None  # モード別閾値に基づくラベル
    stopped: bool = False               # ストッパー発動でスコア無効化されたか
    
    # 個別要素のスコア（各要素のウェイト適用後の値）
    divergence_score: float = 0
    sector_gap_score: float = 0
    volatility_squeeze_score: float = 0
    volume_trend_score: float = 0
    early_trend_score: float = 0
    value_growth_score: float = 0
    
    # ボーナス
    combo_bonus: float = 0
    
    # 発火条件一覧（要素単位: "ダイバージェンス", "ボラ収縮" 等）
    triggered_conditions: List[str] = []
    # ストッパーで除外された理由
    stoppers: List[str] = []
    reasons: List[str] = []


class AnalysisResult(BaseModel):
    symbol: str
    symbol_name: Optional[str] = None
    signal: str
    trade_style: str
    total_score: Optional[float] = None
    max_score: float = 100  # actual max based on available APIs
    analysis_mode: str = "基本モード"  # "フルモード" | "標準モード" | "基本モード"
    macro: MacroResult
    fundamental: Optional[FundamentalResult] = None
    technical: Optional[TechnicalResult] = None
    qualitative: Optional[QualitativeResult] = None
    income: Optional[IncomeResult] = None
    accumulation: Optional[AccumulationResult] = None  # Layer 6
    risk: Optional[RiskInfo] = None
    chart_data: List[ChartDataPoint] = []
    error: Optional[str] = None


class SearchResult(BaseModel):
    symbol: str
    name: Optional[str] = None
    exchange: Optional[str] = None
    type: Optional[str] = None

class SearchResponse(BaseModel):
    results: List[SearchResult]

class HistoryCreate(BaseModel):
    symbol: str
    symbol_name: Optional[str] = None
    trade_style: str
    signal: str
    total_score: Optional[float] = None
    max_score: float
    analysis_mode: str
    result_json: str  # JSON string of AnalysisResult


class HistoryOut(BaseModel):
    id: int
    user_id: int
    symbol: str
    symbol_name: Optional[str] = None
    trade_style: str
    signal: str
    total_score: Optional[float] = None
    max_score: float
    analysis_mode: str
    result_json: str
    created_at: datetime

    class Config:
        from_attributes = True
