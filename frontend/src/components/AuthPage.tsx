'use client';
import { useState, useEffect, useRef } from 'react';
import { API_URL } from '@/lib/api';

interface AuthPageProps {
  onAuthSuccess: (userId: string, username: string) => void;
}

type BackendStatus = 'checking' | 'ready' | 'waking' | 'offline';

export default function AuthPage({ onAuthSuccess }: AuthPageProps) {
  const [tab, setTab] = useState<'login' | 'register'>('login');
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [backendStatus, setBackendStatus] = useState<BackendStatus>('checking');
  const retryRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // On mount: wake the Render backend (free tier sleeps after 15 min idle)
  useEffect(() => {
    let attempts = 0;
    const maxAttempts = 10; // ~50 seconds max

    const ping = async () => {
      try {
        const res = await fetch(`${API_URL}/health`, { signal: AbortSignal.timeout(8000) });
        if (res.ok) {
          setBackendStatus('ready');
          return;
        }
      } catch {
        // server sleeping or not yet ready
      }

      attempts++;
      if (attempts >= maxAttempts) {
        setBackendStatus('offline');
        return;
      }

      setBackendStatus(attempts === 1 ? 'waking' : 'waking');
      retryRef.current = setTimeout(ping, 5000);
    };

    ping();

    return () => {
      if (retryRef.current) clearTimeout(retryRef.current);
    };
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (backendStatus !== 'ready') return;
    setError('');
    setLoading(true);

    const endpoint = tab === 'login' ? '/api/auth/login' : '/api/auth/register';

    try {
      const res = await fetch(`${API_URL}${endpoint}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username: username.trim(), password })
      });
      const data = await res.json();

      if (!res.ok) {
        setError(data.detail || 'Something went wrong.');
        return;
      }

      onAuthSuccess(data.user_id, data.username);
    } catch {
      setError('Server unreachable. Please wait a moment and try again.');
    } finally {
      setLoading(false);
    }
  };

  const statusBar = () => {
    if (backendStatus === 'checking') return (
      <div style={statusStyle('#64ffda22', '#64ffda66', 'var(--text-accent)')}>
        ⏳ Checking server...
      </div>
    );
    if (backendStatus === 'waking') return (
      <div style={statusStyle('rgba(255,200,60,0.08)', 'rgba(255,200,60,0.3)', '#ffc83c')}>
        🌅 Server waking up — this takes ~30–60s on first visit. Please wait...
      </div>
    );
    if (backendStatus === 'offline') return (
      <div style={statusStyle('rgba(255,71,87,0.1)', 'rgba(255,71,87,0.3)', 'var(--danger)')}>
        ❌ Server unreachable. Try refreshing the page.
      </div>
    );
    return null; // 'ready' - show nothing
  };

  function statusStyle(bg: string, border: string, color: string) {
    return {
      background: bg,
      border: `1px solid ${border}`,
      borderRadius: '8px',
      padding: '10px 14px',
      color,
      fontSize: '12px',
      textAlign: 'center' as const,
      letterSpacing: '0.3px',
    };
  }

  const isFormDisabled = backendStatus !== 'ready';

  return (
    <div style={{
      height: '100dvh',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      background: 'var(--bg-primary)',
      padding: '20px',
    }}>
      {/* Ambient glow */}
      <div style={{
        position: 'fixed', top: '20%', left: '50%', transform: 'translateX(-50%)',
        width: '600px', height: '300px',
        background: 'radial-gradient(ellipse, rgba(100,255,218,0.07) 0%, transparent 70%)',
        pointerEvents: 'none',
      }} />

      <div className="glass-panel" style={{
        width: '100%',
        maxWidth: '420px',
        padding: '40px',
        position: 'relative',
      }}>
        {/* Logo / Title */}
        <div style={{ textAlign: 'center', marginBottom: '32px' }}>
          <div style={{ fontSize: '40px', marginBottom: '8px' }}>⚔️</div>
          <h1 style={{
            fontSize: '20px',
            color: 'var(--text-accent)',
            letterSpacing: '3px',
            textTransform: 'uppercase',
            margin: 0,
          }}>AI Dungeon Master</h1>
          <p style={{ color: 'var(--text-secondary)', fontSize: '13px', marginTop: '6px' }}>
            Begin your legend
          </p>
        </div>

        {/* Backend status bar */}
        {statusBar()}

        {/* Tab switcher */}
        <div style={{
          display: 'flex',
          borderBottom: '1px solid var(--border-light)',
          marginTop: backendStatus !== 'ready' ? '16px' : '0',
          marginBottom: '28px',
          gap: '4px',
        }}>
          {(['login', 'register'] as const).map((t) => (
            <button
              key={t}
              onClick={() => { setTab(t); setError(''); }}
              style={{
                flex: 1,
                background: 'transparent',
                border: 'none',
                padding: '10px',
                cursor: 'pointer',
                fontFamily: 'var(--font-mono)',
                fontSize: '13px',
                letterSpacing: '1px',
                textTransform: 'uppercase',
                color: tab === t ? 'var(--text-accent)' : 'var(--text-secondary)',
                borderBottom: tab === t ? '2px solid var(--text-accent)' : '2px solid transparent',
                transition: 'all 0.2s ease',
              }}
            >
              {t === 'login' ? 'Login' : 'Register'}
            </button>
          ))}
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <div>
            <label style={{ fontSize: '12px', color: 'var(--text-secondary)', letterSpacing: '1px', textTransform: 'uppercase' }}>
              Username
            </label>
            <input
              id="auth-username"
              type="text"
              value={username}
              onChange={e => setUsername(e.target.value)}
              placeholder="Enter your username"
              autoComplete="username"
              required
              disabled={isFormDisabled}
              style={{
                width: '100%',
                marginTop: '6px',
                background: 'var(--bg-tertiary)',
                color: 'var(--text-primary)',
                border: '1px solid var(--border-light)',
                padding: '12px 14px',
                borderRadius: '8px',
                outline: 'none',
                fontFamily: 'var(--font-body)',
                fontSize: '15px',
                transition: 'border-color 0.2s',
                opacity: isFormDisabled ? 0.5 : 1,
              }}
              onFocus={e => e.target.style.borderColor = 'var(--text-accent)'}
              onBlur={e => e.target.style.borderColor = 'var(--border-light)'}
            />
          </div>

          <div>
            <label style={{ fontSize: '12px', color: 'var(--text-secondary)', letterSpacing: '1px', textTransform: 'uppercase' }}>
              Password
            </label>
            <input
              id="auth-password"
              type="password"
              value={password}
              onChange={e => setPassword(e.target.value)}
              placeholder={tab === 'register' ? 'At least 6 characters' : 'Enter your password'}
              autoComplete={tab === 'login' ? 'current-password' : 'new-password'}
              required
              disabled={isFormDisabled}
              style={{
                width: '100%',
                marginTop: '6px',
                background: 'var(--bg-tertiary)',
                color: 'var(--text-primary)',
                border: '1px solid var(--border-light)',
                padding: '12px 14px',
                borderRadius: '8px',
                outline: 'none',
                fontFamily: 'var(--font-body)',
                fontSize: '15px',
                transition: 'border-color 0.2s',
                opacity: isFormDisabled ? 0.5 : 1,
              }}
              onFocus={e => e.target.style.borderColor = 'var(--text-accent)'}
              onBlur={e => e.target.style.borderColor = 'var(--border-light)'}
            />
          </div>

          {error && (
            <div style={{
              background: 'rgba(255, 71, 87, 0.1)',
              border: '1px solid rgba(255, 71, 87, 0.3)',
              borderRadius: '8px',
              padding: '10px 14px',
              color: 'var(--danger)',
              fontSize: '13px',
            }}>
              {error}
            </div>
          )}

          <button
            id="auth-submit"
            type="submit"
            disabled={loading || !username.trim() || !password || isFormDisabled}
            className="btn-primary"
            style={{
              marginTop: '8px',
              padding: '13px',
              fontSize: '14px',
              opacity: (loading || !username.trim() || !password || isFormDisabled) ? 0.5 : 1,
              cursor: (loading || !username.trim() || !password || isFormDisabled) ? 'not-allowed' : 'pointer',
            }}
          >
            {loading
              ? 'Please wait...'
              : isFormDisabled
                ? 'Waiting for server...'
                : tab === 'login' ? 'Enter the Realm' : 'Create Account'}
          </button>
        </form>
      </div>
    </div>
  );
}
