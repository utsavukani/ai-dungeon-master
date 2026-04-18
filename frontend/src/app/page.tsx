'use client';
import { useState, useEffect } from 'react';
import AuthPage from '@/components/AuthPage';
import CampaignSelect from '@/components/CampaignSelect';
import ChatPanel from '@/components/ChatPanel';
import Sidebar from '@/components/Sidebar';

type Screen = 'auth' | 'campaign' | 'game';

interface Session {
  userId: string;
  username: string;
  campaignId: string;
  campaignName: string;
}

export default function Home() {
  const [screen, setScreen] = useState<Screen>('auth');
  const [session, setSession] = useState<Session | null>(null);
  const [mobileSidebarOpen, setMobileSidebarOpen] = useState(false);

  // Restore session from localStorage on page load
  useEffect(() => {
    const stored = localStorage.getItem('aidm_session');
    if (stored) {
      try {
        const s: Session = JSON.parse(stored);
        if (s.userId && s.campaignId) {
          setSession(s);
          setScreen('game');
        }
      } catch {
        localStorage.removeItem('aidm_session');
      }
    }
  }, []);

  const handleAuthSuccess = (userId: string, username: string) => {
    setSession({ userId, username, campaignId: '', campaignName: '' });
    setScreen('campaign');
  };

  const handleCampaignSelected = (campaignId: string, campaignName: string) => {
    const s: Session = { ...session!, campaignId, campaignName };
    setSession(s);
    localStorage.setItem('aidm_session', JSON.stringify(s));
    setScreen('game');
  };

  const handleLogout = () => {
    localStorage.removeItem('aidm_session');
    setSession(null);
    setScreen('auth');
  };

  // ── Screens ──────────────────────────────────────────────
  if (screen === 'auth') {
    return <AuthPage onAuthSuccess={handleAuthSuccess} />;
  }

  if (screen === 'campaign') {
    return (
      <CampaignSelect
        userId={session!.userId}
        username={session!.username}
        onCampaignSelected={handleCampaignSelected}
        onLogout={handleLogout}
      />
    );
  }

  // ── Game Screen ───────────────────────────────────────────
  return (
    <main className="app-container">
      {/* Mobile Header */}
      <div className="mobile-header" style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        padding: '10px 20px',
        background: 'var(--bg-secondary)',
        borderBottom: '1px solid var(--border-light)',
      }}>
        <h1 style={{ fontSize: '16px', color: 'var(--text-accent)', margin: 0 }}>
          AI Dungeon Master
        </h1>
        <button
          className="btn-primary"
          onClick={() => setMobileSidebarOpen(!mobileSidebarOpen)}
        >
          {mobileSidebarOpen ? 'Close' : 'Stats'}
        </button>
      </div>

      {/* Chat */}
      <section className="chat-section">
        <div style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: '16px',
          flexShrink: 0,
        }} className="desktop-only">
          <h1 style={{
            fontSize: '20px',
            color: 'var(--text-accent)',
            textTransform: 'uppercase',
            letterSpacing: '2px',
            borderBottom: '1px solid var(--border-glow)',
            paddingBottom: '8px',
            margin: 0,
            flex: 1,
          }}>
            AI Dungeon Master — {session!.campaignName}
          </h1>
          <button
            id="logout-game-btn"
            onClick={handleLogout}
            style={{
              background: 'transparent',
              border: 'none',
              color: 'var(--text-secondary)',
              cursor: 'pointer',
              fontSize: '12px',
              marginLeft: '16px',
              textDecoration: 'underline',
            }}
          >
            Logout
          </button>
        </div>

        <div style={{ flex: 1, minHeight: 0 }}>
          <ChatPanel campaignId={session!.campaignId} />
        </div>
      </section>

      {/* Sidebar */}
      <section
        className="sidebar-section"
        style={{ display: mobileSidebarOpen ? 'block' : undefined }}
      >
        <Sidebar campaignId={session!.campaignId} onLogout={handleLogout} />
      </section>

      <style jsx>{`
        @media (min-width: 769px) {
          .mobile-header { display: none !important; }
        }
        @media (max-width: 768px) {
          .desktop-only { display: none !important; }
          .sidebar-section {
            position: absolute;
            top: 60px;
            right: 0;
            bottom: 0;
            width: 80%;
            z-index: 100;
            border-left: 1px solid var(--border-glow);
            box-shadow: -5px 0 15px rgba(0,0,0,0.5);
          }
        }
      `}</style>
    </main>
  );
}
