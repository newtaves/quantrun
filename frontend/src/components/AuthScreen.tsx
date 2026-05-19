import React, { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { Lock, User, TrendingUp, AlertTriangle } from 'lucide-react';

export const AuthScreen: React.FC = () => {
  const { login, signup, error, clearError } = useAuth();
  const [isLoginMode, setIsLoginMode] = useState<boolean>(true);
  const [username, setUsername] = useState<string>('');
  const [password, setPassword] = useState<string>('');
  const [confirmPassword, setConfirmPassword] = useState<string>('');
  const [localError, setLocalError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLocalError(null);
    clearError();

    const trimmedUser = username.trim();
    const trimmedPass = password.trim();

    if (!trimmedUser || !trimmedPass) {
      setLocalError('Please fill in all fields.');
      return;
    }

    if (!isLoginMode && trimmedPass !== confirmPassword.trim()) {
      setLocalError('Passwords do not match.');
      return;
    }

    setIsSubmitting(true);
    try {
      if (isLoginMode) {
        await login(trimmedUser, trimmedPass);
      } else {
        await signup(trimmedUser, trimmedPass);
      }
    } catch (err) {
      // Error is handled in context
    } finally {
      setIsSubmitting(false);
    }
  };

  const toggleMode = () => {
    setIsLoginMode(!isLoginMode);
    setUsername('');
    setPassword('');
    setConfirmPassword('');
    setLocalError(null);
    clearError();
  };

  const displayError = localError || error;

  return (
    <div style={{
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      minHeight: '100vh',
      padding: '20px',
      background: 'var(--bg-color)',
      color: 'var(--text-primary)'
    }}>
      <div className="glass-panel" style={{
        width: '100%',
        maxWidth: '400px',
        padding: '32px',
        border: '1px solid var(--panel-border)',
        background: 'var(--panel-bg)'
      }}>
        {/* Flat Logo and Brand Header */}
        <div style={{ textAlign: 'center', marginBottom: '32px' }}>
          <div style={{
            display: 'inline-flex',
            alignItems: 'center',
            justifyContent: 'center',
            width: '48px',
            height: '48px',
            background: 'var(--text-primary)',
            color: 'var(--bg-color)',
            border: '1px solid var(--text-primary)',
            marginBottom: '16px'
          }}>
            <TrendingUp size={24} style={{ strokeWidth: 2.5 }} />
          </div>
          <h1 style={{ fontSize: '1.6rem', fontWeight: 700, color: 'var(--text-primary)', fontFamily: 'JetBrains Mono, monospace', letterSpacing: '0.05em', marginBottom: '4px' }}>
            QUANTRUN
          </h1>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.75rem', fontFamily: 'JetBrains Mono, monospace', letterSpacing: '0.1em' }}>
            DESKTOP TERMINAL ENGINE
          </p>
        </div>

        {/* Display Error Box */}
        {displayError && (
          <div style={{
            display: 'flex',
            alignItems: 'flex-start',
            gap: '12px',
            background: 'rgba(255, 56, 56, 0.08)',
            border: '1px solid var(--danger)',
            padding: '12px',
            marginBottom: '20px',
            color: 'var(--danger)',
            fontSize: '0.8rem',
            fontFamily: 'JetBrains Mono, monospace'
          }}>
            <AlertTriangle size={16} style={{ flexShrink: 0, marginTop: '2px' }} />
            <div>
              <strong style={{ display: 'block', marginBottom: '2px', fontWeight: 700 }}>ERROR:</strong>
              {displayError}
            </div>
          </div>
        )}

        {/* Auth Form */}
        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label className="form-label">USERNAME</label>
            <div style={{ position: 'relative' }}>
              <span style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }}>
                <User size={16} />
              </span>
              <input
                type="text"
                className="form-input glow-border"
                placeholder="Enter username"
                style={{ paddingLeft: '40px' }}
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                disabled={isSubmitting}
                autoComplete="username"
              />
            </div>
          </div>

          <div className="form-group" style={{ marginBottom: isLoginMode ? '24px' : '16px' }}>
            <label className="form-label">PASSWORD</label>
            <div style={{ position: 'relative' }}>
              <span style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }}>
                <Lock size={16} />
              </span>
              <input
                type="password"
                className="form-input glow-border"
                placeholder={isLoginMode ? "Enter password" : "Create password (min 6 chars)"}
                style={{ paddingLeft: '40px' }}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                disabled={isSubmitting}
                autoComplete="current-password"
              />
            </div>
          </div>

          {!isLoginMode && (
            <div className="form-group" style={{ marginBottom: '24px' }}>
              <label className="form-label">CONFIRM PASSWORD</label>
              <div style={{ position: 'relative' }}>
                <span style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }}>
                  <Lock size={16} />
                </span>
                <input
                  type="password"
                  className="form-input glow-border"
                  placeholder="Confirm password"
                  style={{ paddingLeft: '40px' }}
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  disabled={isSubmitting}
                  autoComplete="new-password"
                />
              </div>
            </div>
          )}

          <button
            type="submit"
            className="btn btn-primary"
            style={{ width: '100%', padding: '12px', fontSize: '0.85rem', marginBottom: '20px' }}
            disabled={isSubmitting}
          >
            {isSubmitting ? (
              <span style={{ display: 'flex', alignItems: 'center', gap: '8px', justifyContent: 'center' }}>
                <span style={{
                  display: 'inline-block',
                  width: '12px',
                  height: '12px',
                  border: '2px solid rgba(0, 0, 0, 0.2)',
                  borderTopColor: 'var(--primary)',
                  borderRadius: '50%',
                  animation: 'spin 0.8s linear infinite'
                }} />
                {isLoginMode ? 'CONNECTING...' : 'REGISTERING...'}
              </span>
            ) : (
              isLoginMode ? 'CONNECT TERMINAL' : 'CREATE PORTFOLIO ACCOUNT'
            )}
          </button>
        </form>

        {/* Toggle between Sign In / Sign Up */}
        <div style={{
          textAlign: 'center',
          fontSize: '0.8rem',
          color: 'var(--text-secondary)',
          borderTop: '1px solid var(--panel-border)',
          paddingTop: '16px',
          fontFamily: 'JetBrains Mono, monospace'
        }}>
          {isLoginMode ? (
            <>
              First time?{' '}
              <button
                type="button"
                onClick={toggleMode}
                style={{
                  background: 'none',
                  border: 'none',
                  color: 'var(--text-primary)',
                  fontWeight: 700,
                  cursor: 'pointer',
                  padding: 0,
                  textDecoration: 'underline'
                }}
              >
                Sign Up Here
              </button>
            </>
          ) : (
            <>
              Have keys?{' '}
              <button
                type="button"
                onClick={toggleMode}
                style={{
                  background: 'none',
                  border: 'none',
                  color: 'var(--text-primary)',
                  fontWeight: 700,
                  cursor: 'pointer',
                  padding: 0,
                  textDecoration: 'underline'
                }}
              >
                Connect Here
              </button>
            </>
          )}
        </div>
      </div>

      <style>{`
        @keyframes spin {
          to { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );
};
