import { useState } from 'react';
import { Settings, X, Key, ExternalLink, AlertCircle } from 'lucide-react';
import { AppSettings } from './types';

interface Props {
    settings: AppSettings;
    onSave: (s: AppSettings) => void;
    onClose: () => void;
}

export function SettingsModal({ settings, onSave, onClose }: Props) {
    const [local, setLocal] = useState<AppSettings>({ ...settings });

    return (
        <div className="modal-overlay" onClick={onClose}>
            <div className="modal-panel glass-panel" onClick={(e) => e.stopPropagation()}>
                <div className="modal-header">
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                        <Settings size={20} style={{ color: 'var(--accent-primary)' }} />
                        <span>API キー設定</span>
                    </div>
                    <button className="icon-btn" onClick={onClose}><X size={20} /></button>
                </div>

                <div className="modal-body">
                    <div className="settings-notice">
                        <AlertCircle size={16} />
                        <span>APIキーはブラウザのLocalStorageに保存されます。サーバーには送信しません。</span>
                    </div>

                    <div className="input-group">
                        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                            <span className="input-label">
                                <Key size={14} style={{ display: 'inline', marginRight: '6px', verticalAlign: 'middle' }} />
                                J-Quants リフレッシュトークン
                            </span>
                            <a
                                href="https://jpx-jquants.com/"
                                target="_blank"
                                rel="noopener noreferrer"
                                className="settings-link"
                            >
                                取得する <ExternalLink size={12} />
                            </a>
                        </div>
                        <input
                            type="password"
                            className="input"
                            placeholder="日本株ファンダメンタル取得に必要"
                            value={local.jquantsRefreshToken}
                            onChange={(e) => setLocal({ ...local, jquantsRefreshToken: e.target.value })}
                        />
                        <span className="input-hint">未設定の場合、日本株のPER/PBR/ROEは取得できません</span>
                    </div>

                    <div className="input-group">
                        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                            <span className="input-label">
                                <Key size={14} style={{ display: 'inline', marginRight: '6px', verticalAlign: 'middle' }} />
                                Google Gemini API キー
                            </span>
                            <a
                                href="https://aistudio.google.com/app/apikey"
                                target="_blank"
                                rel="noopener noreferrer"
                                className="settings-link"
                            >
                                取得する <ExternalLink size={12} />
                            </a>
                        </div>
                        <input
                            type="password"
                            className="input"
                            placeholder="ニュース定性分析（AI）に使用"
                            value={local.geminiApiKey}
                            onChange={(e) => setLocal({ ...local, geminiApiKey: e.target.value })}
                        />
                        <span className="input-hint">未設定の場合、キーワードベースの簡易分析になります</span>
                    </div>
                </div>

                <div className="modal-footer">
                    <button className="button secondary" onClick={onClose}>キャンセル</button>
                    <button
                        className="button"
                        onClick={() => { onSave(local); onClose(); }}
                    >
                        保存
                    </button>
                </div>
            </div>
        </div>
    );
}
