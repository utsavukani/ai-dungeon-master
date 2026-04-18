'use client';
import { useState, useRef, useEffect } from 'react';
import { getWsUrl } from '@/lib/api';

interface ChatPanelProps {
  campaignId: string;
}

export default function ChatPanel({ campaignId }: ChatPanelProps) {
  const [messages, setMessages] = useState<{role: string, text: string}[]>([]);
  const [input, setInput] = useState('');
  const [isThinking, setIsThinking] = useState(false);
  const [ws, setWs] = useState<WebSocket | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Initialize WebSocket connection using the dynamic campaignId from props
  useEffect(() => {
    const socket = new WebSocket(getWsUrl(campaignId));
    
    socket.onopen = () => {
      console.log(`Connected to campaign: ${campaignId}`);
      setMessages([]);
    };

    socket.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.type === 'thinking') {
        setIsThinking(true);
      } else if (data.type === 'token') {
        setIsThinking(false);
        setMessages((prev) => {
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
      }
    };

    socket.onerror = () => {
      setMessages([{ role: 'dm', text: 'Connection error. Is the backend server running?' }]);
    };

    socket.onclose = () => {
      console.log('WebSocket disconnected');
    };

    setWs(socket);
    return () => socket.close();
  }, [campaignId]);

  // Auto-scroll
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isThinking]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || !ws || ws.readyState !== WebSocket.OPEN) return;
    
    setMessages(prev => [...prev, { role: 'player', text: input }]);
    ws.send(JSON.stringify({ type: 'action', payload: { text: input } }));
    setInput('');
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <div style={{ flex: 1, overflowY: 'auto', marginBottom: '20px', paddingRight: '10px' }}>
        {messages.length === 0 && !isThinking && (
          <div className="animate-pulse" style={{ color: 'var(--text-secondary)', fontStyle: 'italic', fontSize: '14px' }}>
            Connecting to your adventure...
          </div>
        )}
        {messages.map((msg, i) => (
          <div key={i} style={{ 
            marginBottom: '16px', 
            textAlign: msg.role === 'player' ? 'right' : 'left' 
          }}>
            <div style={{
              display: 'inline-block',
              padding: '12px 16px',
              borderRadius: '12px',
              background: msg.role === 'player' ? 'rgba(100, 255, 218, 0.1)' : 'var(--bg-tertiary)',
              border: msg.role === 'player' ? '1px solid var(--border-glow)' : '1px solid var(--border-light)',
              maxWidth: '80%',
              color: msg.role === 'player' ? 'var(--text-accent)' : 'var(--text-primary)',
              whiteSpace: 'pre-wrap',
              lineHeight: '1.6',
            }}>
              {msg.text}
            </div>
          </div>
        ))}
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
          placeholder="What do you do?"
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
          }}
          onFocus={e => e.target.style.borderColor = 'var(--text-accent)'}
          onBlur={e => e.target.style.borderColor = 'var(--border-light)'}
        />
        <button
          id="send-action-btn"
          type="submit"
          className="btn-primary"
          disabled={!input.trim()}
          style={{ opacity: !input.trim() ? 0.5 : 1 }}
        >
          Act
        </button>
      </form>
    </div>
  );
}
