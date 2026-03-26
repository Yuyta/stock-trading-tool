import re
import yfinance as yf
import pandas as pd
import numpy as np
import logging
import requests
from typing import Optional, Dict, Any


def is_jp_stock(symbol: str) -> bool:
    return bool(re.match(r"^\d{4}(\.T|\.JP)?$", symbol.upper()))


def normalize_jp_symbol(symbol: str) -> str:
    if re.match(r"^\d{4}$", symbol):
        return symbol + ".T"
    return symbol


logger = logging.getLogger(__name__)

def fetch_price_history(symbol: str, timeframe: str = "1d") -> Optional[pd.DataFrame]:
    try:
        if is_jp_stock(symbol):
            symbol = normalize_jp_symbol(symbol)
        ticker = yf.Ticker(symbol)
        
        if timeframe in ["1m", "2m", "5m"]:
            period = "5d"
        elif timeframe in ["15m", "30m", "60m", "90m", "1h"]:
            period = "1mo"
        elif timeframe in ["1d"]:
            period = "6mo"
        else:
            period = "2y"
            
        df = ticker.history(period=period, interval=timeframe)
        return df if not df.empty else None
    except Exception as e:
        logger.error(f"Failed to fetch price history for {symbol}: {str(e)}")
        return None


def fetch_macro_data() -> Dict[str, Any]:
    result: Dict[str, Any] = {}
    items = {
        "vix": "^VIX", "wti": "CL=F", "gold": "GC=F", "nikkei": "^N225",
        "us10y": "^TNX", "usdjpy": "JPY=X", "nasdaq": "^IXIC",
        "spy": "SPY", "xlk": "XLK", "xlf": "XLF", "xle": "XLE", "xly": "XLY",
        "jp_bank": "1615.T", "jp_trade": "1629.T", "jp_auto": "1622.T", "jp_semi": "2644.T", "topix": "1306.T"
    }
    
    import concurrent.futures
    
    def fetch_one(key, sym):
        try:
            df = yf.Ticker(sym).history(period="3mo")
            return key, df["Close"] if not df.empty else None
        except Exception as e:
            logger.error(f"Failed to fetch macro data for {sym} ({key}): {str(e)}")
            return key, None

    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        future_to_key = {executor.submit(fetch_one, k, s): k for k, s in items.items()}
        for future in concurrent.futures.as_completed(future_to_key):
            k, data = future.result()
            result[k] = data
            
    return result




def _fetch_yfinance_fundamentals(symbol: str) -> Dict[str, Any]:
    result: Dict[str, Any] = {}
    try:
        # 日本株ならシンボルを正規化 (8136 -> 8136.T)
        if is_jp_stock(symbol):
            symbol = normalize_jp_symbol(symbol)
            
        ticker = yf.Ticker(symbol)
        # info取得（新方式）
        try:
            info = ticker.get_info()
        except Exception as e:
            logger.warning(f"Failed to get info for {symbol}: {str(e)}")
            info = {}

        # -------------------------
        # PER
        # -------------------------
        per = info.get("forwardPE") or info.get("trailingPE")

        # -------------------------
        # PBR
        # -------------------------
        pbr = info.get("priceToBook")

        # -------------------------
        # ROE
        # -------------------------
        roe = info.get("returnOnEquity")
        if roe is not None:
            roe = roe * 100

        result["per"] = per
        result["pbr"] = pbr
        result["roe"] = roe

        # -------------------------
        # 平均出来高
        # -------------------------
        result["average_volume"] = (
            info.get("averageVolume")
            or info.get("averageVolume10days")
        )
        # -------------------------
        # 営業利益成長率
        # -------------------------
        try:
            fin = ticker.financials
            if fin is not None and not fin.empty:
                op_key = next(
                    (k for k in fin.index if "Operating" in k and "Income" in k),
                    None
                )

                if op_key:

                    vals = list(
                        fin.loc[op_key]
                        .sort_index()
                        .dropna()
                    )

                    growths = []

                    for i in range(1, len(vals)):
                        prev = vals[i-1]

                        if prev != 0:
                            growth = (vals[i] - prev) / abs(prev) * 100
                            # 異常値保護: 極端な伸び率（IPO直後や特殊要因）を±500%に制限
                            growth = max(-500.0, min(500.0, growth))
                            growths.append(growth)

                    if growths:
                        result["op_income_growth_avg"] = float(
                            np.mean(growths[-3:])
                        )

        except Exception as e:
            logger.error(f"Error calculating fundamental growth for {symbol}: {str(e)}")
            pass

        # -------------------------
        # その他の基本情報
        # -------------------------
        result["market_cap"] = info.get("marketCap")
        result["sector"] = info.get("sector")

        # -------------------------
        # ニュース
        # -------------------------
        try:
            news = ticker.news
            if news:
                result["news_headlines"] = [
                    n.get("content", {}).get("title", "")
                    or n.get("title", "")
                    for n in news[:10]
                ]
                import time
                now = time.time()
                recent_count = sum(1 for n in news if now - n.get("providerPublishTime", 0) <= 86400)
                result["news_count_24h"] = recent_count
        except Exception as e:
            logger.error(f"Error fetching news for {symbol}: {str(e)}")
            pass
    except Exception as e:
        logger.error(f"Final error in _fetch_yfinance_fundamentals for {symbol}: {str(e)}")
        pass
    return result


