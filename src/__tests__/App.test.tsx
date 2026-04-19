import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import App from '../App';
import * as AuthContext from '../AuthContext';

// AuthContextのモック
vi.mock('../AuthContext', () => ({
  useAuth: vi.fn(),
  AuthProvider: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
}));

// Fetchのモック
global.fetch = vi.fn();

describe('App Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (AuthContext.useAuth as any).mockReturnValue({
      user: null,
      token: null,
      logout: vi.fn(),
    });

    (global.fetch as any).mockResolvedValue({
      ok: true,
      json: async () => ({ status: 'ok' }),
    });
  });

  it('renders correctly and shows health status', async () => {
    render(<App />);
    
    expect(screen.getByText('TradeAlgo Pro')).toBeInTheDocument();
    
    // ヘルスチェックの確認
    await waitFor(() => {
      expect(screen.getByText('API未設定')).toBeInTheDocument();
    });
  });

  it('updates symbol input on change', () => {
    render(<App />);
    const input = screen.getByPlaceholderText('例: Sony, 7203, AAPL');
    fireEvent.change(input, { target: { value: 'AAPL' } });
    expect((input as HTMLInputElement).value).toBe('AAPL');
  });

  it('starts analysis when button is clicked', async () => {
    const mockResult = {
      symbol: 'AAPL',
      signal: 'Buy',
      trade_style: 'swing',
      total_score: 70,
      max_score: 100,
      analysis_mode: '標準モード',
      macro: { passed: true, vix_mode: 'normal' },
      chart_data: [],
    };

    (global.fetch as any).mockImplementation((url: string) => {
      if (url.includes('/api/analyze')) {
        return Promise.resolve({
          ok: true,
          json: async () => mockResult,
        });
      }
      return Promise.resolve({
        ok: true,
        json: async () => ({ results: [] }),
      });
    });

    render(<App />);
    const input = screen.getByPlaceholderText('例: Sony, 7203, AAPL');
    fireEvent.change(input, { target: { value: 'AAPL' } });
    
    const analyzeButton = screen.getByText('自動判定を開始');
    fireEvent.click(analyzeButton);

    await waitFor(() => {
      expect(screen.getByText('Buy')).toBeInTheDocument();
    });
  });
});
