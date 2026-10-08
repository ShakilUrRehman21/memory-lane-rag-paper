import React, { useState, useEffect, useMemo } from 'react';
import { api, type ChangePoint } from '../api';
import {
  Layers, ArrowRight, Calendar, AlertCircle,
  SlidersHorizontal, Sparkles
} from 'lucide-react';

interface ChangeExplorerViewProps {
  userId?: string;
}

export const ChangeExplorerView: React.FC<ChangeExplorerViewProps> = ({ userId = 'default_user' }) => {
  const [changes, setChanges] = useState<ChangePoint[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedTopic, setSelectedTopic] = useState<string>('all');
  const [minMagnitude, setMinMagnitude] = useState<number>(0);
  const [diffMode, setDiffMode] = useState<'cards' | 'timeline'>('cards');

  const loadChanges = async () => {
    setLoading(true);
    try {
      const data = await api.getChanges(userId);
      setChanges(data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadChanges();
  }, [userId]);

  const uniqueTopics = ['all', ...Array.from(new Set(changes.map(c => c.topic_or_entity)))];

  const filteredChanges = useMemo(() => {
    return changes.filter(c => {
      const matchesTopic = selectedTopic === 'all' || c.topic_or_entity === selectedTopic;
      const matchesMagnitude = c.magnitude >= minMagnitude;
      return matchesTopic && matchesMagnitude;
    });
  }, [changes, selectedTopic, minMagnitude]);

  const getChangeBadge = (type: string) => {
    switch (type.toLowerCase()) {
      case 'reversal':
        return <span className="badge badge-reversal">Stance Reversal</span>;
      case 'sudden_shift':
        return <span className="badge" style={{ background: '#fdf2f8', color: '#db2777', border: '1px solid #fbcfe8' }}>Sudden Shift</span>;
      default:
        return <span className="badge badge-decision">Gradual Evolution</span>;
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      {/* Header and Interactive Filters */}
      <div className="glass-panel" style={{ padding: '24px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '16px' }}>
          <div>
            <h2 style={{ fontSize: '18px', fontWeight: 700, display: 'flex', alignItems: 'center', gap: '10px', color: 'var(--text-main)' }}>
              <Layers size={20} style={{ color: 'var(--accent-violet)' }} />
              <span>Change Explorer</span>
            </h2>
          </div>

          {/* Diff Mode Toggle */}
          <div style={{ display: 'flex', background: '#f1f5f9', padding: '3px', borderRadius: '8px', border: '1px solid var(--border-subtle)' }}>
            <button
              onClick={() => setDiffMode('cards')}
              style={{
                padding: '4px 12px',
                borderRadius: '6px',
                border: 'none',
                fontSize: '12px',
                fontWeight: 600,
                cursor: 'pointer',
                background: diffMode === 'cards' ? '#ffffff' : 'transparent',
                color: diffMode === 'cards' ? 'var(--accent-primary)' : 'var(--text-dim)',
                boxShadow: diffMode === 'cards' ? 'var(--shadow-xs)' : 'none',
                transition: 'all 0.15s ease'
              }}
            >
              Side-by-Side Cards
            </button>
            <button
              onClick={() => setDiffMode('timeline')}
              style={{
                padding: '4px 12px',
                borderRadius: '6px',
                border: 'none',
                fontSize: '12px',
                fontWeight: 600,
                cursor: 'pointer',
                background: diffMode === 'timeline' ? '#ffffff' : 'transparent',
                color: diffMode === 'timeline' ? 'var(--accent-primary)' : 'var(--text-dim)',
                boxShadow: diffMode === 'timeline' ? 'var(--shadow-xs)' : 'none',
                transition: 'all 0.15s ease'
              }}
            >
              Connected Chronology
            </button>
          </div>
        </div>

        {/* Filter controls row */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '12px', marginTop: '16px', paddingTop: '14px', borderTop: '1px solid var(--border-subtle)' }}>
          {/* Topic selector pills */}
          <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap', alignItems: 'center' }}>
            <span style={{ fontSize: '11px', color: 'var(--text-dim)', fontWeight: 700, letterSpacing: '0.04em' }}>TOPIC:</span>
            {uniqueTopics.map(t => {
              const count = t === 'all' ? changes.length : changes.filter(c => c.topic_or_entity === t).length;
              return (
                <button
                  key={t}
                  onClick={() => setSelectedTopic(t)}
                  style={{
                    padding: '3px 10px',
                    borderRadius: '6px',
                    border: '1px solid var(--border-subtle)',
                    background: selectedTopic === t ? '#f5f3ff' : '#ffffff',
                    color: selectedTopic === t ? 'var(--accent-violet)' : 'var(--text-muted)',
                    borderColor: selectedTopic === t ? '#ddd6fe' : 'var(--border-subtle)',
                    fontSize: '12px',
                    fontWeight: selectedTopic === t ? 700 : 500,
                    cursor: 'pointer',
                    transition: 'all 0.15s ease'
                  }}
                >
                  {t} <span style={{ opacity: 0.65, fontSize: '10.5px' }}>({count})</span>
                </button>
              );
            })}
          </div>

          {/* Magnitude slider filter */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', background: '#f8fafc', padding: '6px 12px', borderRadius: '8px', border: '1px solid var(--border-subtle)' }}>
            <SlidersHorizontal size={13} style={{ color: 'var(--text-dim)' }} />
            <span style={{ fontSize: '11px', fontWeight: 700, color: 'var(--text-dim)' }}>
              MIN DRIFT:
            </span>
            <input
              type="range"
              min="0"
              max="1"
              step="0.05"
              value={minMagnitude}
              onChange={e => setMinMagnitude(parseFloat(e.target.value))}
              style={{ width: '80px', cursor: 'pointer' }}
            />
            <span style={{ fontSize: '12px', fontWeight: 700, color: 'var(--accent-amber)', minWidth: '32px', fontFamily: 'var(--font-mono)' }}>
              Δ {minMagnitude.toFixed(2)}
            </span>
          </div>
        </div>
      </div>

      {/* Change Points Grid */}
      {loading ? (
        <div style={{ padding: '50px', textAlign: 'center', color: 'var(--text-dim)', background: '#ffffff', borderRadius: '12px', border: '1px solid var(--border-subtle)' }}>
          Computing longitudinal change points...
        </div>
      ) : filteredChanges.length === 0 ? (
        <div className="glass-panel" style={{ padding: '36px', textAlign: 'center', color: 'var(--text-muted)' }}>
          No change points match the topic or minimum drift threshold.
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
          {filteredChanges.map((cp, idx) => (
            <div key={idx} className="glass-panel card-interactive" style={{ padding: '20px', display: 'flex', flexDirection: 'column', gap: '14px' }}>
              {/* Header */}
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '10px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                  <span style={{ fontSize: '15px', fontWeight: 700, color: 'var(--text-main)' }}>
                    {cp.topic_or_entity}
                  </span>
                  {getChangeBadge(cp.change_type)}
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: '14px', fontSize: '12.5px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: 'var(--text-muted)' }}>
                    <Calendar size={13} />
                    <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 600 }}>{cp.from_period.slice(0, 7)}</span>
                    <ArrowRight size={13} style={{ color: 'var(--accent-primary)' }} />
                    <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 600 }}>{cp.to_period.slice(0, 7)}</span>
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <span style={{ fontSize: '11px', color: 'var(--text-dim)', fontWeight: 700 }}>SEMANTIC DRIFT:</span>
                    <span style={{ color: 'var(--accent-amber)', fontWeight: 700, background: '#fffbeb', border: '1px solid #fde68a', padding: '2px 8px', borderRadius: '4px', fontFamily: 'var(--font-mono)' }}>
                      Δ {cp.magnitude}
                    </span>
                  </div>
                </div>
              </div>

              {/* Side-by-side or Connected chronology */}
              {diffMode === 'cards' ? (
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '14px', alignItems: 'stretch' }}>
                  {/* Earlier Statement */}
                  <div style={{ padding: '16px', background: '#f8fafc', borderRadius: '8px', border: '1px solid var(--border-subtle)', display: 'flex', flexDirection: 'column', gap: '6px' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <span style={{ fontSize: '11px', fontWeight: 700, color: 'var(--text-dim)', letterSpacing: '0.04em' }}>
                        EARLIER PERSPECTIVE
                      </span>
                      <span style={{ fontSize: '11px', color: 'var(--text-dim)', fontFamily: 'var(--font-mono)' }}>
                        {cp.from_period.slice(0, 10)}
                      </span>
                    </div>
                    <p style={{ fontSize: '13.5px', color: 'var(--text-muted)', lineHeight: '1.55', fontStyle: 'italic', margin: 0 }}>
                      "{cp.earlier_statement}"
                    </p>
                  </div>

                  {/* Later Statement */}
                  <div style={{ padding: '16px', background: '#eff6ff', borderRadius: '8px', border: '1px solid #bfdbfe', display: 'flex', flexDirection: 'column', gap: '6px' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <span style={{ fontSize: '11px', fontWeight: 700, color: 'var(--accent-primary)', letterSpacing: '0.04em', display: 'flex', alignItems: 'center', gap: '4px' }}>
                        <Sparkles size={11} />
                        <span>EVOLVED PERSPECTIVE</span>
                      </span>
                      <span style={{ fontSize: '11px', color: 'var(--accent-primary)', fontFamily: 'var(--font-mono)', fontWeight: 600 }}>
                        {cp.to_period.slice(0, 10)}
                      </span>
                    </div>
                    <p style={{ fontSize: '13.5px', color: 'var(--text-main)', lineHeight: '1.55', fontStyle: 'italic', margin: 0, fontWeight: 500 }}>
                      "{cp.later_statement}"
                    </p>
                  </div>
                </div>
              ) : (
                /* Connected Chronology View */
                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', background: '#f8fafc', padding: '16px', borderRadius: '8px', border: '1px solid var(--border-subtle)' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                    <span style={{ fontSize: '11.5px', fontWeight: 700, color: 'var(--text-dim)', width: '75px', fontFamily: 'var(--font-mono)' }}>
                      {cp.from_period.slice(0, 7)}
                    </span>
                    <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#94a3b8' }} />
                    <p style={{ fontSize: '13px', color: 'var(--text-muted)', fontStyle: 'italic', margin: 0 }}>
                      "{cp.earlier_statement}"
                    </p>
                  </div>
                  <div style={{ width: '2px', height: '16px', background: '#cbd5e1', marginLeft: '87px' }} />
                  <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                    <span style={{ fontSize: '11.5px', fontWeight: 700, color: 'var(--accent-primary)', width: '75px', fontFamily: 'var(--font-mono)' }}>
                      {cp.to_period.slice(0, 7)}
                    </span>
                    <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: 'var(--accent-primary)' }} />
                    <p style={{ fontSize: '13px', color: 'var(--text-main)', fontStyle: 'italic', fontWeight: 500, margin: 0 }}>
                      "{cp.later_statement}"
                    </p>
                  </div>
                </div>
              )}

              {/* Uncertainty bound annotation */}
              {cp.uncertainty_bounds && (
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '12px', color: '#92400e', background: '#fffbeb', border: '1px solid #fde68a', padding: '8px 12px', borderRadius: '6px' }}>
                  <AlertCircle size={14} style={{ flexShrink: 0, color: 'var(--accent-amber)' }} />
                  <span>{cp.uncertainty_bounds}</span>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default ChangeExplorerView;
