// Mirror of backend Pydantic models

export interface AnalyzeRequest {
    symbol: string;
    timeframe: string;
    trade_style?: string;
    jquants_refresh_token?: string;
    gemini_api_key?: string;
}

export interface ChartDataPoint {
    time: string;
    price: number;
    ema9?: number;
    ema20?: number;
    ema50?: number;
    ema75?: number;
    ema200?: number;
    bollinger_upper?: number;
    bollinger_lower?: number;
}

export interface MacroResult {
    vix?: number;
    vix_mode: string;
    oil_sigma?: number;
    gold_sigma?: number;
    commodity_alert: boolean;
    market_below_ma75?: boolean;
    us10y?: number;
    usdjpy_trend: number;
    nasdaq_below_ma75?: boolean;
    strong_sectors: string[];
    weak_sectors: string[];
    passed: boolean;
    block_reason?: string;
    warnings: string[];
}

export interface FundamentalResult {
    growth_score: number;
    valuation_score: number;
    sub_total: number;
    max_score: number;       // Dynamically set (0 if no API key for JP stocks)
    op_income_growth_avg?: number;
    per?: number;
    pbr?: number;
    roe?: number;
    data_source: string;     // "J-Quants" | "yfinance" | "未設定（J-Quantsキー必要）"
    reasons: string[];
}

export interface TechnicalResult {
    score: number;
    ema9?: number;
    ema20?: number;
    ema50?: number;
    ema75?: number;
    ema200?: number;
    current_price?: number;
    golden_cross: boolean;
    above_ema75: boolean;
    rsi?: number;
    bollinger_upper?: number;
    bollinger_lower?: number;
    macd?: number;
    macd_signal?: number;
    vwap?: number;
    volume_surge: boolean;
    volume_ratio?: number;
    reasons: string[];
}

export interface QualitativeResult {
    score: number;
    max_score: number;       // 10 with Gemini, 7 without, 0 if no news
    sentiment: string;
    news_analyzed: boolean;
    data_source: string;     // "Gemini AI" | "キーワード" | "なし"
    reasons: string[];
}

export interface IncomeResult {
    score: number;
    max_score: number;
    dividend_yield?: number;      // 配当利回り (%)
    five_year_avg_yield?: number; // 5年平均配当利回り (%)
    payout_ratio?: number;        // 配当性向 (%)
    graham_number?: number;       // グレアム指数 (PER × PBR)
    data_source: string;
    reasons: string[];
}

export interface AccumulationResult {
    score: number;
    max_score: number;
    confidence?: number;
    signal_label?: string;
    stopped: boolean;
    divergence_score: number;
    sector_gap_score: number;
    volatility_squeeze_score: number;
    volume_trend_score: number;
    early_trend_score: number;
    value_growth_score: number;
    combo_bonus: number;
    triggered_conditions: string[];
    stoppers: string[];
    reasons: string[];
    is_reliable: boolean;
    has_funda: boolean;
    has_supply: boolean;
    score_momentum: number;
}

export interface RiskInfo {
    liquidity_ok?: boolean;
    avg_daily_volume?: number;
    trailing_stop_base?: number;
    trailing_stop_base_label: string;
    trailing_stop_high?: number;
    trailing_stop_high_label: string;
    warnings: string[];
}

export interface AnalysisResult {
    symbol: string;
    symbol_name?: string;
    signal: string;
    trade_style: string;
    total_score?: number;
    max_score: number;         // Sum of max scores of active layers
    analysis_mode: string;     // "フルモード" | "標準モード" | "基本モード"
    macro: MacroResult;
    fundamental?: FundamentalResult;
    technical?: TechnicalResult;
    qualitative?: QualitativeResult;
    income?: IncomeResult;
    accumulation?: AccumulationResult;
    risk?: RiskInfo;
    chart_data?: ChartDataPoint[];
    error?: string;
    l3_l6_divergence: boolean;
    is_near_earnings: boolean;
    sector_flow_match?: boolean;
    reliability_rating: string;
    prev_signal?: string;
}

export interface AppSettings {
    jquantsRefreshToken: string;
    geminiApiKey: string;
}

export interface User {
    id: string;
    username: string;
    created_at: string;
}

export interface AuthState {
    user: User | null;
    token: string | null;
    isLoading: boolean;
}

export interface AnalysisHistory {
    id: string;
    user_id: string;
    symbol: string;
    symbol_name?: string;
    trade_style: string;
    signal: string;
    total_score?: number;
    max_score: number;
    analysis_mode: string;
    result_json: string;
    created_at: string;
}

export interface SearchResult {
    symbol: string;
    name: string;
    exchange: string;
    type: string;
}
