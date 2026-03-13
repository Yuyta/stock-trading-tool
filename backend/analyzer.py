import numpy as np
import pandas as pd
from typing import Optional
from models import (
    AnalyzeRequest, AnalysisResult, MacroResult,
    FundamentalResult, TechnicalResult, QualitativeResult, RiskInfo,
)
from data_fetcher import fetch_price_history, fetch_macro_data, fetch_fundamentals, is_jp_stock


def analyze(request: AnalyzeRequest) -> AnalysisResult:
    symbol = request.symbol.strip().upper()
    has_jquants = bool(request.jquants_refresh_token)
    has_gemini = bool(request.gemini_api_key)
    jp_stock = is_jp_stock(symbol)

    # --- Decide analysis mode upfront ---
    if request.trade_style == "day":
        analysis_mode = "デイトレモード"
    elif has_gemini and (has_jquants or not jp_stock):
        analysis_mode = "フルモード"
    elif has_gemini or has_jquants:
        analysis_mode = "標準モード"
    else:
        analysis_mode = "基本モード"

    # === Layer 1: Macro Risk Filter ===
    macro = _analyze_macro()
    # Note: Previously returned early here. Now we continue to show scores, 
    # but the macro status will influence the final signal and warnings.

    # === Fetch price history ===
    price_df = fetch_price_history(symbol, request.timeframe)
    if price_df is None or price_df.empty:
        return AnalysisResult(
            symbol=symbol, signal="見送り",
            macro=macro, analysis_mode=analysis_mode,
            error=f"'{symbol}' のデータを取得できませんでした。銘柄コードを確認してください。",
        )

    # === Liquidity check ===
    avg_vol = price_df["Volume"].tail(20).mean() if "Volume" in price_df.columns else None
    avg_close = price_df["Close"].tail(20).mean() if "Close" in price_df.columns else None
    liquidity_ok = None
    if avg_vol is not None and avg_close is not None:
        daily_turnover = avg_vol * avg_close
        if request.trade_style == "day":
            threshold = 500_000_000 if jp_stock else 5_000_000  # Stricter for day trading
        else:
            threshold = 100_000_000 if jp_stock else 1_000_000
        liquidity_ok = daily_turnover >= threshold

    # === Layer 3: Technical (always runs, no API key needed) ===
    technical = _analyze_technical(price_df, request.trade_style)

    fund_data = None

    # === Layer 2: Fundamental ===
    if request.trade_style == "day":
        fundamental = _fundamental_unavailable_day()
    else:
        fund_data = fetch_fundamentals(symbol, request.jquants_refresh_token)
        
        # どのソースからデータが取れたかを詳細に判定
        sources = []
        is_jq = bool(fund_data.get("_jq_success"))
        # 財務メトリクス（PER, PBR, ROE, 成長率）のいずれかがあるか
        has_metrics = any(fund_data.get(k) is not None for k in ["per", "pbr", "roe", "op_income_growth_avg"])
        
        if is_jq:
            sources.append("J-Quants")
        
        if has_metrics:
            if not is_jq:
                sources.append("yfinance")
            elif not has_jquants: # 理論上ここには来ないが念のため
                sources.append("yfinance")

        if not sources:
            if jp_stock and not has_jquants:
                # どのソースからも取れず、J-Quantsも未設定の場合のみ「キーが必要」を表示
                fundamental = _fundamental_unavailable()
            else:
                fundamental = _score_fundamental(fund_data, "不明 / 取得不可")
        else:
            data_source = " + ".join(sources)
            fundamental = _score_fundamental(fund_data, data_source)
            # 日本株でJ-Quantsがない場合、yfinanceでの分析結果に補足を追加
            if jp_stock and not has_jquants:
                fundamental.reasons.append("💡 J-Quantsキーを設定するとより詳細・正確な財務分析が可能になります")

    # === Layer 4: Qualitative (news sentiment) ===
    if fund_data is None:
        fund_data = fetch_fundamentals(symbol, request.jquants_refresh_token if has_jquants else None)

    qualitative = _score_qualitative(fund_data, request.gemini_api_key if has_gemini else None, request.trade_style)

    # === マクロ環境による個別調整（追加） ===
    per = fund_data.get("per") if fund_data else None
    is_growth = per is not None and per > 30
    
    if is_growth:
        if macro.us10y is not None and macro.us10y > 4.5:
            fundamental.sub_total -= 5
            fundamental.reasons.append(f"❌ マクロ影響: 米10年金利({macro.us10y:.2f}%)高止まりによるグロース株減点")
        if macro.nasdaq_below_ma75:
            fundamental.sub_total -= 5
            fundamental.reasons.append("❌ マクロ影響: NASDAQの75日線割れによるグロース環境悪化")
            
    if jp_stock and macro.usdjpy_trend > 2.0:
        fundamental.sub_total += 5
        fundamental.reasons.append(f"✅ マクロ影響: USD/JPY急騰(+{macro.usdjpy_trend:.1f}%)による円安メリット加点")

    # === Total Score & Max Score ===
    total = technical.score + qualitative.score + fundamental.sub_total
    max_score = 40 + qualitative.max_score + fundamental.max_score  # Technical(40) + Qualitative + Fundamental

    # === Normalize signal thresholds to the actual max score ===
    ratio = total / max_score if max_score > 0 else 0
    if ratio >= 0.85:
        signal = "Strong Buy"
    elif ratio >= 0.65:
        signal = "Buy"
    elif ratio >= 0.45:
        signal = "Hold"
    else:
        signal = "Sell / Avoid"

    # マクロ環境に応じた警告ラベルの付与
    if not macro.passed:
        signal = f"回避推奨 ({macro.block_reason})"
    elif macro.vix_mode == "caution":
        signal = signal + " (VIX警戒)"
    elif macro.market_below_ma75 and ratio < 0.85 and request.trade_style != "day":
        signal = signal + " (市場注意)"

    # === Risk Info ===
    current_price = float(price_df["Close"].iloc[-1])
    high_60d = float(price_df["Close"].tail(60).max())
    
    warnings_list = []
    
    # 時価総額チェック
    market_cap = fund_data.get("market_cap") if fund_data else None
    if market_cap:
        if jp_stock and market_cap < 10_000_000_000:
            warnings_list.append("⚠️ 時価総額100億円未満のため、ボラティリティリスクが高めです。")
        elif not jp_stock and market_cap < 100_000_000:
            warnings_list.append("⚠️ 小型株のため、ボラティリティリスクが高めです。")
    
    if request.trade_style == "day":
        risk = RiskInfo(
            liquidity_ok=liquidity_ok,
            avg_daily_volume=float(avg_vol) if avg_vol is not None else None,
            trailing_stop_base=round(float(current_price * 0.98), 2),
            trailing_stop_base_label="損切り目安(−2%)",
            trailing_stop_high=round(float(high_60d * 0.97), 2),
            trailing_stop_high_label="高値から−3%",
            warnings=warnings_list
        )
    else:
        risk = RiskInfo(
            liquidity_ok=liquidity_ok,
            avg_daily_volume=float(avg_vol) if avg_vol is not None else None,
            trailing_stop_base=round(float(current_price * 0.93), 2),
            trailing_stop_base_label="損切り目安(−7%)",
            trailing_stop_high=round(float(high_60d * 0.90), 2),
            trailing_stop_high_label="高値から−10%",
            warnings=warnings_list
        )

    # === Build Chart Data ===
    from models import ChartDataPoint
    chart_data = []
    if price_df is not None and not price_df.empty:
        # 指標の計算 (チャート表示用)
        closes = price_df["Close"]
        ema5_ser = closes.ewm(span=5, adjust=False).mean()
        ema20_ser = closes.ewm(span=20, adjust=False).mean()
        ema75_ser = closes.ewm(span=75, adjust=False).mean()
        sma20 = closes.rolling(window=20).mean()
        std20 = closes.rolling(window=20).std()
        upper_ser = sma20 + (std20 * 2)
        lower_ser = sma20 - (std20 * 2)

        # 結合して tail を取得
        df_all = pd.DataFrame({
            "Close": closes,
            "ema5": ema5_ser,
            "ema20": ema20_ser,
            "ema75": ema75_ser,
            "upper": upper_ser,
            "lower": lower_ser
        })
        
        df_chart = df_all.tail(100)
        for idx, row in df_chart.iterrows():
            if request.timeframe in ["1m", "2m", "5m", "15m", "30m", "60m", "90m", "1h"]:
                time_str = idx.strftime("%m-%d %H:%M")
            else:
                time_str = idx.strftime("%m-%d")
            
            chart_data.append(ChartDataPoint(
                time=time_str, 
                price=round(float(row["Close"]), 2),
                ema5=round(float(row["ema5"]), 2) if not pd.isna(row["ema5"]) else None,
                ema20=round(float(row["ema20"]), 2) if not pd.isna(row["ema20"]) else None,
                ema75=round(float(row["ema75"]), 2) if not pd.isna(row["ema75"]) else None,
                bollinger_upper=round(float(row["upper"]), 2) if not pd.isna(row["upper"]) else None,
                bollinger_lower=round(float(row["lower"]), 2) if not pd.isna(row["lower"]) else None,
            ))

    return AnalysisResult(
        symbol=symbol,
        signal=signal,
        total_score=round(float(total), 1),
        max_score=round(float(max_score), 1),
        analysis_mode=analysis_mode,
        macro=macro,
        fundamental=fundamental,
        technical=technical,
        qualitative=qualitative,
        risk=risk,
        chart_data=chart_data,
    )


