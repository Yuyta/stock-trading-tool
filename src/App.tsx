import { useState, useEffect, useRef } from 'react';
// import html2canvas from 'html2canvas'; // 削除
import {
  Activity, BarChart3, Settings as SettingsIcon, PlayCircle, RefreshCw,
  TrendingUp, TrendingDown, Minus, ShieldCheck, ShieldAlert, ShieldX,
  AlertCircle, ChevronRight, Server, Share2, Coins, LogIn, LogOut, Clock, Menu, X
} from 'lucide-react';
import {
  ResponsiveContainer, ComposedChart, Area, XAxis, YAxis, Tooltip, CartesianGrid, Line, Legend
} from 'recharts';
import { AnalysisResult, AppSettings, SearchResult } from './types';
import { SettingsModal } from './SettingsModal';
import { useAuth } from './AuthContext';
import { AuthModal } from './AuthModal';
import { History } from './History';
import './App.css';

const SETTINGS_KEY = 'stock_analyzer_settings';

const defaultSettings: AppSettings = { jquantsRefreshToken: '', geminiApiKey: '' };

function loadSettings(): AppSettings {
  try {
    const raw = localStorage.getItem(SETTINGS_KEY);
    return raw ? { ...defaultSettings, ...JSON.parse(raw) } : defaultSettings;
  } catch {
    return defaultSettings;
  }
}

function saveSettings(s: AppSettings) {
  localStorage.setItem(SETTINGS_KEY, JSON.stringify(s));
}

function ScoreBar({ value, max, color }: { value: number; max: number; color: string }) {
  const pct = Math.min(100, (value / max) * 100);
  return (
    <div className="score-bar-track">
      <div className="score-bar-fill" style={{ width: `${pct}%`, background: color }} />
    </div>
  );
}

function MacroBadge({ passed, vixMode, blockReason }: { passed: boolean; vixMode: string; blockReason?: string }) {
  if (!passed) {
    return (
      <div className="layer-status danger">
        <ShieldX size={16} />
        <span>マクロ: 緊急停止 — {blockReason}</span>
      </div>
    );
  }
  if (vixMode === 'caution') {
    return (
      <div className="layer-status warning">
        <ShieldAlert size={16} />
        <span>マクロ: 警戒モード（新規買い50%制限）</span>
      </div>
    );
  }
  return (
    <div className="layer-status success">
      <ShieldCheck size={16} />
      <span>マクロ: 正常（全フィルター通過）</span>
    </div>
  );
}

const API_BASE = (import.meta.env.VITE_API_URL as string) || '';

