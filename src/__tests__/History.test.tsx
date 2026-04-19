import { render, screen, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { History } from '../History';
import * as AuthContext from '../AuthContext';

// AuthContextのモック
vi.mock('../AuthContext', () => ({
  useAuth: vi.fn(),
}));

// Fetchのモック
global.fetch = vi.fn();

describe('History Component', () => {
  const mockOnBack = vi.fn();
  const mockOnSelectDetail = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    (AuthContext.useAuth as any).mockReturnValue({
      token: 'fake-token',
    });
  });

  it('renders history items when fetched successfully', async () => {
    const mockHistories = [
      {
        id: '1',
        symbol: '7203.T',
        symbol_name: 'Toyota Motor',
        trade_style: 'swing',
        signal: 'Buy',
        total_score: 65,
        max_score: 100,
        analysis_mode: '標準モード',
        created_at: '2024-04-18T10:00:00Z',
        result_json: JSON.stringify({ symbol: '7203.T', signal: 'Buy' })
      }
    ];

    (global.fetch as any).mockResolvedValue({
      ok: true,
      json: async () => mockHistories,
    });

    render(<History onBack={mockOnBack} onSelectDetail={mockOnSelectDetail} />);

    expect(screen.getByText('判定履歴')).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText('7203.T')).toBeInTheDocument();
      expect(screen.getByText('Toyota Motor')).toBeInTheDocument();
      expect(screen.getByText('Buy')).toBeInTheDocument();
    });
  });

  it('shows empty state when no histories found', async () => {
    (global.fetch as any).mockResolvedValue({
      ok: true,
      json: async () => [],
    });

    render(<History onBack={mockOnBack} onSelectDetail={mockOnSelectDetail} />);

    await waitFor(() => {
      expect(screen.getByText(/履歴がありません/)).toBeInTheDocument();
    });
  });

  it('shows error message when fetch fails', async () => {
    (global.fetch as any).mockResolvedValue({
      ok: false,
    });

    render(<History onBack={mockOnBack} onSelectDetail={mockOnSelectDetail} />);

    await waitFor(() => {
      expect(screen.getByText('履歴の取得に失敗しました')).toBeInTheDocument();
    });
  });
});
