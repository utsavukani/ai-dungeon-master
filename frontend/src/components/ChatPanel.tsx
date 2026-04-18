'use client';
import { useState, useRef, useEffect, useCallback } from 'react';
import { getWsUrl, API_URL } from '@/lib/api';

interface ChatPanelProps {
  campaignId: string;
}

type ConnState = 'waking' | 'connecting' | 'connected' | 'error';

export default function ChatPanel({ campaignId }: ChatPanelProps) {
  const [messages, setMessages] = useState<{role: string, text: string}[]>([]);
  const [input, setInput] = useState('');
  const [isThinking, setIsThinking] = useState(false);
  const [connState, setConnState] = useState<ConnState>('waking');
  const wsRef = useRef<WebSocket | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const addMessage = (role: string, text: string) =>
    setMessages(prev => [...prev, { role, text }]);

  // ── Step 1: Wake the backend (Render free tier sleeps after inactivity) ──
  const connect = useCallback(() => {
    setConnState('connecting');

    const socket = new WebSocket(getWsUrl(campaignId));
    wsRef.current = socket;

    socket.onopen = () => {
      setConnState('connected');
    };

    socket.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.type === 'thinking') {
        setIsThinking(true);
      } else if (data.type === 'token') {
        setIsThinking(false);
        setMessages(prev => {
          const newMsgs = [...prev];
          if (newMsgs.length > 0 && newMsgs[newMsgs.length - 1].role === 'dm') {
            const lastMsg = { ...newMsgs[newMsgs.length - 1] };
            lastMsg.text += data.payload.text;
            newMsgs[newMsgs.length - 1] = lastMsg;
          } else {
            newMsgs.push({ role: 'dm', text: data.payload.text });
          }
          return newMsgs;
        });
      } else if (data.type === 'turn_complete') {
        setIsThinking(false);
        window.dispatchEvent(new CustomEvent('updateGameState', { detail: data.payload }));
      } else if (data.type === 'error') {
        addMessage('system', `⚠️ ${data.content}`);
      }
    };

    socket.onerror = () => {
      setConnState('error');
    };

    socket.onclose = () => {
      if (connState === 'connected') {
        addMessage('system', 'Connection lost. Please refresh the page.');
      }
    };
  }, [campaignId]);

  useEffect(() => {
    let cancelled = false;
    let retries = 0;
    const maxRetries = 12; // up to ~60 seconds

    const wake = async () => {
      try {
        const res = await fetch(`${API_URL}/health`, { signal: AbortSignal.timeout(8000) });
        if (res.ok && !cancelled) {
          connect();
          return;
        }
      } catch {
        // server sleeping, retry
      }

      retries++;
      if (retries >= maxRetries || cancelled) {
        setConnState('error');
        return;
      }
      setTimeout(wake, 5000);
    };

    wake();

    return () => {
      cancelled = true;
      wsRef.current?.close();
    };
  }, [campaignId, connect]);

  // Auto-scroll
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isThinking]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const ws = wsRef.current;
    if (!input.trim() || !ws || ws.readyState !== WebSocket.OPEN) return;

    addMessage('player', input);
    ws.send(JSON.stringify({ type: 'action', payload: { text: input } }));
    setInput('');
  };

  // ── Status banner ──────────────────────────────────────────────────────────
  const statusBanner = () => {
    if (connState === 'waking') return (
      <div className="animate-pulse" style={{ color: 'var(--text-secondary)', fontStyle: 'italic', fontSize: '14px' }}>
        🌅 Waking server — first load takes ~30–60s on free tier…
      </div>
    );
    if (connState === 'connecting') return (
      <div className="animate-pulse" style={{ color: 'var(--text-secondary)', fontStyle: 'italic', fontSize: '14px' }}>
        Connecting to your adventure...
      </div>
    );
    if (connState === 'error') return (
      <div style={{ color: 'var(--danger)', fontSize: '14px' }}>
        ❌ Cannot reach the server.{' '}
        <button
          onClick={() => { setConnState('waking'); }}
          style={{ background: 'none', border: 'none', color: 'var(--text-accent)', cursor: 'pointer', textDecoration: 'underline' }}
        >
          Retry
        </button>
      </div>
    );
    return null;
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <div style={{ flex: 1, overflowY: 'auto', marginBottom: '20px', paddingRight: '10px' }}>
        {(connState === 'waking' || connState === 'connecting') && messages.length === 0 && statusBanner()}

        {messages.map((msg, i) => (
          <div key={i} style={{
            marginBottom: '16px',
            textAlign: msg.role === 'player' ? 'right' : 'left'
          }}>
            <div style={{
              display: 'inline-block',
              padding: '12px 16px',
              borderRadius: '12px',
              background: msg.role === 'player' ? 'rgba(100, 255, 218, 0.1)'
                        : msg.role === 'system'  ? 'rgba(255,71,87,0.08)'
                        : 'var(--bg-tertiary)',
              border: msg.role === 'player' ? '1px solid var(--border-glow)'
                    : msg.role === 'system'  ? '1px solid rgba(255,71,87,0.3)'
                    : '1px solid var(--border-light)',
              maxWidth: '80%',
              color: msg.role === 'player' ? 'var(--text-accent)'
                   : msg.role === 'system'  ? 'var(--danger)'
                   : 'var(--text-primary)',
              whiteSpace: 'pre-wrap',
              lineHeight: '1.6',
            }}>
              {msg.text}
            </div>
          </div>
        ))}

        {connState === 'error' && messages.length === 0 && statusBanner()}

        {isThinking && (
          <div style={{ color: 'var(--text-secondary)', fontStyle: 'italic', fontSize: '14px' }}>
            The DM is thinking <span className="animate-pulse">...</span>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      <form onSubmit={handleSubmit} style={{ display: 'flex', gap: '10px', flexShrink: 0 }}>
        <input
          id="player-action-input"
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder={connState === 'connected' ? 'What do you do?' : 'Waiting for connection...'}
          disabled={connState !== 'connected'}
          style={{
            flex: 1,
            background: 'var(--bg-tertiary)',
            color: 'var(--text-primary)',
            border: '1px solid var(--border-light)',
            padding: '12px 16px',
            borderRadius: '8px',
            outline: 'none',
            fontFamily: 'var(--font-body)',
            fontSize: '16px',
            opacity: connState !== 'connected' ? 0.5 : 1,
          }}
          onFocus={e => e.target.style.borderColor = 'var(--text-accent)'}
          onBlur={e => e.target.style.borderColor = 'var(--border-light)'}
        />
        <button
          id="send-action-btn"
          type="submit"
          className="btn-primary"
          disabled={!input.trim() || connState !== 'connected'}
          style={{ opacity: (!input.trim() || connState !== 'connected') ? 0.5 : 1 }}
        >
          Act
        </button>
      </form>
    </div>
  );
}
