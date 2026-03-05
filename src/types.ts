// Mirror of backend Pydantic models

export interface AnalyzeRequest {
    symbol: string;
    timeframe: string;
    jquants_refresh_token?: string;
    gemini_api_key?: string;
}

export interface MacroResult {
    vix?: number;
    vix_mode: string;
    oil_sigma?: number;
    gold_sigma?: number;
    commodity_alert: boolean;
    market_below_ma75?: boolean;
    passed: boolean;
    block_reason?: string;
}

export interface FundamentalResult {
    growth_score: number;
    valuation_score: number;
    sub_total: number;
    op_income_growth_avg?: number;
    per?: number;
    pbr?: number;
    roe?: number;
    reasons: string[];
}

export interface TechnicalResult {
    score: number;
    ema5?: number;
    ema20?: number;
    ema75?: number;
    current_price?: number;
    golden_cross: boolean;
    above_ema75: boolean;
    rsi?: number;
    volume_surge: boolean;
    volume_ratio?: number;
    reasons: string[];
}

export interface QualitativeResult {
    score: number;
    sentiment: string;
    news_analyzed: boolean;
    reasons: string[];
}

export interface RiskInfo {
    liquidity_ok?: boolean;
    avg_daily_volume?: number;
    trailing_stop_7pct?: number;
    trailing_stop_from_high_10pct?: number;
}

export interface AnalysisResult {
    symbol: string;
    signal: string;
    total_score?: number;
    macro: MacroResult;
    fundamental?: FundamentalResult;
    technical?: TechnicalResult;
    qualitative?: QualitativeResult;
    risk?: RiskInfo;
    error?: string;
}

export interface AppSettings {
    jquantsRefreshToken: string;
    geminiApiKey: string;
}