def _analyze_macro() -> MacroResult:
    data = fetch_macro_data()
    result = MacroResult()

    vix_s = data.get("vix")
    if vix_s is not None and len(vix_s) > 0:
        vix = float(vix_s.iloc[-1])
        result.vix = round(vix, 2)
        if vix > 40:
            result.vix_mode = "emergency"
            result.passed = False
            result.block_reason = f"VIXパニックモード ({vix:.1f} > 40)"
        elif vix > 30:
            result.vix_mode = "caution"
            result.passed = True  # 表示のみでブロックはしない
            result.block_reason = f"VIX高リスク ({vix:.1f} > 30)"
        elif vix > 25:
            result.vix_mode = "caution"
            result.passed = True
        else:
            result.vix_mode = "normal"
            result.passed = True

    for key, attr in [("wti", "oil_sigma"), ("gold", "gold_sigma")]:
        s = data.get(key)
        if s is not None and len(s) >= 20:
            mean_5d = float(s.tail(5).mean())
            std_20d = float(s.tail(20).std())
            current = float(s.iloc[-1])
            sigma = (current - mean_5d) / std_20d if std_20d > 0 else 0.0
            setattr(result, attr, round(sigma, 2))
            if sigma >= 2.0:
                result.commodity_alert = True

    nk = data.get("nikkei")
    if nk is not None and len(nk) >= 75:
        ma75 = float(nk.rolling(75).mean().iloc[-1])
        result.market_below_ma75 = float(nk.iloc[-1]) < ma75

    # US10Y
    us10y = data.get("us10y")
    if us10y is not None and len(us10y) > 0:
        result.us10y = round(float(us10y.iloc[-1]), 3)

    # USD/JPY
    usdjpy = data.get("usdjpy")
    if usdjpy is not None and len(usdjpy) >= 2:
        curr = float(usdjpy.iloc[-1])
        prev = float(usdjpy.iloc[-2])
        if prev > 0:
            result.usdjpy_trend = round((curr / prev - 1) * 100, 2)

    # NASDAQ
    nq = data.get("nasdaq")
    if nq is not None and len(nq) >= 75:
        nq_ma75 = float(nq.rolling(75).mean().iloc[-1])
        result.nasdaq_below_ma75 = float(nq.iloc[-1]) < nq_ma75

    # Sector Rotation
    # For US stocks: SPY is baseline, XLK, XLF, XLE, XLY are sectors.
    # For JP stocks: TOPIX is baseline, jp_bank, jp_trade, jp_auto, jp_semi are sectors.
    spy = data.get("spy")
    spy_perf = (float(spy.iloc[-1]) / float(spy.iloc[-20]) - 1) if spy is not None and len(spy) >= 20 else 0
    us_sectors = {"XLK": "xlk", "XLF": "xlf", "XLE": "xle", "XLY": "xly"}
    
    topix = data.get("topix")
    topix_perf = (float(topix.iloc[-1]) / float(topix.iloc[-20]) - 1) if topix is not None and len(topix) >= 20 else 0
    jp_sectors = {"銀行": "jp_bank", "商社": "jp_trade", "自動車": "jp_auto", "半導体": "jp_semi"}

    sectors_perf = {}
    # Combine US sectors
    for name, k in us_sectors.items():
        sec = data.get(k)
        if sec is not None and len(sec) >= 20:
            sectors_perf[name] = (float(sec.iloc[-1]) / float(sec.iloc[-20]) - 1) - spy_perf

    # Combine JP sectors
    for name, k in jp_sectors.items():
        sec = data.get(k)
        if sec is not None and len(sec) >= 20:
            sectors_perf[name] = (float(sec.iloc[-1]) / float(sec.iloc[-20]) - 1) - topix_perf
            
    if sectors_perf:
        result.strong_sectors = [k for k, outperf in sectors_perf.items() if outperf > 0.02]
        result.weak_sectors = [k for k, outperf in sectors_perf.items() if outperf < -0.02]

    # Populate warnings for easier consumption
    if not result.passed:
        result.warnings.append(f"緊急: {result.block_reason}")
    elif result.vix_mode == "caution":
        result.warnings.append("VIX指数が高いため、新規建玉の縮小を推奨します。")
    
    if result.market_below_ma75:
        result.warnings.append("主要指数が75日移動平均線を下回っています。")
    if result.commodity_alert:
        result.warnings.append("コモディティ価格（原油・金）の急変が検出されました。")

    return result