def _to_float(val) -> Optional[float]:
    try:
        return float(val) if val is not None else None
    except (ValueError, TypeError):
        return None


def _fetch_jquants(symbol: str, refresh_token: str) -> Dict[str, Any]:
    result: Dict[str, Any] = {}
    try:
        resp = requests.post(
            "https://api.jquants.com/v1/token/auth_refresh",
            params={"refreshtoken": refresh_token},
            timeout=10,
        )
        if resp.status_code != 200:
            return result
        id_token = resp.json().get("idToken")
        if not id_token:
            return result

        headers = {"Authorization": f"Bearer {id_token}"}
        # Standard J-Quants code is 4 digits
        code = symbol.split(".")[0]

        stmts_resp = requests.get(
            "https://api.jquants.com/v1/fins/statements",
            params={"code": code},
            headers=headers,
            timeout=15,
        )
        if stmts_resp.status_code == 200:
            stmts = stmts_resp.json().get("statements", [])
            if stmts:
                # Sort by DisclosuresSince to get the latest filing
                stmts = sorted(stmts, key=lambda x: x.get("DisclosuresSince", ""), reverse=False)
                latest = stmts[-1]
                
                # J-Quants sometimes provides PER/PBR/ROE in specific summary filings
                # but often we need to calculate them or find them in different fields.
                result["per"] = _to_float(latest.get("PriceEarningsRatio") or latest.get("PER"))
                result["pbr"] = _to_float(latest.get("PriceBookValueRatio") or latest.get("PBR"))
                
                # ROE Calculation Fallback
                roe = _to_float(latest.get("ROE") or latest.get("ReturnOnEquity"))
                if roe is None:
                    # Try calculate NetIncome / Equity
                    net_income = _to_float(latest.get("NetIncome") or latest.get("Profit"))
                    equity = _to_float(latest.get("Equity") or latest.get("NetAssets"))
                    if net_income and equity and equity != 0:
                        roe = (net_income / equity) * 100
                result["roe"] = roe
                
                # Growth calculation
                # Use "NetSales" or "OperatingProfit"
                op_key = next((k for k in ["OperatingProfit", "OperatingIncome", "NetSales"] if k in latest), None)
                if op_key and len(stmts) >= 2:
                    # Get historical values for the same key
                    op_vals = []
                    for s in stmts:
                        v = _to_float(s.get(op_key))
                        if v is not None:
                            op_vals.append(v)
                    
                    if len(op_vals) >= 2:
                        growths = []
                        for i in range(1, len(op_vals)):
                            if op_vals[i-1] != 0:
                                g = (op_vals[i] - op_vals[i-1]) / abs(op_vals[i-1]) * 100
                                # 異常値保護: ±500%に制限
                                g = max(-500.0, min(500.0, g))
                                growths.append(g)
                        if growths:
                            # Average of last 3 periods if available
                            result["op_income_growth_avg"] = float(np.mean(growths[-3:]))
    except Exception as e:
        logger.error(f"Error in _fetch_jquants for {symbol}: {str(e)}")
        pass

    try:
        sym_yf = normalize_jp_symbol(symbol)
        ticker = yf.Ticker(sym_yf)
        
        info = {}
        try:
            info = ticker.get_info()
        except Exception as e:
            logger.warning(f"Failed to get info during J-Quants fallback for {symbol}: {str(e)}")
            pass
        result["market_cap"] = info.get("marketCap")
        result["sector"] = info.get("sector")
        
        news = ticker.news
        if news:
            result["news_headlines"] = [
                n.get("content", {}).get("title", "") or n.get("title", "")
                for n in news[:10]
            ]
            import time
            now = time.time()
            recent_count = sum(1 for n in news if now - n.get("providerPublishTime", 0) <= 86400)
            result["news_count_24h"] = recent_count
    except Exception as e:
        logger.error(f"Error in _fetch_jquants yfinance-fallback for {symbol}: {str(e)}")
        pass
    return result


def fetch_fundamentals(symbol: str, jquants_refresh_token: Optional[str] = None) -> Dict[str, Any]:
    # 戦略: J-Quants（信頼性の高い財務）と yfinance（比率・ニュース）を統合
    # 正規化は内部の関数でも行われるが、ここでも明示しておく
    yf_data = _fetch_yfinance_fundamentals(symbol)
    
    if is_jp_stock(symbol) and jquants_refresh_token:
        jq_data = _fetch_jquants(symbol, jquants_refresh_token)
        
        # J-Quantsから取得できた項目を優先的に上書き
        for key in ["per", "pbr", "roe", "op_income_growth_avg"]:
            if jq_data.get(key) is not None:
                yf_data[key] = jq_data[key]
        
        # J-Quantsからニュースが取れなかった場合 yf のものを使う (既にyf_dataに入っている)
        if jq_data.get("news_headlines"):
            yf_data["news_headlines"] = jq_data["news_headlines"]
            
        # J-Quants成功フラグ（analyzer側での表示切替に使用可能）
        if any(jq_data.get(k) is not None for k in ["per", "pbr", "roe", "op_income_growth_avg"]):
            yf_data["_jq_success"] = True
            
    return yf_data
