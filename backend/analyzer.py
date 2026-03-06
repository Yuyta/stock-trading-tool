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
    if not macro.passed:
        return AnalysisResult(
            symbol=symbol, signal="見送り",
            macro=macro, analysis_mode=analysis_mode,
        )

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
        threshold = 100_000_000 if jp_stock else 1_000_000
        liquidity_ok = daily_turnover >= threshold

    # === Layer 3: Technical (always runs, no API key needed) ===
    technical = _analyze_technical(price_df)

    fund_data = None

    # === Layer 2: Fundamental ===
    if request.trade_style == "day":
        fundamental = _fundamental_unavailable_day()
    elif jp_stock and not has_jquants:
        # No J-Quants key for JP stock → skip API-based fundamental scoring
        fundamental = _fundamental_unavailable()
    else:
        fund_data = fetch_fundamentals(symbol, request.jquants_refresh_token)
        data_source = "J-Quants" if (jp_stock and has_jquants) else "yfinance"
        fundamental = _score_fundamental(fund_data, data_source)

    # === Layer 4: Qualitative (news sentiment) ===
    if fund_data is None:
        fund_data = fetch_fundamentals(symbol, request.jquants_refresh_token if has_jquants else None)

    qualitative = _score_qualitative(fund_data, request.gemini_api_key if has_gemini else None)

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

    if macro.market_below_ma75 and ratio < 0.85:
        signal = signal + " (市場注意)"

    # === Risk Info ===
    current_price = float(price_df["Close"].iloc[-1])
    high_60d = float(price_df["Close"].tail(60).max())
    risk = RiskInfo(
        liquidity_ok=liquidity_ok,
        avg_daily_volume=float(avg_vol) if avg_vol is not None else None,
        trailing_stop_7pct=round(current_price * 0.93, 2),
        trailing_stop_from_high_10pct=round(high_60d * 0.90, 2),
    )

    # === Build Chart Data ===
    from models import ChartDataPoint
    chart_data = []
    if price_df is not None and not price_df.empty:
        # Limit to max 100 points for frontend rendering
        df_chart = price_df.tail(100)
        for idx, row in df_chart.iterrows():
            if request.timeframe in ["1m", "2m", "5m", "15m", "30m", "60m", "90m", "1h"]:
                time_str = idx.strftime("%m-%d %H:%M")
            else:
                time_str = idx.strftime("%m-%d")
            chart_data.append(ChartDataPoint(time=time_str, price=round(float(row["Close"]), 2)))

    return AnalysisResult(
        symbol=symbol,
        signal=signal,
        total_score=round(total, 1),
        max_score=round(max_score, 1),
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
        if vix > 30:
            result.vix_mode = "emergency"
            result.passed = False
            result.block_reason = f"VIX緊急モード ({vix:.1f} > 30): 新規買い禁止"
        elif vix > 25:
            result.vix_mode = "caution"
        else:
            result.vix_mode = "normal"

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

    return result


def _analyze_technical(price_df: pd.DataFrame) -> TechnicalResult:
    result = TechnicalResult()
    score = 0.0
    reasons = []
    try:
        closes = price_df["Close"]
        volumes = price_df["Volume"] if "Volume" in price_df.columns else None

        ema5 = closes.ewm(span=5, adjust=False).mean()
        ema20 = closes.ewm(span=20, adjust=False).mean()
        ema75 = closes.ewm(span=75, adjust=False).mean()

        cur = float(closes.iloc[-1])
        e5 = float(ema5.iloc[-1])
        e20 = float(ema20.iloc[-1])
        e75 = float(ema75.iloc[-1])

        result.current_price = round(cur, 2)
        result.ema5 = round(e5, 2)
        result.ema20 = round(e20, 2)
        result.ema75 = round(e75, 2)

        gc = e5 > e20
        above = cur > e75
        result.golden_cross = gc
        result.above_ema75 = above

        if gc and above:
            score += 15
            reasons.append("✅ ゴールデンクロス形成 & 75日EMA上方（強気トレンド）")
        elif gc:
            score += 8
            reasons.append("⚠️ ゴールデンクロス形成（75日EMA未達）")
        elif above:
            score += 5
            reasons.append("⚠️ 75日EMA上方（クロス未形成）")
        else:
            reasons.append("❌ ゴールデンクロスなし・75日EMA下方")

        delta = closes.diff()
        gain = delta.clip(lower=0).rolling(14).mean()
        loss = (-delta).clip(lower=0).rolling(14).mean()
        rs = gain / (loss + 1e-10)
        rsi = float((100 - 100 / (1 + rs)).iloc[-1])
        result.rsi = round(rsi, 1)

        if 30 <= rsi <= 60:
            score += 15
            reasons.append(f"✅ RSI {rsi:.0f}: 適正ゾーン（上昇余地あり）")
        elif 20 <= rsi < 30:
            score += 10
            reasons.append(f"⚠️ RSI {rsi:.0f}: 売られすぎ圏（反転期待）")
        elif 60 < rsi <= 70:
            score += 8
            reasons.append(f"⚠️ RSI {rsi:.0f}: やや過熱気味")
        elif rsi > 70:
            score += 2
            reasons.append(f"❌ RSI {rsi:.0f}: 買われすぎ（過熱）")
        else:
            reasons.append(f"❌ RSI {rsi:.0f}: 過度な売られすぎ")

        if volumes is not None and len(volumes) >= 6:
            avg5 = float(volumes.tail(6).iloc[:-1].mean())
            cur_vol = float(volumes.iloc[-1])
            if avg5 > 0:
                ratio = cur_vol / avg5
                result.volume_ratio = round(ratio, 2)
                if ratio >= 1.5:
                    result.volume_surge = True
                    score += 10
                    reasons.append(f"✅ 出来高急増（{ratio:.1f}x 5日平均比）")
                elif ratio >= 1.2:
                    score += 5
                    reasons.append(f"⚠️ 出来高やや増加（{ratio:.1f}x）")
                else:
                    reasons.append(f"➖ 出来高変化なし（{ratio:.1f}x）")
    except Exception as e:
        reasons.append(f"テクニカル計算エラー: {str(e)}")

    result.score = round(score, 1)
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
        if pbr <= 1.2:
            val_score += 6; reasons.append(f"✅ PBR {pbr:.2f}倍（割安）")
        elif pbr <= 2.0:
            val_score += 3; reasons.append(f"⚠️ PBR {pbr:.2f}倍（普通）")
        else:
            reasons.append(f"❌ PBR {pbr:.2f}倍（割高）")
    else:
        data_missing += 6; reasons.append("⚪ PBRデータなし（スコア対象外）")

    if roe:
        if roe >= 10:
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


def _score_qualitative(fund_data: dict, gemini_api_key: Optional[str]) -> QualitativeResult:
    result = QualitativeResult()
    headlines = [h for h in fund_data.get("news_headlines", []) if h]

    if not headlines:
        result.score = 0.0
        result.max_score = 0  # no data → excluded from total
        result.data_source = "なし"
        result.reasons.append("⚪ ニュースデータなし（スコア対象外）")
        return result

    # ── WITHOUT Gemini API: keyword-based, max 7 pts ──
    if not gemini_api_key:
        result.data_source = "キーワード"
        result.max_score = 7  # cap because keyword analysis is less reliable

        neg_kw = ["不祥事", "下方修正", "赤字", "倒産", "scandal", "fraud", "bankruptcy",
                  "war", "downgrade", "warning", "recall", "investigation"]
        pos_kw = ["増益", "上方修正", "最高益", "好決算", "growth", "upgrade",
                  "record", "beat", "strong", "dividend", "buyback"]

        neg = sum(1 for h in headlines for kw in neg_kw if kw.lower() in h.lower())
        pos = sum(1 for h in headlines for kw in pos_kw if kw.lower() in h.lower())

        if neg > pos:
            result.score = max(0.0, 5.0 - neg * 1.5)
            result.sentiment = "negative"
            result.reasons.append(f"⚠️ ネガティブキーワード検知（{neg}件）")
        elif pos > 0:
            result.score = min(7.0, 5.0 + pos * 0.8)
            result.sentiment = "positive"
            result.reasons.append(f"✅ ポジティブキーワード検知（{pos}件）")
        else:
            result.score = 4.0
            result.sentiment = "neutral"
            result.reasons.append("➖ 中立的なニュース")

        result.reasons.append("　　Gemini APIキーを設定するとAI詳細分析（満点10点）が利用可能")
        result.news_analyzed = True
        return result

    # ── WITH Gemini API: AI-powered, max 10 pts ──
    result.data_source = "Gemini AI"
    result.max_score = 10
    try:
        import google.generativeai as genai
        import json
        import re as re_mod

        genai.configure(api_key=gemini_api_key)
        text_headlines = "\n".join(f"- {h}" for h in headlines)
        prompt = f"""以下の株式ニュースヘッドラインを分析し、投資家視点での感情スコアを0〜10の整数で返してください。
0=非常にネガティブ（不祥事・倒産・戦争等）、5=中立、10=非常にポジティブ（増益・最高益等）

ヘッドライン:
{text_headlines}

以下のJSON形式のみで回答してください:
{{"score": <0-10の整数>, "sentiment": "<positive/neutral/negative>", "reason": "<50字以内の日本語で分析根拠>"}}"""

        model = genai.GenerativeModel("gemini-2.0-flash")
        resp = model.generate_content(prompt)
        m = re_mod.search(r'\{.*\}', resp.text, re_mod.DOTALL)
        if m:
            parsed = json.loads(m.group())
            result.score = float(max(0, min(10, parsed.get("score", 5))))
            result.sentiment = parsed.get("sentiment", "neutral")
            result.reasons.append(f"✅ Gemini AI解析: {parsed.get('reason', '')}")
            result.news_analyzed = True
    except Exception as e:
        result.score = 5.0
        result.reasons.append(f"⚠️ Gemini APIエラー: {str(e)[:80]}")

    return result
