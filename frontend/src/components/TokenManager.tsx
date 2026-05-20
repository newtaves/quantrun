import React, { useState, useEffect } from 'react';
import { DJANGO_API_URL } from '../config';
import { Key, Plus, Trash2, CheckCircle, Clock } from 'lucide-react';

interface Token {
  id: number;
  token: string;
  created_at: string;
  expires_at: string;
  is_active: boolean;
}

interface TokenManagerProps {
  token: string;
}

export const TokenManager: React.FC<TokenManagerProps> = ({ token }) => {
  const [tokens, setTokens] = useState<Token[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [isGenerating, setIsGenerating] = useState<boolean>(false);
  const [newlyCreatedToken, setNewlyCreatedToken] = useState<string | null>(null);

  const fetchTokens = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const resp = await fetch(`${DJANGO_API_URL}/api/tokens/`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (!resp.ok) throw new Error('Failed to fetch API credentials');
      const data = await resp.json();
      setTokens(data.tokens || []);
    } catch (e: any) {
      setError(e.message || 'Error fetching credentials');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchTokens();
  }, []);

  const handleGenerateToken = async () => {
    setIsGenerating(true);
    setNewlyCreatedToken(null);
    try {
      const resp = await fetch(`${DJANGO_API_URL}/api/tokens/generate/`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` }
      });
      const data = await resp.json();
      if (resp.ok) {
        setNewlyCreatedToken(data.token);
        fetchTokens();
      } else {
        alert(data.detail || 'Failed to generate token');
      }
    } catch (e) {
      alert('Network error generating token');
    } finally {
      setIsGenerating(false);
    }
  };

  const handleRevokeToken = async (tokenId: number) => {
    if (!window.confirm('REVOKE TOKEN? Any active automated bot using this key will immediately be terminated.')) {
      return;
    }
    
    try {
      const resp = await fetch(`${DJANGO_API_URL}/api/tokens/${tokenId}/revoke/`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (resp.ok) {
        fetchTokens();
      } else {
        const data = await resp.json();
        alert(data.detail || 'Failed to revoke token');
      }
    } catch (e) {
      alert('Error revoking token');
    }
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    alert('TOKEN COPIED TO CLIPBOARD!');
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      <div>
        <h2 style={{ fontSize: '1.4rem', fontWeight: 700, color: 'var(--text-primary)' }}>
          API KEY DEPLOYMENT CENTER
        </h2>
        <p style={{ color: 'var(--text-secondary)', fontSize: '0.8rem', marginTop: '4px', fontFamily: 'JetBrains Mono, monospace' }}>
          Generate stateless credential keys to connect external strategy scripts directly to the paper execution matching engine.
        </p>
      </div>

      {newlyCreatedToken && (
        <div style={{
          padding: '16px',
          background: 'rgba(0, 255, 0, 0.04)',
          border: '1px solid var(--success)',
        }}>
          <h4 style={{ color: 'var(--success)', display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.85rem', fontWeight: 700, fontFamily: 'JetBrains Mono, monospace' }}>
            <CheckCircle size={16} /> [KEY_GENERATED_SUCCESSFULLY]
          </h4>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.75rem', margin: '6px 0 12px' }}>
            Copy this token now! It is stored hashed in SQLite and cannot be retrieved again once you exit this screen.
          </p>
          <div style={{ display: 'flex', gap: '10px' }}>
            <input
              type="text"
              readOnly
              value={newlyCreatedToken}
              onClick={(e) => (e.target as HTMLInputElement).select()}
              style={{
                flex: 1,
                background: 'var(--bg-color)',
                border: '1px solid var(--panel-border)',
                padding: '8px 12px',
                color: 'var(--text-primary)',
                fontFamily: 'JetBrains Mono, monospace',
                fontSize: '0.8rem'
              }}
            />
            <button
              onClick={() => copyToClipboard(newlyCreatedToken)}
              className="btn btn-primary"
              style={{ padding: '8px 16px', fontSize: '0.75rem' }}
            >
              COPY
            </button>
          </div>
        </div>
      )}

      <div className="glass-panel" style={{ padding: '20px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
          <h3 style={{ fontSize: '0.85rem', fontWeight: 700, fontFamily: 'JetBrains Mono, monospace' }}>ACTIVE CREDENTIALS</h3>
          <button
            onClick={handleGenerateToken}
            disabled={isGenerating}
            className="btn btn-primary"
            style={{ padding: '6px 12px', fontSize: '0.75rem' }}
          >
            <Plus size={14} />
            {isGenerating ? 'GENERATING...' : 'GENERATE KEY'}
          </button>
        </div>

        {isLoading ? (
          <div style={{ textAlign: 'center', padding: '24px', color: 'var(--text-muted)', fontSize: '0.78rem', fontFamily: 'JetBrains Mono, monospace' }}>
            SYNCHRONIZING SECURE KEYSTORE...
          </div>
        ) : error ? (
          <div style={{ color: 'var(--danger)', fontSize: '0.78rem', padding: '10px 0', fontFamily: 'JetBrains Mono, monospace' }}>
            ERROR: {error}
          </div>
        ) : tokens.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '32px', color: 'var(--text-muted)', fontSize: '0.8rem', fontFamily: 'JetBrains Mono, monospace' }}>
            NO PROGRAMMATIC CREDENTIALS DEPLOYED.
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            {tokens.map((t) => (
              <div
                key={t.id}
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  padding: '12px 16px',
                  background: 'transparent',
                  border: '1px solid var(--panel-border)',
                  opacity: t.is_active ? 1 : 0.4
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                  <div style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    width: '32px',
                    height: '32px',
                    border: '1px solid var(--panel-border)',
                    background: t.is_active ? 'var(--panel-hover)' : 'transparent',
                    color: t.is_active ? 'var(--text-primary)' : 'var(--text-muted)'
                  }}>
                    <Key size={14} />
                  </div>
                  <div>
                    <div style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '0.8rem', color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: '8px' }}>
                      KEY #{t.id}{' '}
                      <span className={`badge ${t.is_active ? 'badge-buy' : 'badge-sell'}`} style={{ padding: '1px 6px', fontSize: '0.6rem' }}>
                        {t.is_active ? 'ACTIVE' : 'REVOKED'}
                      </span>
                    </div>
                    <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)', marginTop: '4px', display: 'flex', alignItems: 'center', gap: '4px', fontFamily: 'JetBrains Mono, monospace' }}>
                      <Clock size={10} />
                      IAT: {new Date(t.created_at).toLocaleDateString()} | EXP: {new Date(t.expires_at).toLocaleDateString()}
                    </div>
                  </div>
                </div>

                {t.is_active && (
                  <button
                    onClick={() => handleRevokeToken(t.id)}
                    style={{
                      background: 'rgba(255, 56, 56, 0.08)',
                      border: '1px solid var(--danger)',
                      padding: '6px',
                      color: 'var(--danger)',
                      cursor: 'pointer',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      transition: 'all 0.1s'
                    }}
                    title="Revoke Token"
                  >
                    <Trash2 size={14} />
                  </button>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