def _analyze_technical(price_df: pd.DataFrame, trade_style: str) -> TechnicalResult:
    result = TechnicalResult()
    score = 0.0
    reasons = []

    try:
        closes = price_df["Close"]
        volumes = price_df["Volume"]
        highs = price_df["High"]
        lows = price_df["Low"]

        cur = float(closes.iloc[-1])
        result.current_price = round(cur, 2)

        # EMA Calculation
        ema5 = closes.ewm(span=5, adjust=False).mean()
        ema20 = closes.ewm(span=20, adjust=False).mean()
        ema75 = closes.ewm(span=75, adjust=False).mean()
        
        e5 = float(ema5.iloc[-1])
        e20 = float(ema20.iloc[-1])
        e75 = float(ema75.iloc[-1])
        
        result.ema5 = round(e5, 2)
        result.ema20 = round(e20, 2)
        result.ema75 = round(e75, 2)
        result.above_ema75 = cur > e75

        # Golden Cross check (5 crosses 20)
        if len(ema5) >= 2:
            prev_e5 = float(ema5.iloc[-2])
            prev_e20 = float(ema20.iloc[-2])
            result.golden_cross = (prev_e5 <= prev_e20) and (e5 > e20)

        # =====================================================
        # Relative Strength
        # =====================================================
        if len(closes) >= 20:
            stock_perf = cur / float(closes.iloc[-20]) - 1
            if stock_perf > 0.05:
                score += 6
                reasons.append(f"✅ Relative Strength強 ({stock_perf*100:.1f}%)")
            elif stock_perf > 0:
                score += 3
                reasons.append("⚠️ 市場平均以上の推移")

        # =====================================================
        # Relative Volume (RVOL)
        # =====================================================
        if len(volumes) >= 20:
            avg_vol_20 = float(volumes.tail(20).mean())
            if avg_vol_20 > 0:
                rvol = float(volumes.iloc[-1]) / avg_vol_20
                result.volume_ratio = round(rvol, 2)
                result.volume_surge = rvol >= 2.0

                if rvol >= 2.0:
                    score += 10
                    reasons.append(f"🔥 RVOL {rvol:.1f}（資金流入）")
                elif rvol >= 1.5:
                    score += 6
                    reasons.append(f"✅ 出来高増加 {rvol:.1f}x")

        # =====================================================
        # Trend Score
        # =====================================================
        if e5 > e20 and cur > e75:
            score += 15
            reasons.append("✅ 強い上昇トレンド")
        elif e5 > e20:
            score += 8
            reasons.append("⚠️ 短期上昇")
        elif cur < e75:
            reasons.append("❌ 長期トレンド下落中")

        # =====================================================
        # RSI
        # =====================================================
        delta = closes.diff()
        gain = delta.clip(lower=0).rolling(14).mean()
        loss = (-delta).clip(lower=0).rolling(14).mean()
        rs = gain / (loss + 1e-9)
        rsi_ser = 100 - 100 / (1 + rs)
        rsi = float(rsi_ser.iloc[-1])
        result.rsi = round(float(rsi), 1)

        if 40 <= rsi <= 65:
            score += 10
            reasons.append(f"✅ RSI良好 {rsi:.0f}")
        elif rsi > 70:
            score += 4
            reasons.append("⚠️ RSI過熱")
        elif rsi < 30:
            reasons.append("⚠️ RSI売られすぎ")

        # =====================================================
        # MACD
        # =====================================================
        ema12 = closes.ewm(span=12, adjust=False).mean()
        ema26 = closes.ewm(span=26, adjust=False).mean()
        macd = ema12 - ema26
        signal = macd.ewm(span=9, adjust=False).mean()
        
        result.macd = round(float(macd.iloc[-1]), 2)
        result.macd_signal = round(float(signal.iloc[-1]), 2)
        
        if result.macd > result.macd_signal:
            score += 5
            reasons.append("✅ MACDゴールデンクロス")

        # =====================================================
        # Bollinger Bands (20, 2)
        # =====================================================
        sma20 = closes.rolling(window=20).mean()
        std20 = closes.rolling(window=20).std()
        upper = sma20 + (std20 * 2)
        lower = sma20 - (std20 * 2)
        
        result.bollinger_upper = round(float(upper.iloc[-1]), 2)
        result.bollinger_lower = round(float(lower.iloc[-1]), 2)
        
        if cur > result.bollinger_upper:
            reasons.append("⚠️ ボリンジャーバンド+2σ超え（過熱）")
        elif cur < result.bollinger_lower:
            reasons.append("✅ ボリンジャーバンド-2σ到達（自律反発期待）")

        # =====================================================
        # VWAP (Approximated for daily, or reset for intraday)
        # =====================================================
        # For daily data, we can use a volume-weighted moving average as an approximation
        # For intraday, we should ideally reset daily, but here we'll do 20-period VWMA
        typical_price = (closes + highs + lows) / 3
        vwap = (typical_price * volumes).rolling(window=14).sum() / volumes.rolling(window=14).sum()
        result.vwap = round(float(vwap.iloc[-1]), 2)

    except Exception as e:
        reasons.append(f"テクニカルエラー {str(e)}")

    result.score = min(40.0, max(0.0, score))
    result.reasons = reasons
    return result

