import React, { useState, useEffect } from 'react';
import { api, type Contradiction } from '../api';
import { AlertTriangle, Calendar, CheckCircle, ArrowRight, ShieldAlert } from 'lucide-react';

interface ContradictionViewProps {
  userId?: string;
}

export const ContradictionView: React.FC<ContradictionViewProps> = ({ userId = 'default_user' }) => {
  const [contradictions, setContradictions] = useState<Contradiction[]>([]);
  const [loading, setLoading] = useState(true);

  const loadContradictions = async () => {
    setLoading(true);
    try {
      const data = await api.getContradictions(userId);
      setContradictions(data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadContradictions();
  }, [userId]);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      {/* Header */}
      <div className="glass-panel" style={{ padding: '24px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '16px' }}>
          <div>
            <h2 style={{ fontSize: '18px', fontWeight: 700, display: 'flex', alignItems: 'center', gap: '10px', color: 'var(--text-main)' }}>
              <AlertTriangle size={20} style={{ color: 'var(--accent-rose)' }} />
              <span>Contradictions & Stance Inversions</span>
            </h2>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ fontSize: '11.5px', color: 'var(--text-dim)', fontWeight: 600 }}>
              {contradictions.length} Inversions Tracked
            </span>
          </div>
        </div>
      </div>

      {loading ? (
        <div style={{ padding: '40px', textAlign: 'center', color: 'var(--text-dim)' }}>
          Scanning memories for polarity inversions and reversals...
        </div>
      ) : contradictions.length === 0 ? (
        <div className="glass-panel" style={{ padding: '36px', textAlign: 'center', color: 'var(--text-muted)' }}>
          <CheckCircle size={32} style={{ color: 'var(--accent-emerald)', margin: '0 auto 12px' }} />
          <h4 style={{ fontSize: '15px', fontWeight: 600, color: 'var(--text-main)', marginBottom: '4px' }}>
            No Stance Inversions Detected
          </h4>
          <p style={{ fontSize: '13px', color: 'var(--text-dim)' }}>
            All documented perspectives in the archive maintain consistent polarity or progressive evolution.
          </p>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          {contradictions.map((c, idx) => (
            <div key={idx} className="glass-panel card-interactive" style={{ padding: '22px', display: 'flex', flexDirection: 'column', gap: '14px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '8px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <span className="badge badge-reversal">
                    Potential Stance Reversal
                  </span>
                  <span style={{ fontSize: '12px', color: 'var(--accent-rose)', fontWeight: 700, fontFamily: 'var(--font-mono)' }}>
                    {(c.confidence * 100).toFixed(0)}% Inversion Confidence
                  </span>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '12px', color: 'var(--text-dim)' }}>
                  <ShieldAlert size={14} style={{ color: 'var(--accent-rose)' }} />
                  <span>Epistemic Tension Detected</span>
                </div>
              </div>

              {/* Rationale */}
              <div style={{ fontSize: '14px', color: 'var(--text-main)', fontWeight: 600, lineHeight: '1.5' }}>
                {c.evidence_rationale}
              </div>

              {/* Side-by-side Evidence Cards */}
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '14px', alignItems: 'stretch' }}>
                {/* Earlier Stance */}
                <div style={{ padding: '16px', background: '#fff1f2', borderRadius: '8px', border: '1px solid #fecdd3', display: 'flex', flexDirection: 'column', gap: '8px' }}>
                  <div style={{ fontSize: '11px', fontWeight: 700, color: 'var(--accent-rose)', display: 'flex', justifyContent: 'space-between', alignItems: 'center', letterSpacing: '0.04em' }}>
                    <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                      <Calendar size={12} />
                      <span>EARLIER POSITION</span>
                    </span>
                    <span style={{ fontFamily: 'var(--font-mono)' }}>{c.source_date || 'Earlier Period'}</span>
                  </div>
                  <blockquote style={{ fontSize: '13.5px', color: '#9f1239', lineHeight: '1.55', fontStyle: 'italic', margin: 0, fontWeight: 500 }}>
                    "{c.source_statement}"
                  </blockquote>
                </div>

                {/* Later Stance */}
                <div style={{ padding: '16px', background: '#ecfdf5', borderRadius: '8px', border: '1px solid #a7f3d0', display: 'flex', flexDirection: 'column', gap: '8px' }}>
                  <div style={{ fontSize: '11px', fontWeight: 700, color: 'var(--accent-emerald)', display: 'flex', justifyContent: 'space-between', alignItems: 'center', letterSpacing: '0.04em' }}>
                    <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                      <ArrowRight size={12} />
                      <span>INVERTED POSITION</span>
                    </span>
                    <span style={{ fontFamily: 'var(--font-mono)' }}>{c.target_date || 'Later Period'}</span>
                  </div>
                  <blockquote style={{ fontSize: '13.5px', color: '#065f46', lineHeight: '1.55', fontStyle: 'italic', margin: 0, fontWeight: 500 }}>
                    "{c.target_statement}"
                  </blockquote>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default ContradictionView;
