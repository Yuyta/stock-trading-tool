import { useState, useEffect } from 'react';
import { 
  BarChart3, 
  TrendingUp, 
  TrendingDown, 
  Activity, 
  Settings,
  AlertCircle,
  PlayCircle,
  ChevronRight,
  RefreshCw
} from 'lucide-react';
import './App.css';

type Signal = 'BUY' | 'SELL' | 'HOLD' | null;

interface AnalysisResult {
  signal: Signal;
  confidence: number;
  reasons: { type: 'pro' | 'con'; text: string }[];
  metrics: {
    rsi: number;
    macd: number;
    volume: string;
  };
}

function App() {
  const [symbol, setSymbol] = useState('AAPL');
  const [timeframe, setTimeframe] = useState('1D');
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [result, setResult] = useState<AnalysisResult | null>(null);

  // Mock chart data state
  const [bars, setBars] = useState<number[]>([]);

  useEffect(() => {
    // Generate random mock chart bars
    setBars(Array.from({ length: 24 }, () => Math.floor(Math.random() * 60) + 20));
  }, [symbol]);

  const handleAnalyze = () => {
    if (!symbol.trim()) return;
    
    setIsAnalyzing(true);
    setResult(null);

    // Simulate analysis delay
    setTimeout(() => {
      const signals: Signal[] = ['BUY', 'SELL', 'HOLD'];
      const randomSignal = signals[Math.floor(Math.random() * signals.length)];
      
      const mockResult: AnalysisResult = {
        signal: randomSignal,
        confidence: Math.floor(Math.random() * 30) + 60, // 60-90%
        reasons: [
          { type: 'pro', text: '移動平均線(MA) ゴールデンクロス形成' },
          { type: 'con', text: 'RSIが買われすぎ水準(70以上)に接近' },
          { type: 'pro', text: '直近決算でのポジティブサプライズ' }
        ],
        metrics: {
          rsi: Math.floor(Math.random() * 80) + 10,
          macd: Number((Math.random() * 4 - 2).toFixed(2)),
          volume: (Math.random() * 10 + 1).toFixed(1) + 'M'
        }
      };
      
      setResult(mockResult);
      setIsAnalyzing(false);
      
      // Update chart bars to show "movement"
      setBars(Array.from({ length: 24 }, () => Math.floor(Math.random() * 60) + 20));
    }, 1500);
  };

  const getSignalColor = (signal: Signal) => {
    if (signal === 'BUY') return 'var(--success)';
    if (signal === 'SELL') return 'var(--danger)';
    if (signal === 'HOLD') return 'var(--warning)';
    return 'currentColor';
  };

  return (
    <div className="app-container">
      <header className="header glass-panel animate-slide-in">
        <div className="header-title">
          <Activity className="logo-icon" />
          <span>TradeAlgo Pro</span>
        </div>
        <button className="button secondary">
          <Settings size={18} />
          <span>設定</span>
        </button>
      </header>

      <main className="main-content">
        {/* Left Column: Data & Input */}
        <div className="column column-left">
          <div className="card glass-panel" style={{ animationDelay: '0.1s' }}>
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
                  placeholder="例: AAPL, 7203" 
                />
              </div>
              <div className="input-group" style={{ flex: 1 }}>
                <span className="input-label">時間軸</span>
                <select 
                  className="input"
                  value={timeframe}
                  onChange={(e) => setTimeframe(e.target.value)}
                >
                  <option value="1H">1時間足</option>
                  <option value="1D">日足</option>
                  <option value="1W">週足</option>
                </select>
              </div>
            </div>

            <button 
              className="button" 
              onClick={handleAnalyze} 
              disabled={isAnalyzing || !symbol}
              style={{ padding: '1rem', marginTop: '0.5rem', fontSize: '1rem' }}
            >
              {isAnalyzing ? (
                <>
                  <RefreshCw size={20} className="spinner" style={{ width: 20, height: 20, border: 'none', animation: 'spin 1s linear infinite' }} />
                  分析中...
                </>
              ) : (
                <>
                  <PlayCircle size={20} />
                  自動判定を開始
                </>
              )}
            </button>
          </div>

          <div className="card glass-panel" style={{ marginTop: '2rem', animationDelay: '0.2s' }}>
            <div className="card-header">
              <Activity className="card-icon" />
              <span>チャートシミュレーション</span>
            </div>
            <div className="chart-placeholder">
              <div className="chart-bars">
                {bars.map((height, i) => (
                  <div 
                    key={i} 
                    className="chart-bar" 
                    style={{ 
                      height: `${height}%`,
                      background: i === bars.length - 1 ? (result ? getSignalColor(result.signal) : 'var(--accent-primary)') : 'var(--accent-primary)',
                      opacity: i === bars.length - 1 ? 0.8 : 0.2
                    }} 
                  />
                ))}
              </div>
            </div>
            
            <div className="metric-grid">
              <div className="metric-card">
                <span className="metric-title">現在値 (Mock)</span>
                <span className="metric-value">1,492.5</span>
              </div>
              <div className="metric-card">
                <span className="metric-title">24h 変動</span>
                <div className="metric-status status-buy">
                  <TrendingUp size={16} />
                  <span>+2.4%</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Right Column: Judgment Result */}
        <div className="column column-right">
          <div className="card glass-panel" style={{ height: '100%', animationDelay: '0.3s' }}>
            <div className="card-header">
              <AlertCircle className="card-icon" />
              <span>AI 判定結果</span>
            </div>

            <div className="judgment-area">
              {isAnalyzing && (
                <div className="loading-overlay">
                  <div className="spinner" />
                </div>
              )}

              {!result && !isAnalyzing && (
                <div style={{ color: 'var(--text-muted)' }}>
                  <BarChart3 size={48} style={{ opacity: 0.5, marginBottom: '1rem' }} />
                  <p>「自動判定を開始」をクリックして<br/>分析を実行してください</p>
                </div>
              )}

              {result && !isAnalyzing && (
                <>
                  <div>
                    <span className="metric-title" style={{ letterSpacing: '2px' }}>総合判定</span>
                    <div className={`big-signal signal-${result.signal} animate-slide-in`} style={{ color: getSignalColor(result.signal) }}>
                      {result.signal === 'BUY' && <TrendingUp size={64} />}
                      {result.signal === 'SELL' && <TrendingDown size={64} />}
                      {result.signal === 'HOLD' && <Activity size={64} />}
                      {result.signal}
                    </div>
                  </div>

                  <div className="metric-grid" style={{ width: '100%', marginTop: '1rem' }}>
                    <div className="metric-card">
                      <span className="metric-title">確信度</span>
                      <span className="metric-value">{result.confidence}%</span>
                    </div>
                    <div className="metric-card">
                      <span className="metric-title">RSI (14)</span>
                      <span className="metric-value">{result.metrics.rsi}</span>
                    </div>
                    <div className="metric-card">
                      <span className="metric-title">MACD</span>
                      <span className="metric-value">{result.metrics.macd}</span>
                    </div>
                  </div>

                  <div style={{ width: '100%', marginTop: '1rem' }}>
                    <span className="metric-title" style={{ display: 'block', marginBottom: '1rem', textAlign: 'left' }}>主な判定理由</span>
                    <ul className="reasoning-list">
                      {result.reasons.map((reason, i) => (
                        <li key={i} className={`reasoning-item animate-slide-in ${reason.type}`} style={{ animationDelay: `${0.2 + i * 0.1}s` }}>
                          <ChevronRight size={16} style={{ marginTop: '2px' }} />
                          <span>{reason.text}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                </>
              )}
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}

export default App;
