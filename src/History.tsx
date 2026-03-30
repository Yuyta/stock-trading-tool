import React, { useState, useEffect } from 'react';
import {
  ChevronRight, Search, ArrowUpDown, Calendar, Tag, BarChart3,
  ArrowLeft, RefreshCw, AlertCircle, Clock, Trash2
} from 'lucide-react';
import { AnalysisHistory, AnalysisResult } from './types';
import { useAuth } from './AuthContext';

const API_BASE = (import.meta.env.VITE_API_URL as string) || '';

interface HistoryProps {
  onBack: () => void;
  onSelectDetail: (result: AnalysisResult) => void;
}

export const History: React.FC<HistoryProps> = ({ onBack, onSelectDetail }) => {
  const { token } = useAuth();
  const [histories, setHistories] = useState<AnalysisHistory[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isDeleting, setIsDeleting] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [searchSymbol, setSearchSymbol] = useState('');
  const [sortBy, setSortBy] = useState<'created_at' | 'symbol'>('created_at');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');

  const fetchHistories = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const query = new URLSearchParams({
        sort_by: sortBy,
        order: sortOrder,
      });
      if (searchSymbol) query.append('symbol', searchSymbol);

      const resp = await fetch(`${API_BASE}/api/history?${query.toString()}`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      if (!resp.ok) throw new Error('履歴の取得に失敗しました');
      const data = await resp.json();
      setHistories(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : '通信エラー');
    } finally {
      setIsLoading(false);
    }
  };

  const handleDelete = async (e: React.MouseEvent, id: number) => {
    e.stopPropagation(); // 親の onClick (詳細表示) を発火させない
    
    if (!window.confirm('この履歴を削除してもよろしいですか？')) {
      return;
    }

    setIsDeleting(id);
    try {
      const resp = await fetch(`${API_BASE}/api/history/${id}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      if (!resp.ok) throw new Error('削除に失敗しました');
      
      // 成功したらリストから除外
      setHistories(prev => prev.filter(h => h.id !== id));
    } catch (err) {
      alert(err instanceof Error ? err.message : '削除エラーが発生しました');
    } finally {
      setIsDeleting(null);
    }
  };

  useEffect(() => {
    if (token) fetchHistories();
  }, [token, sortBy, sortOrder]);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    fetchHistories();
  };

  const toggleSort = (field: 'created_at' | 'symbol') => {
    if (sortBy === field) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
    } else {
      setSortBy(field);
      setSortOrder('desc');
    }
  };

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleString('ja-JP', {
      year: 'numeric', month: '2-digit', day: '2-digit',
      hour: '2-digit', minute: '2-digit'
    });
  };

  const getSignalColor = (signal: string) => {
    if (signal.startsWith('Strong Buy')) return 'var(--success)';
    if (signal.startsWith('Buy')) return '#34d399';
    if (signal.startsWith('Hold')) return 'var(--warning)';
    if (signal.startsWith('Sell') || signal === '見送り') return 'var(--danger)';
    return 'var(--text-secondary)';
  };

  return (
    <div className="history-container animate-slide-in">
      <div className="card glass-panel">
        <div className="card-header" style={{ justifyContent: 'space-between' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <button className="button secondary icon-only" onClick={onBack} title="戻る">
              <ArrowLeft size={18} />
            </button>
            <Clock className="card-icon" />
            <span>判定履歴</span>
          </div>
          <button className="button secondary" onClick={fetchHistories} disabled={isLoading}>
            <RefreshCw size={16} className={isLoading ? 'spin' : ''} />
            <span>更新</span>
          </button>
        </div>

        {/* Search & Sort Controls */}
        <div className="history-controls">
          <form onSubmit={handleSearch} className="search-box">
            <div className="search-input-wrapper">
              <Search size={18} className="search-icon" />
              <input
                type="text"
                placeholder="銘柄コードや企業名で検索..."
                value={searchSymbol}
                onChange={(e) => setSearchSymbol(e.target.value)}
              />
            </div>
            <button type="submit" className="button small" disabled={isLoading}>検索</button>
          </form>

          <div className="sort-buttons">
            <button
              className={`sort-tab ${sortBy === 'created_at' ? 'active' : ''}`}
              onClick={() => toggleSort('created_at')}
            >
              <Calendar size={14} />
              分析日時
              {sortBy === 'created_at' && <ArrowUpDown size={12} className={sortOrder} />}
            </button>
            <button
              className={`sort-tab ${sortBy === 'symbol' ? 'active' : ''}`}
              onClick={() => toggleSort('symbol')}
            >
              <Tag size={14} />
              銘柄
              {sortBy === 'symbol' && <ArrowUpDown size={12} className={sortOrder} />}
            </button>
          </div>
        </div>

        {/* History List */}
        <div className="history-list">
          {isLoading && histories.length === 0 ? (
            <div className="empty-state">
              <div className="spinner" />
              <p>履歴を読み込み中...</p>
            </div>
          ) : error ? (
            <div className="alert-box danger">
              <AlertCircle size={16} />
              <span>{error}</span>
            </div>
          ) : histories.length === 0 ? (
            <div className="empty-state">
              <BarChart3 size={48} style={{ opacity: 0.3, marginBottom: '1rem' }} />
              <p>履歴がありません。<br />分析を実行して結果を保存しましょう。</p>
            </div>
          ) : (
            histories.map((item) => (
              <div
                key={item.id}
                className="history-item glass-panel hover-effect"
                onClick={() => onSelectDetail(JSON.parse(item.result_json))}
              >
                <div className="history-item-main">
                  <div className="history-item-info">
                    <div className="history-item-top">
                      <div className="history-symbol-row">
                        <span className="history-symbol">{item.symbol}</span>
                        {item.symbol_name && (
                          <span className="history-company-name">{item.symbol_name}</span>
                        )}
                      </div>
                      <span className="history-date">{formatDate(item.created_at)}</span>
                    </div>
                    <div className="history-item-details">
                      <span className="tag">{item.trade_style === 'long_hold' ? '長期' : item.trade_style === 'day' ? '短期' : '中長期'}</span>
                      <span className="tag">{item.analysis_mode}</span>
                    </div>
                  </div>
                  <div className="history-item-result">
                    <div className="history-signal" style={{ color: getSignalColor(item.signal) }}>
                      {item.signal}
                    </div>
                    {item.total_score != null && (
                      <div className="history-score">
                        {item.total_score} / {item.max_score}
                      </div>
                    )}
                  </div>
                </div>
                
                <div className="history-actions">
                  <button 
                    className="button secondary icon-only delete-button"
                    onClick={(e) => handleDelete(e, item.id)}
                    disabled={isDeleting === item.id}
                    title="削除"
                  >
                    {isDeleting === item.id ? (
                      <RefreshCw size={18} className="spin" />
                    ) : (
                      <Trash2 size={18} />
                    )}
                  </button>
                  <ChevronRight size={20} className="history-arrow" />
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
};
