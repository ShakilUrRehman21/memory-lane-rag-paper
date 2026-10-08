import React, { useState, useEffect } from 'react';
import { api, type VersionDiff } from '../api';
import { GitCompare, PlusCircle, MinusCircle, CheckCircle2, Sparkles } from 'lucide-react';

interface VersionDiffViewProps {
  userId?: string;
}

export const VersionDiffView: React.FC<VersionDiffViewProps> = ({ userId = 'default_user' }) => {
  const [series, setSeries] = useState('Resume');
  const [earlier, setEarlier] = useState('2019');
  const [later, setLater] = useState('2026');
  const [diff, setDiff] = useState<VersionDiff | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const presets = [
    { label: 'Resume: 2019 vs 2026', series: 'Resume', earlier: '2019', later: '2026' }
  ];

  const handleCompare = async (s = series, e = earlier, l = later) => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.getVersionDiff(s, e, l, userId);
      setDiff(data);
    } catch (err: any) {
      setError('Could not find version series matching these labels. Ensure documents with matching version names are uploaded.');
      setDiff(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    handleCompare();
  }, [userId]);

  const selectPreset = (p: typeof presets[0]) => {
    setSeries(p.series);
    setEarlier(p.earlier);
    setLater(p.later);
    handleCompare(p.series, p.earlier, p.later);
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      {/* Header & Controls */}
      <div className="glass-panel" style={{ padding: '24px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '16px', marginBottom: '16px' }}>
          <div>
            <h2 style={{ fontSize: '18px', fontWeight: 700, display: 'flex', alignItems: 'center', gap: '10px', color: 'var(--text-main)' }}>
              <GitCompare size={20} style={{ color: 'var(--accent-indigo)' }} />
              <span>Document Version Diff</span>
            </h2>
          </div>

          {/* Quick Presets */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ fontSize: '11px', fontWeight: 700, color: 'var(--text-dim)', letterSpacing: '0.04em' }}>
              PRESET:
            </span>
            {presets.map((p, idx) => (
              <button
                key={idx}
                className="btn btn-secondary"
                onClick={() => selectPreset(p)}
                style={{ padding: '4px 10px', fontSize: '12px', gap: '6px' }}
              >
                <Sparkles size={12} style={{ color: 'var(--accent-indigo)' }} />
                <span>{p.label}</span>
              </button>
            ))}
          </div>
        </div>

        {/* Input selectors */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '12px' }}>
          <div>
            <label style={{ fontSize: '11px', color: 'var(--text-dim)', fontWeight: 700, letterSpacing: '0.04em' }}>SERIES NAME</label>
            <input
              type="text"
              className="input-field"
              value={series}
              onChange={e => setSeries(e.target.value)}
              placeholder="e.g. Resume"
              style={{ marginTop: '4px' }}
            />
          </div>
          <div>
            <label style={{ fontSize: '11px', color: 'var(--text-dim)', fontWeight: 700, letterSpacing: '0.04em' }}>EARLIER VERSION</label>
            <input
              type="text"
              className="input-field"
              value={earlier}
              onChange={e => setEarlier(e.target.value)}
              placeholder="e.g. 2019"
              style={{ marginTop: '4px' }}
            />
          </div>
          <div>
            <label style={{ fontSize: '11px', color: 'var(--text-dim)', fontWeight: 700, letterSpacing: '0.04em' }}>LATER VERSION</label>
            <input
              type="text"
              className="input-field"
              value={later}
              onChange={e => setLater(e.target.value)}
              placeholder="e.g. 2026"
              style={{ marginTop: '4px' }}
            />
          </div>
          <div style={{ display: 'flex', alignItems: 'flex-end' }}>
            <button
              className="btn btn-primary"
              onClick={() => handleCompare()}
              disabled={loading}
              style={{ width: '100%', height: '39px' }}
            >
              <GitCompare size={15} />
              <span>{loading ? 'Comparing...' : 'Compare Versions'}</span>
            </button>
          </div>
        </div>
      </div>

      {error && (
        <div style={{ padding: '16px 20px', background: '#fffbeb', border: '1px solid #fde68a', borderRadius: '8px', color: '#92400e', fontSize: '13px' }}>
          {error}
        </div>
      )}

      {diff && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          {/* Summary Box */}
          <div className="glass-panel" style={{ padding: '20px 24px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <CheckCircle2 size={16} style={{ color: 'var(--accent-emerald)' }} />
                <span style={{ fontSize: '14.5px', fontWeight: 700, color: 'var(--text-main)' }}>
                  {diff.series_name}: {diff.earlier_version} vs {diff.later_version}
                </span>
              </div>
              <span style={{ fontSize: '11.5px', color: 'var(--text-dim)', fontFamily: 'var(--font-mono)' }}>
                {diff.earlier_version} → {diff.later_version}
              </span>
            </div>

            <div style={{ background: '#f8fafc', padding: '14px 18px', borderRadius: '8px', border: '1px solid var(--border-subtle)', fontSize: '13.5px', lineHeight: '1.6', color: 'var(--text-main)', marginBottom: '16px' }}>
              {diff.summary}
            </div>

            {/* Added & Removed Breakdown */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '16px' }}>
              {/* Added Items */}
              <div style={{ padding: '16px', background: '#ecfdf5', borderRadius: '8px', border: '1px solid #a7f3d0' }}>
                <div style={{ fontSize: '11.5px', fontWeight: 700, color: '#065f46', marginBottom: '10px', display: 'flex', alignItems: 'center', gap: '6px', letterSpacing: '0.04em' }}>
                  <PlusCircle size={14} />
                  <span>ADDED IN {diff.later_version} ({(diff.added_skills_or_topics || []).length})</span>
                </div>
                {(!diff.added_skills_or_topics || diff.added_skills_or_topics.length === 0) ? (
                  <span style={{ fontSize: '12px', color: 'var(--text-dim)' }}>No additions detected.</span>
                ) : (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                    {diff.added_skills_or_topics.map((item: string, idx: number) => (
                      <div key={idx} className="diff-line-add">
                        + {item}
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Removed Items */}
              <div style={{ padding: '16px', background: '#fff1f2', borderRadius: '8px', border: '1px solid #fecdd3' }}>
                <div style={{ fontSize: '11.5px', fontWeight: 700, color: '#9f1239', marginBottom: '10px', display: 'flex', alignItems: 'center', gap: '6px', letterSpacing: '0.04em' }}>
                  <MinusCircle size={14} />
                  <span>DEPRECATED / REMOVED ({(diff.removed_skills_or_topics || []).length})</span>
                </div>
                {(!diff.removed_skills_or_topics || diff.removed_skills_or_topics.length === 0) ? (
                  <span style={{ fontSize: '12px', color: 'var(--text-dim)' }}>No removals detected.</span>
                ) : (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                    {diff.removed_skills_or_topics.map((item: string, idx: number) => (
                      <div key={idx} className="diff-line-del">
                        - {item}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default VersionDiffView;
