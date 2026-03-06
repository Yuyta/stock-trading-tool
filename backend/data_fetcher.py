import re
import yfinance as yf
import pandas as pd
import numpy as np
import requests
from typing import Optional, Dict, Any


def is_jp_stock(symbol: str) -> bool:
    return bool(re.match(r"^\d{4}(\.T|\.JP)?$", symbol.upper()))


def normalize_jp_symbol(symbol: str) -> str:
    if re.match(r"^\d{4}$", symbol):
        return symbol + ".T"
    return symbol


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
    except Exception:
        return None


def fetch_macro_data() -> Dict[str, Any]:
    result: Dict[str, Any] = {}
    for key, sym in {"vix": "^VIX", "wti": "CL=F", "gold": "GC=F", "nikkei": "^N225"}.items():
        try:
            df = yf.Ticker(sym).history(period="3mo")
            result[key] = df["Close"] if not df.empty else None
        except Exception:
            result[key] = None
    return result


def fetch_fundamentals(symbol: str, jquants_refresh_token: Optional[str] = None) -> Dict[str, Any]:
    if is_jp_stock(symbol) and jquants_refresh_token:
        return _fetch_jquants(symbol, jquants_refresh_token)
    return _fetch_yfinance_fundamentals(symbol)


def _fetch_yfinance_fundamentals(symbol: str) -> Dict[str, Any]:
    result: Dict[str, Any] = {}
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info
        result["per"] = info.get("forwardPE") or info.get("trailingPE")
        result["pbr"] = info.get("priceToBook")
        roe = info.get("returnOnEquity")
        result["roe"] = roe * 100 if roe is not None else None
        result["average_volume"] = info.get("averageVolume") or info.get("averageVolume10days")

        try:
            fin = ticker.financials
            if fin is not None and not fin.empty:
                op_key = next((k for k in fin.index if "Operating" in k and "Income" in k), None)
                if op_key:
                    vals = list(fin.loc[op_key].sort_index().dropna())
                    growths = [
                        (vals[i] - vals[i-1]) / abs(vals[i-1]) * 100
                        for i in range(1, len(vals)) if vals[i-1] != 0
                    ]
                    if growths:
                        result["op_income_growth_avg"] = float(np.mean(growths[-3:]))
        except Exception:
            pass

        try:
            news = ticker.news
            if news:
                result["news_headlines"] = [
                    n.get("content", {}).get("title", "") or n.get("title", "")
                    for n in news[:10]
                ]
        except Exception:
            pass
    except Exception:
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
                latest = stmts[-1]
                result["per"] = _to_float(latest.get("PER") or latest.get("PriceEarningsRatio"))
                result["pbr"] = _to_float(latest.get("PBR") or latest.get("PriceBookValueRatio"))
                result["roe"] = _to_float(latest.get("ROE"))
                op_key = next((k for k in ["OperatingProfit", "OperatingIncome"] if k in latest), None)
                if op_key and len(stmts) >= 3:
                    op_vals = [_to_float(s.get(op_key)) for s in stmts[-4:] if _to_float(s.get(op_key)) is not None]
                    growths = [
                        (op_vals[i] - op_vals[i-1]) / abs(op_vals[i-1]) * 100
                        for i in range(1, len(op_vals)) if op_vals[i-1] != 0
                    ]
                    if growths:
                        result["op_income_growth_avg"] = float(np.mean(growths))
    except Exception:
        pass

    try:
        sym_yf = normalize_jp_symbol(symbol)
        ticker = yf.Ticker(sym_yf)
        news = ticker.news
        if news:
            result["news_headlines"] = [
                n.get("content", {}).get("title", "") or n.get("title", "")
                for n in news[:10]
            ]
    except Exception:
        pass
    return result