def _fundamental_unavailable() -> FundamentalResult:
    """
    Called when JP stock and no J-Quants key.
    Returns a zero-score result with max_score=0 so it doesn't skew the total.
    """
    result = FundamentalResult()
    result.growth_score = 0
    result.valuation_score = 0
    result.sub_total = 0
    result.max_score = 0  # excluded from ratio calculation
    result.data_source = "未設定（J-Quantsキー必要）"
    result.reasons = [
        "⚪ 日本株のファンダメンタル分析にはJ-Quantsリフレッシュトークンが必要です",
        "　　設定画面からJ-Quantsキーを入力すると詳細な財務分析が可能になります",
    ]
    return result

def _fundamental_unavailable_day() -> FundamentalResult:
    result = FundamentalResult()
    result.growth_score = 0
    result.valuation_score = 0
    result.sub_total = 0
    result.max_score = 0  # excluded from ratio calculation
    result.data_source = "非対象（デイトレモード）"
    result.reasons = [
        "⚪ デイトレードモードのため、ファンダメンタル（長期目線）分析は除外されています",
    ]
    return result


def _score_fundamental(fund_data: dict, data_source: str) -> FundamentalResult:
    result = FundamentalResult()
    result.data_source = data_source
    reasons = []
    growth_score = 0.0
    val_score = 0.0

    # --- Growth (0–30 pts) ---
    growth = fund_data.get("op_income_growth_avg")
    result.op_income_growth_avg = round(growth, 1) if growth is not None else None
    if growth is not None:
        if growth >= 15:
            growth_score = 30
            reasons.append(f"✅ 営業利益成長率 {growth:.1f}%（優秀）")
        elif growth >= 10:
            growth_score = 25
            reasons.append(f"✅ 営業利益成長率 {growth:.1f}%（良好）")
        elif growth >= 5:
            growth_score = 15
            reasons.append(f"⚠️ 営業利益成長率 {growth:.1f}%（普通）")
        elif growth >= 0:
            growth_score = 5
            reasons.append(f"⚠️ 営業利益成長率 {growth:.1f}%（低成長）")
        else:
            reasons.append(f"❌ 営業利益成長率 {growth:.1f}%（減益）")
    else:
        # No growth data from this source → 0 pts (not estimated)
        growth_score = 0
        reasons.append("⚠️ 営業利益成長データなし（スコア対象外）")

    # --- Valuation (0–20 pts): PER 7 + PBR 6 + ROE 7 ---
    per = fund_data.get("per")
    pbr = fund_data.get("pbr")
    roe = fund_data.get("roe")
    result.per = round(float(per), 1) if per else None
    result.pbr = round(float(pbr), 2) if pbr else None
    result.roe = round(float(roe), 1) if roe else None

    data_missing = 0
    if per:
        if per <= 12:
            val_score += 7; reasons.append(f"✅ PER {per:.1f}倍（割安）")
        elif per <= 15:
            val_score += 5; reasons.append(f"✅ PER {per:.1f}倍（適正）")
        elif per <= 20:
            val_score += 2; reasons.append(f"⚠️ PER {per:.1f}倍（やや高め）")
        else:
            reasons.append(f"❌ PER {per:.1f}倍（割高）")
    else:
        data_missing += 7; reasons.append("⚪ PERデータなし（スコア対象外）")

    if pbr:
        if pbr < 1.0 and is_jp_stock:
            val_score += 10; reasons.append(f"✅ PBR {pbr:.2f}倍（東証改革テーマ・PBR1割れ）")
        elif pbr <= 1.2:
            val_score += 6; reasons.append(f"✅ PBR {pbr:.2f}倍（割安）")
        elif pbr <= 2.0:
            val_score += 3; reasons.append(f"⚠️ PBR {pbr:.2f}倍（普通）")
        else:
            reasons.append(f"❌ PBR {pbr:.2f}倍（割高）")
    else:
        data_missing += 6; reasons.append("⚪ PBRデータなし（スコア対象外）")

    if roe:
        if roe > 15:
            val_score += 10; reasons.append(f"✅ ROE {roe:.1f}%（超高収益）")
        elif roe >= 10:
            val_score += 7; reasons.append(f"✅ ROE {roe:.1f}%（高収益）")
        elif roe >= 8:
            val_score += 5; reasons.append(f"✅ ROE {roe:.1f}%（良好）")
        elif roe >= 5:
            val_score += 2; reasons.append(f"⚠️ ROE {roe:.1f}%（普通）")
        else:
            reasons.append(f"❌ ROE {roe:.1f}%（低収益）")
    else:
        data_missing += 7; reasons.append("⚪ ROEデータなし（スコア対象外）")

    # Max score = 50 minus the portions where data was missing
    result.max_score = 50 - data_missing
    result.growth_score = round(growth_score, 1)
    result.valuation_score = round(val_score, 1)
    result.sub_total = round(growth_score + val_score, 1)
    result.reasons = reasons
    return result


