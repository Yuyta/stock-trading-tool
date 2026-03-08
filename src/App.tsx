import { useState, useEffect } from 'react';
import {
  Activity, BarChart3, Settings as SettingsIcon, PlayCircle, RefreshCw,
  TrendingUp, TrendingDown, Minus, ShieldCheck, ShieldAlert, ShieldX,
  AlertCircle, ChevronRight, Server
} from 'lucide-react';
import {
  ResponsiveContainer, AreaChart, Area, XAxis, YAxis, Tooltip, CartesianGrid
} from 'recharts';
import { AnalysisResult, AppSettings } from './types';
import { SettingsModal } from './SettingsModal';
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

export default function App() {
  const [symbol, setSymbol] = useState('AAPL');
  const [timeframe, setTimeframe] = useState('1d');
  const [tradeStyle, setTradeStyle] = useState('swing');
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showSettings, setShowSettings] = useState(false);
  const [settings, setSettings] = useState<AppSettings>(loadSettings);
  const [backendOnline, setBackendOnline] = useState<boolean | null>(null);

  useEffect(() => {
    fetch('/api/health')
      .then(r => r.ok ? setBackendOnline(true) : setBackendOnline(false))
      .catch(() => setBackendOnline(false));
  }, []);

  const handleSaveSettings = (s: AppSettings) => {
    setSettings(s);
    saveSettings(s);
  };

  const handleAnalyze = async () => {
    if (!symbol.trim()) return;
    setIsAnalyzing(true);
    setResult(null);
    setError(null);

    try {
      const resp = await fetch('/api/analyze', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          symbol: symbol.trim().toUpperCase(),
          timeframe,
          trade_style: tradeStyle,
          jquants_refresh_token: settings.jquantsRefreshToken || undefined,
          gemini_api_key: settings.geminiApiKey || undefined,
        }),
      });
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const data: AnalysisResult = await resp.json();
      setResult(data);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : '通信エラー');
    } finally {
      setIsAnalyzing(false);
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

      <header className="header glass-panel animate-slide-in">
        <div className="header-title">
          <Activity className="logo-icon" />
          <span>TradeAlgo Pro</span>
        </div>
        <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center' }}>
          {/* API Connectivity Status */}
          <div className={`backend-badge ${backendOnline === true ? 'online' : backendOnline === false ? 'offline' : 'checking'}`}>
            <Server size={14} />
            <span>
              {backendOnline === true ? (
                <>
                  {settings.jquantsRefreshToken && settings.geminiApiKey ? 'J-Quants + Gemini 接続中' :
                    settings.jquantsRefreshToken ? 'J-Quants 接続中' :
                      settings.geminiApiKey ? 'Gemini 接続中' :
                        'API接続済み (キー未設定)'}
                </>
              ) : backendOnline === false ? 'サーバー未起動' : '接続確認中'}
            </span>
          </div>
          {(!settings.jquantsRefreshToken && !settings.geminiApiKey && backendOnline === true) && (
            <div className="backend-badge offline" style={{ background: 'rgba(239, 68, 68, 0.1)', color: '#ef4444' }}>
              <AlertCircle size={14} />
              <span>APIキー未設定</span>
            </div>
          )}
          <button className="button secondary" onClick={() => setShowSettings(true)}>
            <SettingsIcon size={18} />
            <span>設定</span>
          </button>
        </div>
      </header>

      <main className="main-content">
        {/* Left column */}
        <div>
          <div className="card glass-panel animate-slide-in">
            <div className="card-header">
              <BarChart3 className="card-icon" />
              <span>分析対象</span>
            </div>
            <div className="input-row">
              <div className="input-group" style={{ flex: 2 }}>
                <span className="input-label">銘柄コード / シンボル</span>
                <input
                  type="text"
                  className="input"
                  value={symbol}
                  onChange={(e) => setSymbol(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleAnalyze()}
                  placeholder="例: AAPL, 7203, MSFT"
                />
              </div>
              <div className="input-group" style={{ flex: 2 }}>
                <span className="input-label">トレードスタイル</span>
                <select className="input" value={tradeStyle} onChange={(e) => {
                  setTradeStyle(e.target.value);
                  if (e.target.value === 'day' && timeframe === '1d') {
                    setTimeframe('5m');
                  }
                }}>
                  <option value="swing">中長期投資 (スイング)</option>
                  <option value="day">短期・デイトレード</option>
                </select>
              </div>
              <div className="input-group" style={{ flex: 1 }}>
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
              onClick={handleAnalyze}
              disabled={isAnalyzing || !symbol || backendOnline === false}
              style={{ padding: '1rem', fontSize: '1rem' }}
            >
              {isAnalyzing ? (
                <><RefreshCw size={20} style={{ animation: 'spin 1s linear infinite' }} />分析中...</>
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

          {/* Chart */}
          <div className="card glass-panel" style={{ marginTop: '1.5rem' }}>
            <div className="card-header">
              <Activity className="card-icon" />
              <span>価格チャート（参考）</span>
            </div>
            <div className="chart-placeholder" style={{ height: '220px', padding: '10px 0', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              {result?.chart_data && result.chart_data.length > 0 ? (
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={result.chart_data} margin={{ top: 5, right: 0, left: -20, bottom: 0 }}>
                    <defs>
                      <linearGradient id="colorPrice" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor={getSignalColor(result.signal)} stopOpacity={0.5} />
                        <stop offset="95%" stopColor={getSignalColor(result.signal)} stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" vertical={false} />
                    <XAxis
                      dataKey="time"
                      tick={{ fill: 'var(--text-muted)', fontSize: 11 }}
                      tickLine={false}
                      axisLine={false}
                      minTickGap={20}
                    />
                    <YAxis
                      domain={['auto', 'auto']}
                      tick={{ fill: 'var(--text-muted)', fontSize: 11 }}
                      tickLine={false}
                      axisLine={false}
                      tickFormatter={(val) => val.toLocaleString()}
                    />
                    <Tooltip
                      contentStyle={{ backgroundColor: 'rgba(15, 23, 42, 0.9)', borderColor: 'rgba(255,255,255,0.1)', color: 'white' }}
                      itemStyle={{ color: 'var(--accent-primary)' }}
                      labelStyle={{ color: 'var(--text-muted)' }}
                    />
                    <Area type="monotone" dataKey="price" stroke={getSignalColor(result.signal)} fillOpacity={1} fill="url(#colorPrice)" />
                  </AreaChart>
                </ResponsiveContainer>
              ) : (
                <div style={{ color: 'var(--text-muted)' }}>
                  チャートデータがありません（判定を実行してください）
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
                  <span className="metric-title">5日EMA</span>
                  <span className="metric-value">{result.technical.ema5?.toLocaleString() ?? '—'}</span>
                </div>
                <div className="metric-card">
                  <span className="metric-title">出来高比</span>
                  <span className="metric-value">{result.technical.volume_ratio != null ? `${result.technical.volume_ratio}x` : '—'}</span>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Right column: Results */}
        <div className="card glass-panel result-panel">
          <div className="card-header">
            <AlertCircle className="card-icon" />
            <span>AI 判定結果</span>
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
              <div className="layer-details">
                {result.macro.vix != null && <span className="tag">VIX: {result.macro.vix}</span>}
                {result.macro.oil_sigma != null && <span className="tag">原油σ: {result.macro.oil_sigma}</span>}
                {result.macro.gold_sigma != null && <span className="tag">金σ: {result.macro.gold_sigma}</span>}
                {result.macro.commodity_alert && <span className="tag danger-tag">コモディティ急騰 ⚠️</span>}
              </div>

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

              {/* Qualitative */}
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

              {/* Risk Info */}
              {result.risk && (
                <div className="risk-section">
                  <span className="metric-title">🛡 リスク管理</span>
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
      </main>
    </div>
  );
}
