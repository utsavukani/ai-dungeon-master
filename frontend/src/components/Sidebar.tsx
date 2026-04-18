'use client';
import { useState, useEffect } from 'react';
import { API_URL } from '@/lib/api';

interface SidebarProps {
  campaignId: string;
  onLogout: () => void;
}

export default function Sidebar({ campaignId, onLogout }: SidebarProps) {
  const [character, setCharacter] = useState<any>(null);
  const [quests, setQuests] = useState<any[]>([]);
  const [inventory, setInventory] = useState<string[]>([]);

  // Listen to live turn_complete events from ChatPanel
  useEffect(() => {
    const handleUpdate = (e: any) => {
      const payload = e.detail;
      if (payload.character) setCharacter(payload.character);
      if (payload.quests) setQuests(payload.quests);
      if (payload.inventory) setInventory(payload.inventory);
    };
    window.addEventListener('updateGameState', handleUpdate);
    return () => window.removeEventListener('updateGameState', handleUpdate);
  }, []);

  // Initial data fetch using dynamic campaignId prop
  useEffect(() => {
    if (!campaignId) return;

    const refreshData = async () => {
      try {
        const charRes = await fetch(`${API_URL}/api/character?campaign_id=${campaignId}`);
        if (charRes.ok) {
          const charData = await charRes.json();
          if (charData.status === 'success') {
            setCharacter(charData.stats);
            setInventory(charData.inventory ?? []);
          }
        }

        const questRes = await fetch(`${API_URL}/api/quests?campaign_id=${campaignId}`);
        if (questRes.ok) {
          const questData = await questRes.json();
          if (questData.status === 'success') {
            setQuests(questData.active_quests ?? []);
          }
        }
      } catch {
        // Backend might not be ready yet — silently retry
      }
    };

    refreshData();
  }, [campaignId]);

  // Stat bar helper
  const StatBar = ({ value, max, color }: { value: number; max: number; color: string }) => (
    <div style={{
      height: '4px',
      background: 'var(--bg-primary)',
      borderRadius: '2px',
      overflow: 'hidden',
      marginTop: '4px',
    }}>
      <div style={{
        height: '100%',
        width: `${Math.min(100, (value / max) * 100)}%`,
        background: color,
        borderRadius: '2px',
        transition: 'width 0.4s ease',
      }} />
    </div>
  );

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column', gap: '16px' }}>

      {/* Character Stats */}
      <div className="glass-panel" style={{ padding: '18px' }}>
        <h2 style={{ fontSize: '11px', color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '2px', marginBottom: '14px' }}>
          Character
        </h2>
        {character ? (
          <div style={{ fontSize: '13px', display: 'flex', flexDirection: 'column', gap: '10px' }}>
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: 'var(--text-secondary)' }}>HP</span>
                <span style={{ color: 'var(--danger)' }}>{character.health}/{character.max_health}</span>
              </div>
              <StatBar value={character.health} max={character.max_health} color="var(--danger)" />
            </div>
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: 'var(--text-secondary)' }}>XP</span>
                <span style={{ color: 'var(--success)' }}>{character.experience}</span>
              </div>
              <StatBar value={character.experience % 100} max={100} color="var(--success)" />
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px', marginTop: '4px' }}>
              <div style={{ color: 'var(--text-secondary)' }}>Level <span style={{ color: 'var(--text-primary)' }}>{character.level}</span></div>
              <div style={{ color: 'var(--text-secondary)' }}>Gold <span style={{ color: 'var(--warning)' }}>{character.gold}</span></div>
              <div style={{ color: 'var(--text-secondary)' }}>STR <span style={{ color: 'var(--text-primary)' }}>{character.strength}</span></div>
              <div style={{ color: 'var(--text-secondary)' }}>INT <span style={{ color: 'var(--text-primary)' }}>{character.intelligence}</span></div>
              <div style={{ color: 'var(--text-secondary)' }}>CHA <span style={{ color: 'var(--text-primary)' }}>{character.charisma}</span></div>
            </div>
          </div>
        ) : (
          <div className="animate-pulse" style={{ color: 'var(--text-secondary)', fontSize: '12px' }}>
            Waiting for game to start...
          </div>
        )}
      </div>

      {/* Inventory */}
      <div className="glass-panel" style={{ padding: '18px' }}>
        <h2 style={{ fontSize: '11px', color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '2px', marginBottom: '14px' }}>
          Inventory
        </h2>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
          {inventory && inventory.length > 0 ? (
            inventory.map((item, i) => (
              <span key={i} style={{
                background: 'var(--bg-tertiary)',
                padding: '4px 10px',
                borderRadius: '4px',
                fontSize: '12px',
                border: '1px solid var(--border-light)',
                color: 'var(--text-primary)',
              }}>
                {item}
              </span>
            ))
          ) : (
            <span style={{ color: 'var(--text-secondary)', fontSize: '12px' }}>Empty</span>
          )}
        </div>
      </div>

      {/* Quests */}
      <div className="glass-panel" style={{ padding: '18px', flex: 1, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
        <h2 style={{ fontSize: '11px', color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '2px', marginBottom: '14px', flexShrink: 0 }}>
          Active Quests
        </h2>
        <ul style={{ listStyle: 'none', padding: 0, margin: 0, fontSize: '13px', overflowY: 'auto', flex: 1 }}>
          {quests && quests.length > 0 ? (
            quests.map((q: any, i) => (
              <li key={i} style={{
                padding: '8px 0',
                borderBottom: '1px solid var(--border-light)',
                color: 'var(--text-primary)',
                display: 'flex',
                gap: '8px',
                alignItems: 'flex-start',
              }}>
                <span style={{ color: 'var(--warning)', flexShrink: 0 }}>◆</span>
                <span>{q.description}</span>
              </li>
            ))
          ) : (
            <li style={{ color: 'var(--text-secondary)', fontSize: '12px' }}>No active quests yet.</li>
          )}
        </ul>
      </div>

      {/* Logout */}
      <button
        id="sidebar-logout-btn"
        onClick={onLogout}
        style={{
          background: 'transparent',
          border: '1px solid var(--border-light)',
          color: 'var(--text-secondary)',
          borderRadius: '8px',
          padding: '10px',
          cursor: 'pointer',
          fontSize: '12px',
          letterSpacing: '1px',
          textTransform: 'uppercase',
          transition: 'all 0.2s',
          flexShrink: 0,
        }}
        onMouseEnter={e => (e.currentTarget.style.borderColor = 'var(--danger)')}
        onMouseLeave={e => (e.currentTarget.style.borderColor = 'var(--border-light)')}
      >
        Logout
      </button>
    </div>
  );
}
