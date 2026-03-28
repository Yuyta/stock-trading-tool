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
    ema5?: number;
    ema20?: number;
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
    ema5?: number;
    ema20?: number;
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
    risk?: RiskInfo;
    chart_data?: ChartDataPoint[];
    error?: string;
}

export interface AppSettings {
    jquantsRefreshToken: string;
    geminiApiKey: string;
}
