'use client';
import { useState, useEffect } from 'react';
import { API_URL } from '@/lib/api';

interface Campaign {
  id: string;
  name: string;
  created_at: string;
  last_played: string | null;
}

interface CampaignSelectProps {
  userId: string;
  username: string;
  onCampaignSelected: (campaignId: string, campaignName: string) => void;
  onLogout: () => void;
}

export default function CampaignSelect({ userId, username, onCampaignSelected, onLogout }: CampaignSelectProps) {
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [newName, setNewName] = useState('');
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    fetchCampaigns();
  }, []);

  const fetchCampaigns = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API_URL}/api/campaigns?user_id=${userId}`);
      const data = await res.json();
      if (data.status === 'success') {
        setCampaigns(data.campaigns);
      }
    } catch {
      setError('Failed to load campaigns.');
    } finally {
      setLoading(false);
    }
  };

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setCreating(true);
    try {
      const res = await fetch(`${API_URL}/api/campaigns`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: userId, name: newName.trim() || 'New Adventure' })
      });
      const data = await res.json();
      if (!res.ok) {
        setError(data.detail || 'Failed to create campaign.');
        return;
      }
      onCampaignSelected(data.campaign_id, data.name);
    } catch {
      setError('Cannot reach the server.');
    } finally {
      setCreating(false);
    }
  };

  const formatDate = (iso: string | null) => {
    if (!iso) return 'Never';
    return new Date(iso).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
  };

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
        background: 'radial-gradient(ellipse, rgba(100,255,218,0.06) 0%, transparent 70%)',
        pointerEvents: 'none',
      }} />

      <div style={{ width: '100%', maxWidth: '520px' }}>
        {/* Header */}
        <div style={{ textAlign: 'center', marginBottom: '32px' }}>
          <div style={{ fontSize: '36px', marginBottom: '8px' }}>🗺️</div>
          <h1 style={{
            fontSize: '18px',
            color: 'var(--text-accent)',
            letterSpacing: '3px',
            textTransform: 'uppercase',
            margin: 0,
          }}>Choose Your Adventure</h1>
          <p style={{ color: 'var(--text-secondary)', fontSize: '13px', marginTop: '8px' }}>
            Welcome back, <span style={{ color: 'var(--text-primary)' }}>{username}</span>
          </p>
        </div>

        {/* Start New Adventure */}
        <div className="glass-panel" style={{ padding: '24px', marginBottom: '20px' }}>
          <h2 style={{ fontSize: '13px', color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '1px', marginBottom: '16px' }}>
            New Adventure
          </h2>
          <form onSubmit={handleCreate} style={{ display: 'flex', gap: '10px' }}>
            <input
              id="campaign-name-input"
              type="text"
              value={newName}
              onChange={e => setNewName(e.target.value)}
              placeholder="Name your adventure (optional)"
              style={{
                flex: 1,
                background: 'var(--bg-tertiary)',
                color: 'var(--text-primary)',
                border: '1px solid var(--border-light)',
                padding: '11px 14px',
                borderRadius: '8px',
                outline: 'none',
                fontFamily: 'var(--font-body)',
                fontSize: '14px',
              }}
              onFocus={e => e.target.style.borderColor = 'var(--text-accent)'}
              onBlur={e => e.target.style.borderColor = 'var(--border-light)'}
            />
            <button
              id="create-campaign-btn"
              type="submit"
              disabled={creating}
              className="btn-primary"
              style={{ whiteSpace: 'nowrap', opacity: creating ? 0.6 : 1 }}
            >
              {creating ? 'Creating...' : '+ Start'}
            </button>
          </form>
          {error && (
            <div style={{
              marginTop: '12px',
              color: 'var(--danger)',
              fontSize: '13px',
              padding: '8px 12px',
              background: 'rgba(255,71,87,0.1)',
              borderRadius: '6px',
              border: '1px solid rgba(255,71,87,0.2)',
            }}>
              {error}
            </div>
          )}
        </div>

        {/* Existing Campaigns */}
        {campaigns.length > 0 && (
          <div className="glass-panel" style={{ padding: '24px', marginBottom: '20px' }}>
            <h2 style={{ fontSize: '13px', color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '1px', marginBottom: '16px' }}>
              Resume Adventure
            </h2>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
              {loading ? (
                <div className="animate-pulse" style={{ color: 'var(--text-secondary)', fontSize: '14px' }}>
                  Loading campaigns...
                </div>
              ) : (
                campaigns.map((c) => (
                  <button
                    key={c.id}
                    id={`campaign-${c.id}`}
                    onClick={() => onCampaignSelected(c.id, c.name)}
                    style={{
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center',
                      background: 'var(--bg-tertiary)',
                      border: '1px solid var(--border-light)',
                      borderRadius: '8px',
                      padding: '14px 16px',
                      cursor: 'pointer',
                      transition: 'all 0.2s ease',
                      textAlign: 'left',
                    }}
                    onMouseEnter={e => {
                      (e.currentTarget as HTMLElement).style.borderColor = 'var(--border-glow)';
                      (e.currentTarget as HTMLElement).style.background = 'rgba(100,255,218,0.05)';
                    }}
                    onMouseLeave={e => {
                      (e.currentTarget as HTMLElement).style.borderColor = 'var(--border-light)';
                      (e.currentTarget as HTMLElement).style.background = 'var(--bg-tertiary)';
                    }}
                  >
                    <div>
                      <div style={{ color: 'var(--text-primary)', fontSize: '14px', fontWeight: 500 }}>
                        {c.name}
                      </div>
                      <div style={{ color: 'var(--text-secondary)', fontSize: '12px', marginTop: '2px' }}>
                        Last played: {formatDate(c.last_played)}
                      </div>
                    </div>
                    <span style={{ color: 'var(--text-accent)', fontSize: '18px' }}>→</span>
                  </button>
                ))
              )}
            </div>
          </div>
        )}

        {/* Logout */}
        <div style={{ textAlign: 'center' }}>
          <button
            id="logout-btn"
            onClick={onLogout}
            style={{
              background: 'transparent',
              border: 'none',
              color: 'var(--text-secondary)',
              cursor: 'pointer',
              fontSize: '13px',
              textDecoration: 'underline',
            }}
          >
            Logout
          </button>
        </div>
      </div>
    </div>
  );
}