export default function App() {
  const [symbol, setSymbol] = useState('');
  const [timeframe, setTimeframe] = useState('1d');
  const [tradeStyle, setTradeStyle] = useState('long_hold');
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showSettings, setShowSettings] = useState(false);
  const [settings, setSettings] = useState<AppSettings>(loadSettings);
  const [backendOnline, setBackendOnline] = useState<boolean | null>(null);
  const chartRef = useRef<HTMLDivElement>(null);
  const [isSharing, setIsSharing] = useState(false);
  const [showAuth, setShowAuth] = useState(false);
  const { user, token, logout } = useAuth();
  const [view, setView] = useState<'home' | 'history'>('home');
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const [searchResults, setSearchResults] = useState<SearchResult[]>([]);
  const [showSearchDropdown, setShowSearchDropdown] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // オートコンプリートのデバウンス検索
  useEffect(() => {
    const timer = setTimeout(async () => {
      if (symbol.length >= 2) {
        try {
          const resp = await fetch(`${API_BASE}/api/search?q=${encodeURIComponent(symbol)}`);
          if (resp.ok) {
            const data = await resp.json();
            setSearchResults(data.results);
            setShowSearchDropdown(data.results.length > 0);
          }
        } catch (e) {
          console.error('Search error:', e);
        }
      } else {
        setSearchResults([]);
        setShowSearchDropdown(false);
      }
    }, 400);

    return () => clearTimeout(timer);
  }, [symbol]);

  // クリック以外でドロップダウンを閉じるためのイベントリスナー
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setShowSearchDropdown(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  useEffect(() => {
    fetch(`${API_BASE}/api/health`)
      .then(r => r.ok ? setBackendOnline(true) : setBackendOnline(false))
      .catch(() => setBackendOnline(false));
  }, []);

  const handleSaveSettings = (s: AppSettings) => {
    setSettings(s);
    saveSettings(s);
  };

  const handleAnalyze = async (overrideSymbol?: string) => {
    let currentSymbol = overrideSymbol || symbol;

    // もし入力がティッカー形式っぽくなく（例: 日本語）、かつ検索結果があれば筆頭を採用する
    if (!overrideSymbol && searchResults.length > 0 && !/^\d{4}$|^[A-Z]{1,5}$/.test(currentSymbol)) {
      if (searchResults[0].symbol !== 'NOTICE') {
        currentSymbol = searchResults[0].symbol;
        setSymbol(currentSymbol);
      }
    }

    if (!currentSymbol.trim()) return;
    setIsAnalyzing(true);
    setResult(null);
    setError(null);
    setShowSearchDropdown(false);

    try {
      const resp = await fetch(`${API_BASE}/api/analyze`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          symbol: currentSymbol.trim().toUpperCase(),
          timeframe,
          trade_style: tradeStyle,
          jquants_refresh_token: settings.jquantsRefreshToken || undefined,
          gemini_api_key: settings.geminiApiKey || undefined,
        }),
      });
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const data: AnalysisResult = await resp.json();
      setResult(data);
      setSymbol(data.symbol); // 正しいシンボル（例: 7867）に更新

      // ログイン中なら履歴を保存
      if (user && token) {
        try {
          await fetch(`${API_BASE}/api/history`, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({
              symbol: data.symbol,
              trade_style: data.trade_style,
              signal: data.signal,
              total_score: data.total_score,
              max_score: data.max_score,
              analysis_mode: data.analysis_mode,
              result_json: JSON.stringify(data)
            }),
          });
        } catch (saveErr) {
          console.error('Failed to save history:', saveErr);
        }
      }
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : '通信エラー');
    } finally {
      setIsAnalyzing(false);
    }
  };

  const copyToClipboard = async (text: string) => {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      await navigator.clipboard.writeText(text);
      return true;
    }

    // Fallback for non-secure contexts (HTTP) or browsers missing Clipboard API
    const textArea = document.createElement("textarea");
    textArea.value = text;
    textArea.style.position = "fixed";
    textArea.style.left = "-9999px";
    textArea.style.top = "0";
    document.body.appendChild(textArea);
    textArea.focus();
    textArea.select();
    try {
      document.execCommand('copy');
      textArea.remove();
      return true;
    } catch (err) {
      textArea.remove();
      return false;
    }
  };

  const handleShare = async () => {
    if (!result) return;
    setIsSharing(true);

    const now = new Date();
    const dateStr = now.toLocaleString('ja-JP', {
      year: 'numeric', month: '2-digit', day: '2-digit',
      hour: '2-digit', minute: '2-digit'
    });

    const { macro, fundamental, technical, qualitative, risk } = result;
    const styleLabelMap: Record<string, string> = {
      long_hold: '長期 (配当・インカム)',
      swing: '中長期 (スイング)',
      day: '短期 (デイトレ)'
    };

    let summaryText = `【TradeAlgo Pro 分析レポート】\n` +
      `発行日時: ${dateStr}\n` +
      `銘柄: ${result.symbol}\n` +
      `トレードスタイル: ${styleLabelMap[result.trade_style] ?? result.trade_style}\n` +
      `判定: ${result.signal}\n` +
      `総合スコア: ${result.total_score}/${result.max_score} (${result.analysis_mode})\n` +
      `========================\n\n` +
      `■ 1. マクロ環境 (判定: ${macro.passed ? '正常' : '警戒'})\n` +
      `・VIX: ${macro.vix ?? '—'} (${macro.vix_mode})\n` +
      `・米10年債: ${macro.us10y ?? '—'}%\n` +
      `・ドル円騰落: ${macro.usdjpy_trend > 0 ? '+' : ''}${macro.usdjpy_trend}%\n` +
      `・原油σ: ${macro.oil_sigma ?? '—'} / 金σ: ${macro.gold_sigma ?? '—'}\n` +
      `${macro.nasdaq_below_ma75 ? '⚠️ NASDAQ 75日線下\n' : ''}` +
      `${macro.market_below_ma75 ? '⚠️ 市場 75日線下\n' : ''}` +
      `${macro.commodity_alert ? '⚠️ コモディティ急騰警報\n' : ''}` +
      `${macro.strong_sectors?.length ? `🔥 流入: ${macro.strong_sectors.join(', ')}\n` : ''}` +
      `${macro.weak_sectors?.length ? `❄️ 流出: ${macro.weak_sectors.join(', ')}\n` : ''}` +
      `${macro.block_reason ? `理由: ${macro.block_reason}\n` : ''}\n`;

    if (fundamental) {
      summaryText += `■ 2. ファンダメンタル (スコア: ${fundamental.sub_total}/${fundamental.max_score})\n` +
        `・PER: ${fundamental.per ?? '—'}倍 / PBR: ${fundamental.pbr ?? '—'}倍\n` +
        `・ROE: ${fundamental.roe ?? '—'}% / 営業利益成長: ${fundamental.op_income_growth_avg ?? '—'}%\n` +
        `・根拠:\n ${fundamental.reasons.map(r => `  - ${r}`).join('\n')}\n` +
        `  (ソース: ${fundamental.data_source})\n\n`;
    }

    if (technical) {
      summaryText += `■ 3. テクニカル (スコア: ${technical.score}/40)\n` +
        `・現在値: ${technical.current_price?.toLocaleString() ?? '—'} / RSI(14): ${technical.rsi ?? '—'}\n` +
        `・MACD: ${technical.macd ?? '—'} (Sig: ${technical.macd_signal ?? '—'})\n` +
        `・VWAP: ${technical.vwap?.toLocaleString() ?? '—'} / 出来高比: ${technical.volume_ratio ?? '—'}x\n` +
        `・ボリンジャー: ${technical.bollinger_lower?.toLocaleString() ?? '—'} - ${technical.bollinger_upper?.toLocaleString() ?? '—'}\n` +
        `・EMA: [5] ${technical.ema5?.toLocaleString() ?? '—'} [20] ${technical.ema20?.toLocaleString() ?? '—'} [75] ${technical.ema75?.toLocaleString() ?? '—'}\n` +
        `・根拠:\n ${technical.reasons.map(r => `  - ${r}`).join('\n')}\n\n`;
    }

    if (qualitative) {
      summaryText += `■ 4. 定性・ニュース (スコア: ${qualitative.score}/${qualitative.max_score})\n` +
        `・根拠:\n ${qualitative.reasons.map(r => `  - ${r}`).join('\n')}\n` +
        `  (ソース: ${qualitative.data_source})\n\n`;
    }

    if (risk) {
      summaryText += `■ ⚖️ リスク管理\n` +
        `・流動性: ${risk.liquidity_ok ? '✅ 問題なし' : '❌ 要注意'}\n` +
        `${risk.trailing_stop_base ? `・${risk.trailing_stop_base_label}: ${risk.trailing_stop_base.toLocaleString()}\n` : ''}` +
        `${risk.trailing_stop_high ? `・${risk.trailing_stop_high_label}: ${risk.trailing_stop_high.toLocaleString()}\n` : ''}` +
        `${risk.warnings?.length ? `⚠️ 警告:\n ${risk.warnings.map(w => `  - ${w}`).join('\n')}\n` : ''}\n`;
    }

    if (result.income) {
      const inc = result.income;
      summaryText += `■ 💰 配当・インカム (スコア: ${inc.score}/${inc.max_score})\n` +
        `・利回り: ${inc.dividend_yield ?? '—'}% / 5年平均: ${inc.five_year_avg_yield ?? '—'}%\n` +
        `・配当性向: ${inc.payout_ratio ?? '—'}%\n` +
        `・グレアム指数: ${inc.graham_number ?? '—'}\n` +
        `・根拠:\n ${inc.reasons.map(r => `  - ${r}`).join('\n')}\n\n`;
    }

    summaryText += `----------\n#株 #テクニカル分析 #TradeAlgoPro`;

    const shareData: ShareData = {
      title: `TradeAlgo Pro: ${result.symbol} 判定`,
      text: summaryText,
    };

    try {
      if (navigator.share) {
        // --- Navigator Share (Text Only) ---
        await navigator.share(shareData);
      } else {
        throw new Error('Web Share API not supported');
      }
    } catch (err) {
      if ((err as Error).name !== 'AbortError') {
        console.warn('Navigator Share failed, trying Clipboard copy', err);
        const copied = await copyToClipboard(summaryText);
        if (copied) {
          alert('結果をクリップボードにコピーしました。');
        } else {
          alert('共有に失敗しました。');
        }
      }
    } finally {
      setIsSharing(false);
    }
  };

  const getSignalColor = (signal: string) => {
    if (signal.startsWith('Strong Buy')) return 'var(--success)';
    if (signal.startsWith('Buy')) return '#34d399';
    if (signal.startsWith('Hold')) return 'var(--warning)';
    if (signal.startsWith('Sell') || signal === '見送り') return 'var(--danger)';
    return 'var(--text-secondary)';
  };

  const getSignalIcon = (signal: string) => {
    if (signal.startsWith('Strong Buy') || signal.startsWith('Buy')) return <TrendingUp size={52} />;
    if (signal.startsWith('Sell') || signal === '見送り') return <TrendingDown size={52} />;
    return <Minus size={52} />;
  };

  return (
    <div className="app-container">
      {showSettings && (
        <SettingsModal
          settings={settings}
          onSave={handleSaveSettings}
          onClose={() => setShowSettings(false)}
        />
      )}

      {showAuth && (
        <AuthModal onClose={() => setShowAuth(false)} />
      )}

      <header className="header glass-panel animate-slide-in" style={{ flexDirection: 'column', alignItems: 'stretch', gap: 0 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', width: '100%' }}>
          <div className="header-title" onClick={() => setView('home')} style={{ cursor: 'pointer' }}>
            <Activity className="logo-icon" />
            <span>TradeAlgo Pro</span>
          </div>

          {/* API Connectivity Status (In header) */}
          <div className={`backend-badge ${backendOnline === true ? 'online' : backendOnline === false ? 'offline' : 'checking'}`} style={{ marginLeft: 'auto', marginRight: '1rem' }}>
            <Server size={14} />
            <span>
              {backendOnline === true ? (
                <>
                  {settings.jquantsRefreshToken && settings.geminiApiKey ? 'J-Quants + Gemini' :
                    settings.jquantsRefreshToken ? 'J-Quants' :
                      settings.geminiApiKey ? 'Gemini' :
                        'API未設定'}
                </>
              ) : backendOnline === false ? 'サーバー未起動' : '接続確認中'}
            </span>
          </div>

          <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center' }}>
            {user ? (
              <span className="user-name">{user.username}</span>
            ) : (
              <button className="button small" onClick={() => setShowAuth(true)}>
                <LogIn size={16} />
                <span>ログイン / 新規登録</span>
              </button>
            )}

            <button
              className="button secondary icon-only"
              onClick={() => setIsMenuOpen(!isMenuOpen)}
              aria-label="メニュー"
            >
              {isMenuOpen ? <X size={20} /> : <Menu size={20} />}
            </button>
          </div>
        </div>

        {/* Hamburger Menu (Push layout) */}
        {isMenuOpen && (
          <div className="menu-push glass-panel">
            <div className="menu-content">
              <div className="menu-items-grid">
                {user && (
                  <button
                    className={`menu-item ${view === 'history' ? 'active' : ''}`}
                    onClick={() => { setView(view === 'home' ? 'history' : 'home'); setIsMenuOpen(false); }}
                  >
                    {view === 'home' ? <Clock size={18} /> : <BarChart3 size={18} />}
                    <span>{view === 'home' ? '履歴を見る' : '分析画面へ戻る'}</span>
                  </button>
                )}

                <button className="menu-item" onClick={() => { setShowSettings(true); setIsMenuOpen(false); }}>
                  <SettingsIcon size={18} />
                  <span>設定</span>
                </button>

                {user && (
                  <button className="menu-item danger" onClick={() => { logout(); setIsMenuOpen(false); }}>
                    <LogOut size={18} />
                    <span>ログアウト</span>
                  </button>
                )}
              </div>
            </div>
          </div>
        )}
      </header>

      <main className="main-content">
        {view === 'history' ? (
          <History
            onBack={() => setView('home')}
            onSelectDetail={(res) => {
              setResult(res);
              setView('home');
              // スムーズに結果パネルへスクロール
              setTimeout(() => {
                const resultsPanel = document.querySelector('.result-panel');
                resultsPanel?.scrollIntoView({ behavior: 'smooth' });
              }, 100);
            }}
          />
        ) : (
          <>
            <div>
              <div className="card glass-panel animate-slide-in">
                <div className="card-header">
                  <BarChart3 className="card-icon" />
                  <span>分析対象</span>
                </div>
                <div className="input-row">
                  <div className="input-group search-autocomplete-container" ref={dropdownRef}>
                    <span className="input-label">銘柄コード / 企業名</span>
                    <input
                      type="text"
                      className="input"
                      value={symbol}
                      onChange={(e) => setSymbol(e.target.value)}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter') {
                          // もし検索結果があればその筆頭を選択、なければ今の入力をそのまま使う
                          if (searchResults.length > 0) {
                            const bestMatch = searchResults[0].symbol;
                            setSymbol(bestMatch);
                            handleAnalyze(bestMatch);
                          } else {
                            handleAnalyze();
                          }
                          setShowSearchDropdown(false);
                        }
                      }}
                      onFocus={() => { if (searchResults.length > 0) setShowSearchDropdown(true); }}
                      placeholder="例: Sony, 7203, AAPL"
                      autoComplete="off"
                    />
                    {showSearchDropdown && (
                      <div className="search-dropdown glass-panel">
                        {searchResults.map((res, i) => (
                          <div
                            key={`${res.symbol}-${i}`}
                            className={`search-item ${res.symbol === 'NOTICE' ? 'search-hint' : ''}`}
                            onClick={() => {
                              if (res.symbol === 'NOTICE') return;
                              setSymbol(res.symbol);
                              setShowSearchDropdown(false);
                              handleAnalyze(res.symbol);
                            }}
                          >
                            <div className="search-item-primary">
                              <span className="search-item-symbol">{res.symbol}</span>
                              <span className="search-item-name">{res.name}</span>
                            </div>
                            <div className="search-item-secondary">
                              <span className="search-item-exchange">{res.exchange}</span>
                              {res.type && <span className="search-item-type">{res.type}</span>}
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                  <div className="input-group">
                    <span className="input-label">トレードスタイル</span>
                    <select className="input" value={tradeStyle} onChange={(e) => {
                      setTradeStyle(e.target.value);
                      if (e.target.value === 'day' && timeframe === '1d') {
                        setTimeframe('5m');
                      }
                    }}>
                      <option value="long_hold">長期 (配当・インカム)</option>
                      <option value="swing">中長期 (スイング)</option>
                      <option value="day">短期 (デイトレ)</option>
                    </select>
                  </div>
                  <div className="input-group">
                    <span className="input-label">時間軸</span>
                    <select className="input" value={timeframe} onChange={(e) => setTimeframe(e.target.value)}>
                      <option value="1m">1分足</option>
                      <option value="5m">5分足</option>
                      <option value="15m">15分足</option>
                      <option value="1h">1時間足</option>
                      <option value="1d">日足</option>
                      <option value="1wk">週足</option>
                    </select>
                  </div>
                </div>
                <button
                  className="button"
                  onClick={() => handleAnalyze()}
                  disabled={isAnalyzing || !symbol || backendOnline === false}
                >
                  {isAnalyzing ? (
                    <><RefreshCw size={20} className="spin" />分析中...</>
                  ) : (
                    <><PlayCircle size={20} />自動判定を開始</>
                  )}
                </button>
                {backendOnline === false && (
                  <div className="alert-box warning">
                    <AlertCircle size={16} />
                    <span>バックエンドが起動していません。<code>backend/</code> ディレクトリで <code>uvicorn main:app --reload</code> を実行してください。</span>
                  </div>
                )}
              </div>

              <div className="card glass-panel" style={{ marginTop: '1.5rem' }} ref={chartRef}>
                <div className="card-header">
                  <Activity className="card-icon" />
                  <span>価格チャート（参考）</span>
                </div>
                <div className="chart-placeholder" style={{ height: '400px', padding: '10px 0', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                  {result?.chart_data && result.chart_data.length > 0 ? (
                    <ResponsiveContainer width="100%" height="100%">
                      <ComposedChart data={result.chart_data} margin={{ top: 5, right: 0, left: -20, bottom: 0 }}>
                        <defs>
                          <linearGradient id="colorPrice" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="5%" stopColor={getSignalColor(result.signal)} stopOpacity={0.5} />
                            <stop offset="95%" stopColor={getSignalColor(result.signal)} stopOpacity={0} />
                          </linearGradient>
                        </defs>
                        <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" vertical={false} />
                        <XAxis
                          dataKey="time"
                          tick={{ fill: 'var(--text-muted)', fontSize: 10 }}
                          tickLine={false}
                          axisLine={false}
                          minTickGap={20}
                        />
                        <YAxis
                          domain={['auto', 'auto']}
                          tick={{ fill: 'var(--text-muted)', fontSize: 10 }}
                          tickLine={false}
                          axisLine={false}
                          tickFormatter={(val) => val.toLocaleString()}
                        />
                        <Tooltip
                          contentStyle={{ backgroundColor: 'rgba(15, 23, 42, 0.9)', borderColor: 'rgba(255,255,255,0.1)', color: 'white' }}
                          itemStyle={{ color: 'var(--accent-primary)' }}
                          labelStyle={{ color: 'var(--text-muted)' }}
                        />
                        <Area type="monotone" dataKey="price" stroke={getSignalColor(result.signal)} fillOpacity={1} fill="url(#colorPrice)" name="価格" />

                        {/* トレードスタイルに応じた指標表示 */}
                        {result.trade_style !== 'long_hold' && (
                          <Line type="monotone" dataKey="ema5" stroke="#fcd34d" strokeWidth={2} dot={false} name="5日" />
                        )}
                        <Line type="monotone" dataKey="ema20" stroke="#fb923c" strokeWidth={2} dot={false} name="20日" />
                        <Line type="monotone" dataKey="ema75" stroke="#a855f7" strokeWidth={2} dot={false} name="75日" />
                        {result.trade_style !== 'day' && (
                          <Line type="monotone" dataKey="ema200" stroke="#0ea5e9" strokeWidth={2} dot={false} name="200日" />
                        )}

                        {result.trade_style !== 'long_hold' && (
                          <>
                            <Line type="monotone" dataKey="bollinger_upper" stroke="rgba(255,255,255,0.3)" strokeDasharray="3 3" dot={false} name="ボリバン上限" />
                            <Line type="monotone" dataKey="bollinger_lower" stroke="rgba(255,255,255,0.3)" strokeDasharray="3 3" dot={false} name="ボリバン下限" />
                          </>
                        )}

                        <Legend verticalAlign="top" height={30} wrapperStyle={{ fontSize: '11px', paddingBottom: '10px' }} iconSize={10} />
                      </ComposedChart>
                    </ResponsiveContainer>
                  ) : (
                    <div style={{ color: 'var(--text-muted)', textAlign: 'center' }}>
                      <p>チャートデータがありません</p>
                      <p>（判定を実行してください）</p>
                    </div>
                  )}
                </div>

                {result?.technical && (
                  <div className="metric-grid">
                    <div className="metric-card">
                      <span className="metric-title">現在値</span>
                      <span className="metric-value">{result.technical.current_price?.toLocaleString() ?? '—'}</span>
                    </div>
                    <div className="metric-card">
                      <span className="metric-title">RSI (14)</span>
                      <span className="metric-value">{result.technical.rsi ?? '—'}</span>
                    </div>
                    <div className="metric-card">
                      <span className="metric-title">MACD (Sig)</span>
                      <span className="metric-value" style={{ fontSize: '0.9rem' }}>
                        {result.technical.macd ?? '—'} ({result.technical.macd_signal ?? '—'})
                      </span>
                    </div>
                    {result.trade_style === 'day' && (
                      <div className="metric-card">
                        <span className="metric-title">VWAP</span>
                        <span className="metric-value">{result.technical.vwap?.toLocaleString() ?? '—'}</span>
                      </div>
                    )}
                    <div className="metric-card">
                      <span className="metric-title">出来高比</span>
                      <span className="metric-value">{result.technical.volume_ratio != null ? `${result.technical.volume_ratio}x` : '—'}</span>
                    </div>
                    <div className="metric-card">
                      <span className="metric-title">指数平滑移動平均 (EMA)</span>
                      <div className="metric-value" style={{ fontSize: '0.75rem', display: 'flex', flexDirection: 'column', gap: '2px', marginTop: '4px' }}>
                        {result.trade_style !== 'long_hold' && (
                          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                            <span style={{ width: '8px', height: '2px', background: '#fcd34d', flexShrink: 0 }} />
                            <span>5日: {result.technical.ema5?.toLocaleString() ?? '—'}</span>
                          </div>
                        )}
                        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                          <span style={{ width: '8px', height: '2px', background: '#fb923c', flexShrink: 0 }} />
                          <span>20日: {result.technical.ema20?.toLocaleString() ?? '—'}</span>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                          <span style={{ width: '8px', height: '2px', background: '#a855f7', flexShrink: 0 }} />
                          <span>75日: {result.technical.ema75?.toLocaleString() ?? '—'}</span>
                        </div>
                        {result.trade_style !== 'day' && result.technical.ema200 != null && (
                          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                            <span style={{ width: '8px', height: '2px', background: '#0ea5e9', flexShrink: 0 }} />
                            <span>200日: {result.technical.ema200.toLocaleString()}</span>
                          </div>
                        )}
                      </div>
                    </div>
                    <div className="metric-card">
                      <span className="metric-title">ボリンジャー(±2σ)</span>
                      <span className="metric-value" style={{ fontSize: '0.85rem' }}>
                        {result.technical.bollinger_lower != null && result.technical.bollinger_upper != null
                          ? `${result.technical.bollinger_lower.toLocaleString()} - ${result.technical.bollinger_upper.toLocaleString()}`
                          : '—'}
                      </span>
                    </div>
                  </div>
                )}
              </div>
            </div>

            {/* Right column: Results */}
            <div className="card glass-panel result-panel">
              <div className="card-header" style={{ justifyContent: 'space-between' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                  <AlertCircle className="card-icon" />
                  <span>AI 判定結果</span>
                </div>
                {result && !isAnalyzing && (
                  <button
                    className="button secondary"
                    onClick={handleShare}
                    disabled={isSharing}
                    style={{ padding: '0.4rem 0.8rem', fontSize: '0.8rem' }}
                  >
                    {isSharing ? <RefreshCw size={14} className="spin" /> : <Share2 size={14} />}
                    <span>共有</span>
                  </button>
                )}
              </div>

              {!result && !isAnalyzing && !error && (
                <div className="empty-state">
                  <BarChart3 size={48} style={{ opacity: 0.3, marginBottom: '1rem' }} />
                  <p>銘柄を入力して<br />「自動判定を開始」をクリック</p>
                </div>
              )}

              {isAnalyzing && (
                <div className="empty-state">
                  <div className="spinner" style={{ marginBottom: '1rem' }} />
                  <p>三層分析を実行中...</p>
                  <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>マクロ → ファンダメンタル → テクニカル</p>
                </div>
              )}

              {error && (
                <div className="alert-box danger">
                  <AlertCircle size={16} />
                  <span>{error}</span>
                </div>
              )}

              {result && !isAnalyzing && (
                <div className="result-body animate-slide-in">
                  {/* Signal */}
                  <div className="signal-block" style={{ color: getSignalColor(result.signal) }}>
                    {getSignalIcon(result.signal)}
                    <div>
                      <div className="signal-text">{result.signal}</div>
                      {result.total_score != null && result.max_score > 0 && (
                        <div className="score-badge" style={{ borderColor: getSignalColor(result.signal) }}>
                          {result.total_score} / {result.max_score} <span style={{ fontSize: '0.7em', marginLeft: '6px', fontWeight: 'normal' }}>({result.analysis_mode})</span>
                        </div>
                      )}
                      {/* 判定時のトレードスタイル表示 */}
                      <div style={{ marginTop: '6px' }}>
                        <span className="tag">判定スタイル: {result.trade_style === 'long_hold' ? '長期 (配当・インカム)' : result.trade_style === 'day' ? '短期 (デイトレ)' : '中長期 (スイング)'}</span>
                      </div>
                    </div>
                  </div>

                  {result.error && (
                    <div className="alert-box warning">
                      <AlertCircle size={14} />
                      <span>{result.error}</span>
                    </div>
                  )}

                  {/* Layer 1: Macro */}
                  <MacroBadge
                    passed={result.macro.passed}
                    vixMode={result.macro.vix_mode}
                    blockReason={result.macro.block_reason}
                  />
                  <div className="layer-details" style={{ flexWrap: 'wrap' }}>
                    {result.macro.vix != null && <span className="tag">VIX: {result.macro.vix}</span>}
                    {result.macro.us10y != null && <span className="tag">米10年金利: {result.macro.us10y}%</span>}
                    {result.macro.usdjpy_trend !== 0 && <span className="tag">USD/JPY: {result.macro.usdjpy_trend > 0 ? '+' : ''}{result.macro.usdjpy_trend}%</span>}
                    {result.macro.oil_sigma != null && <span className="tag">原油σ: {result.macro.oil_sigma}</span>}
                    {result.macro.gold_sigma != null && <span className="tag">金σ: {result.macro.gold_sigma}</span>}
                    {result.macro.nasdaq_below_ma75 && <span className="tag danger-tag">NASDAQ 75日線下 ⚠️</span>}
                    {result.macro.market_below_ma75 && <span className="tag danger-tag">市場 75日線下 ⚠️</span>}
                    {result.macro.commodity_alert && <span className="tag danger-tag">コモディティ急騰 ⚠️</span>}
                  </div>

                  {/* Sector Rotation Info */}
                  {((result.macro.strong_sectors && result.macro.strong_sectors.length > 0) || (result.macro.weak_sectors && result.macro.weak_sectors.length > 0)) && (
                    <div className="layer-details" style={{ marginTop: '0.5rem', flexWrap: 'wrap' }}>
                      {result.macro.strong_sectors && result.macro.strong_sectors.length > 0 && (
                        <span className="tag" style={{ background: 'rgba(52, 211, 153, 0.2)', color: '#34d399', border: '1px solid rgba(52, 211, 153, 0.3)' }}>
                          🔥 資金流入セクター: {result.macro.strong_sectors.join(', ')}
                        </span>
                      )}
                      {result.macro.weak_sectors && result.macro.weak_sectors.length > 0 && (
                        <span className="tag" style={{ background: 'rgba(248, 113, 113, 0.2)', color: '#f87171', border: '1px solid rgba(248, 113, 113, 0.3)' }}>
                          ❄️ 資金流出セクター: {result.macro.weak_sectors.join(', ')}
                        </span>
                      )}
                    </div>
                  )}

                  {/* Layer 2: Fundamental */}
                  {result.fundamental && (
                    <div className="score-section">
                      <div className="score-section-header">
                        <span>📊 ファンダメンタル</span>
                        {result.fundamental.max_score > 0 ? (
                          <span className="score-num">{result.fundamental.sub_total} / {result.fundamental.max_score}</span>
                        ) : (
                          <span className="score-num" style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>スコア対象外</span>
                        )}
                      </div>
                      {result.fundamental.max_score > 0 && <ScoreBar value={result.fundamental.sub_total} max={result.fundamental.max_score} color="var(--accent-primary)" />}
                      <div className="sub-scores" style={{ justifyContent: 'space-between' }}>
                        <div style={{ display: 'flex', gap: '1rem' }}>
                          {result.fundamental.max_score > 0 && <span>成長性: {result.fundamental.growth_score}  割安性: {result.fundamental.valuation_score}</span>}
                        </div>
                        <span className="tag" style={{ border: 'none', background: 'rgba(255,255,255,0.1)' }}>ソース: {result.fundamental.data_source}</span>
                      </div>
                      <div className="kv-grid">
                        {result.fundamental.per != null && <><span>PER</span><span>{result.fundamental.per}倍</span></>}
                        {result.fundamental.pbr != null && <><span>PBR</span><span>{result.fundamental.pbr}倍</span></>}
                        {result.fundamental.roe != null && <><span>ROE</span><span>{result.fundamental.roe}%</span></>}
                        {result.fundamental.op_income_growth_avg != null && <><span>営業利益成長</span><span>{result.fundamental.op_income_growth_avg}%</span></>}
                      </div>
                      <ul className="reason-list">
                        {result.fundamental.reasons.map((r, i) => (
                          <li key={i}><ChevronRight size={13} />{r}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {/* Layer 3: Technical */}
                  {result.technical && (
                    <div className="score-section">
                      <div className="score-section-header">
                        <span>📈 テクニカル</span>
                        <span className="score-num">{result.technical.score} / 40</span>
                      </div>
                      <ScoreBar value={result.technical.score} max={40} color="var(--success)" />
                      <ul className="reason-list">
                        {result.technical.reasons.map((r, i) => (
                          <li key={i}><ChevronRight size={13} />{r}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {/* Layer 4: Qualitative */}
                  {result.qualitative && (
                    <div className="score-section">
                      <div className="score-section-header">
                        <span>📰 定性・ニュース</span>
                        {result.qualitative.max_score > 0 ? (
                          <span className="score-num">{result.qualitative.score} / {result.qualitative.max_score}</span>
                        ) : (
                          <span className="score-num" style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>スコア対象外</span>
                        )}
                      </div>
                      {result.qualitative.max_score > 0 && <ScoreBar value={result.qualitative.score} max={result.qualitative.max_score} color="var(--warning)" />}
                      <div className="sub-scores" style={{ justifyContent: 'flex-end', marginTop: result.qualitative.max_score > 0 ? 0 : '-0.5rem' }}>
                        <span className="tag" style={{ border: 'none', background: 'rgba(255,255,255,0.1)' }}>分析: {result.qualitative.data_source}</span>
                      </div>
                      <ul className="reason-list">
                        {result.qualitative.reasons.map((r, i) => (
                          <li key={i}><ChevronRight size={13} />{r}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {/* Layer 5: Income (Dividend) */}
                  {result.income && (
                    <div className="score-section" style={{ borderLeft: '4px solid #FCD34D' }}>
                      <div className="score-section-header">
                        <span style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                          <Coins size={16} color="#FCD34D" />
                          配当・インカム
                        </span>
                        <span className="score-num">{result.income.score} / {result.income.max_score}</span>
                      </div>
                      <ScoreBar value={result.income.score} max={result.income.max_score} color="#FCD34D" />
                      <div className="kv-grid">
                        {result.income.dividend_yield != null && <><span>配当利回り</span><span>{result.income.dividend_yield}%</span></>}
                        {result.income.five_year_avg_yield != null && <><span>5年平均利回り</span><span>{result.income.five_year_avg_yield}%</span></>}
                        {result.income.payout_ratio != null && <><span>配当性向</span><span>{result.income.payout_ratio}%</span></>}
                        {result.income.graham_number != null && <><span>グレアム指数</span><span>{result.income.graham_number}</span></>}
                      </div>
                      <ul className="reason-list">
                        {result.income.reasons.map((r, i) => (
                          <li key={i}><ChevronRight size={13} />{r}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {/* Risk Info */}
                  {result.risk && (
                    <div className="risk-section">
                      <span className="metric-title">🛡 リスク管理</span>

                      {result.risk.warnings && result.risk.warnings.length > 0 && (
                        <ul className="reason-list" style={{ marginBottom: '0.75rem', marginTop: '0.5rem' }}>
                          {result.risk.warnings.map((w, i) => (
                            <li key={`risk-warn-${i}`} style={{ color: 'var(--danger)' }}>{w}</li>
                          ))}
                        </ul>
                      )}

                      <div className="kv-grid">
                        {result.risk.liquidity_ok != null && (
                          <>
                            <span>流動性</span>
                            <span style={{ color: result.risk.liquidity_ok ? 'var(--success)' : 'var(--danger)' }}>
                              {result.risk.liquidity_ok ? '✅ 問題なし' : '❌ 低流動性注意'}
                            </span>
                          </>
                        )}
                        {result.risk.trailing_stop_base != null && (
                          <><span>{result.risk.trailing_stop_base_label}</span><span>{result.risk.trailing_stop_base.toLocaleString()}</span></>
                        )}
                        {result.risk.trailing_stop_high != null && (
                          <><span>{result.risk.trailing_stop_high_label}</span><span>{result.risk.trailing_stop_high.toLocaleString()}</span></>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          </>
        )}
      </main>
    </div>
  );
}