def _score_qualitative(fund_data: dict, gemini_api_key: Optional[str], trade_style: str) -> QualitativeResult:
    result = QualitativeResult()
    headlines = [h for h in fund_data.get("news_headlines", []) if h]

    news_count_24h = fund_data.get("news_count_24h", 0)

    if not headlines:
        result.score = 0.0
        result.max_score = 0  # no data → excluded from total
        result.data_source = "なし"
        result.reasons.append("⚪ ニュースデータなし（スコア対象外）")
        return result
        
    def apply_news_count_modifier(res: QualitativeResult):
        if news_count_24h >= 4:
            res.score = min(res.max_score, res.score + 2.0)
            res.reasons.append(f"✅ 24時間以内のニュース急増({news_count_24h}件・短期トレンド発生)")
        elif news_count_24h >= 2:
            res.score = min(res.max_score, res.score + 1.0)
            res.reasons.append(f"✅ 24時間以内のアクティブな情報発信({news_count_24h}件)")

    # ── WITHOUT Gemini API: keyword-based, max 7 pts ──
    if not gemini_api_key:
        result.data_source = "キーワード"
        result.max_score = 7  # cap because keyword analysis is less reliable

        neg_kw = ["不祥事", "下方修正", "赤字", "倒産", "scandal", "fraud", "bankruptcy",
                  "war", "downgrade", "warning", "recall", "investigation"]
        pos_kw = ["増益", "上方修正", "最高益", "好決算", "growth", "upgrade",
                  "record", "beat", "strong", "dividend", "buyback"]

        hits_neg = [kw for kw in neg_kw if any(kw.lower() in h.lower() for h in headlines)]
        hits_pos = [kw for kw in pos_kw if any(kw.lower() in h.lower() for h in headlines)]
        
        neg = sum(1 for h in headlines for kw in neg_kw if kw.lower() in h.lower())
        pos = sum(1 for h in headlines for kw in pos_kw if kw.lower() in h.lower())

        if neg > pos:
            result.score = max(0.0, 5.0 - neg * 1.5)
            result.sentiment = "negative"
            kw_str = ", ".join(hits_neg)
            result.reasons.append(f"⚠️ ネガティブキーワード検知: {kw_str}（{neg}件）")
        elif pos > 0:
            result.score = min(7.0, 5.0 + pos * 0.8)
            result.sentiment = "positive"
            kw_str = ", ".join(hits_pos)
            result.reasons.append(f"✅ ポジティブキーワード検知: {kw_str}（{pos}件）")
        else:
            result.score = 4.0
            result.sentiment = "neutral"
            result.reasons.append("➖ 中立的なニュース")

        result.reasons.append("　　Gemini APIキーを設定するとAI詳細分析（満点10点）が利用可能")
        result.news_analyzed = True
        apply_news_count_modifier(result)
        return result

    # ── WITH Gemini API: AI-powered, max 10 pts ──
    result.data_source = "Gemini AI"
    result.max_score = 10
    
    # Pre-define keywords for fallback in case of API error
    neg_kw = ["不祥事", "下方修正", "赤字", "倒産", "scandal", "fraud", "bankruptcy",
              "war", "downgrade", "warning", "recall", "investigation"]
    pos_kw = ["増益", "上方修正", "最高益", "好決算", "growth", "upgrade",
              "record", "beat", "strong", "dividend", "buyback"]
    
    def run_keyword_fallback(error_msg: str):
        result.data_source = "キーワード(エラー切替)"
        result.max_score = 7
        hits_neg = [kw for kw in neg_kw if any(kw.lower() in h.lower() for h in headlines)]
        hits_pos = [kw for kw in pos_kw if any(kw.lower() in h.lower() for h in headlines)]
        
        neg = sum(1 for h in headlines for kw in neg_kw if kw.lower() in h.lower())
        pos = sum(1 for h in headlines for kw in pos_kw if kw.lower() in h.lower())
        if neg > pos:
            result.score = max(0.0, 5.0 - neg * 1.5)
            result.sentiment = "negative"
            kw_str = ", ".join(hits_neg)
            result.reasons.append(f"⚠️ API制限のためキーワード判定: {kw_str}（{neg}件）")
        elif pos > 0:
            result.score = min(7.0, 5.0 + pos * 0.8)
            result.sentiment = "positive"
            kw_str = ", ".join(hits_pos)
            result.reasons.append(f"✅ API制限のためキーワード判定: {kw_str}（{pos}件）")
        else:
            result.score = 4.0
            result.sentiment = "neutral"
            result.reasons.append("➖ API制限のためキーワード判定（中立）")
        result.reasons.append(f"エラー詳細: {error_msg[:40]}...")

    try:
        import google.generativeai as genai
        import json
        import re as re_mod

        genai.configure(api_key=gemini_api_key)
        text_headlines = "\n".join(f"- {h}" for h in headlines)
        
        if trade_style == "day":
            prompt = f"""以下の株式ニュースヘッドラインを分析し、**「今日～明日の短期的な値動き・ボラティリティへの影響（デイトレード視点）」**を基準に感情スコアを0〜10の整数で返してください。
0=急落リスク（不祥事、致命的な発表など）、5=中立（今日は材料視されない無風）、10=急騰確実のアクティブ材料（サプライズ決算、テーマ株の本命発表など）

ヘッドライン:
{text_headlines}

以下のJSON形式のみで回答してください:
{{"score": <0-10の整数>, "sentiment": "<positive/neutral/negative>", "reason": "<50字以内の日本語で分析根拠>"}}"""
        else:
            prompt = f"""以下の株式ニュースヘッドラインを分析し、中長期的な投資家視点での感情スコアを0〜10の整数で返してください。
0=非常にネガティブ（不祥事・倒産・戦争等）、5=中立、10=非常にポジティブ（増益・最高益等）

ヘッドライン:
{text_headlines}

以下のJSON形式のみで回答してください:
{{"score": <0-10の整数>, "sentiment": "<positive/neutral/negative>", "reason": "<50字以内の日本語で分析根拠>"}}"""

        # Using gemini-3.1-flash-lite-preview for maximum compatibility and stability
        model = genai.GenerativeModel("gemini-3.1-flash-lite-preview")
        resp = model.generate_content(prompt)
        m = re_mod.search(r'\{.*\}', resp.text, re_mod.DOTALL)
        if m:
            parsed = json.loads(m.group())
            result.score = float(max(0, min(10, parsed.get("score", 5))))
            result.sentiment = parsed.get("sentiment", "neutral")
            result.reasons.append(f"✅ Gemini AI解析: {parsed.get('reason', '')}")
            result.news_analyzed = True
            apply_news_count_modifier(result)
        else:
            run_keyword_fallback("JSON解析失敗")
            apply_news_count_modifier(result)
    except Exception as e:
        run_keyword_fallback(str(e))
        apply_news_count_modifier(result)

    return result
