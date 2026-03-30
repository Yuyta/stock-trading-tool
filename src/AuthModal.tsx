import React, { useState } from 'react';
import { useAuth } from './AuthContext';
import { LogIn, UserPlus, X, RefreshCw, AlertCircle } from 'lucide-react';

interface AuthModalProps {
  onClose: () => void;
}

const API_BASE = (import.meta.env.VITE_API_URL as string) || 'http://localhost:8000';

export function AuthModal({ onClose }: AuthModalProps) {
  const { login: setAuth } = useAuth();
  const [isLogin, setIsLogin] = useState(true);
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError(null);

    const endpoint = isLogin ? '/api/login' : '/api/signup';
    const payload = { username, password };

    try {
      const resp = await fetch(`${API_BASE}${endpoint}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      if (!resp.ok) {
        const data = await resp.json();
        throw new Error(data.detail || (isLogin ? 'ログインに失敗しました' : 'サインアップに失敗しました'));
      }

      if (isLogin) {
        const { access_token } = await resp.json();
        // Get user info after login
        const meResp = await fetch(`${API_BASE}/api/me`, {
          headers: { 'Authorization': `Bearer ${access_token}` }
        });
        const user = await meResp.json();
        setAuth(access_token, user);
        onClose();
      } else {
        // After signup, switch to login
        setIsLogin(true);
        alert('サインアップが完了しました。ログインしてください。');
      }
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'エラーが発生しました');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="modal-overlay">
      <div className="settings-modal auth-modal animate-slide-in">
        <div className="modal-header">
          <div className="header-title">
            {isLogin ? <LogIn size={20} /> : <UserPlus size={20} />}
            <span>{isLogin ? 'ログイン' : 'サインアップ'}</span>
          </div>
          <button className="close-button" onClick={onClose}><X size={20} /></button>
        </div>

        <form onSubmit={handleSubmit} className="modal-body">
          {error && (
            <div className="alert-box danger" style={{ marginBottom: '1rem' }}>
              <AlertCircle size={16} />
              <span>{error}</span>
            </div>
          )}

          <div className="input-group">
            <label className="input-label">ユーザー名</label>
            <input
              type="text"
              className="input"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
              autoComplete="username"
            />
          </div>

          <div className="input-group">
            <label className="input-label">パスワード</label>
            <input
              type="password"
              className="input"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              autoComplete={isLogin ? "current-password" : "new-password"}
            />
          </div>

          <button
            type="submit"
            className="button"
            disabled={isLoading}
            style={{ width: '100%', marginTop: '1rem' }}
          >
            {isLoading ? (
              <><RefreshCw size={20} className="spin" /> 実行中...</>
            ) : (
              isLogin ? 'ログイン' : 'アカウント作成'
            )}
          </button>

          <div style={{ textAlign: 'center', marginTop: '1.5rem', fontSize: '0.9rem', color: 'var(--text-muted)' }}>
            {isLogin ? (
              <>
                アカウントをお持ちでないですか？{' '}
                <button type="button" className="text-button" onClick={() => setIsLogin(false)} style={{ color: 'var(--accent-primary)', textDecoration: 'underline' }}>
                  新規登録
                </button>
              </>
            ) : (
              <>
                既にアカウントをお持ちですか？{' '}
                <button type="button" className="text-button" onClick={() => setIsLogin(true)} style={{ color: 'var(--accent-primary)', textDecoration: 'underline' }}>
                  ログイン
                </button>
              </>
            )}
          </div>
        </form>
      </div>
    </div>
  );
}
