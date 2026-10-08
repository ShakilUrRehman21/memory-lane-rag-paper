import React, { useState, useEffect, useMemo } from 'react';
import { api, type TimelinePoint } from '../api';
import {
  Clock, FileText, Search, X, ChevronRight,
  Filter, ShieldCheck
} from 'lucide-react';

const YEARS = [2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025, 2026];
const MEMORY_TYPES = ['all', 'belief', 'goal', 'decision', 'preference', 'event'];

interface TimelineViewProps {
  userId?: string;
}

export const TimelineView: React.FC<TimelineViewProps> = ({ userId = 'default_user' }) => {
  const [timeline, setTimeline] = useState<TimelinePoint[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedYear, setSelectedYear] = useState<number | null>(null);
  const [selectedType, setSelectedType] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [activeItem, setActiveItem] = useState<TimelinePoint | null>(null);

  const loadTimeline = async () => {
    setLoading(true);
    try {
      const data = await api.getTimeline(selectedYear || undefined, selectedYear || undefined, userId);
      setTimeline(data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadTimeline();
  }, [selectedYear, userId]);

  // Year counts histogram calculation
  const yearDistribution = useMemo(() => {
    const counts: Record<number, number> = {};
    YEARS.forEach(y => { counts[y] = 0; });
    timeline.forEach(item => {
      const y = parseInt(item.period?.slice(0, 4) || '2024', 10);
      if (counts[y] !== undefined) counts[y]++;
    });
    return counts;
  }, [timeline]);

  const maxYearCount = Math.max(...Object.values(yearDistribution), 1);

  const filteredItems = useMemo(() => {
    return timeline.filter(item => {
      const matchesType = selectedType === 'all' || item.memory_type.toLowerCase() === selectedType.toLowerCase();
      const matchesQuery = !searchQuery.trim() ||
        item.statement.toLowerCase().includes(searchQuery.toLowerCase()) ||
        item.document_title.toLowerCase().includes(searchQuery.toLowerCase()) ||
        item.period.toLowerCase().includes(searchQuery.toLowerCase());
      return matchesType && matchesQuery;
    });
  }, [timeline, selectedType, searchQuery]);

  const getBadgeClass = (type: string) => {
    switch (type.toLowerCase()) {
      case 'belief': return 'badge-belief';
      case 'goal': return 'badge-goal';
      case 'decision': return 'badge-decision';
      case 'preference': return 'badge-preference';
      default: return 'badge-event';
    }
  };

  const getTypeColor = (type: string) => {
    switch (type.toLowerCase()) {
      case 'belief': return '#0284c7';
      case 'goal': return '#059669';
      case 'decision': return '#7c3aed';
      case 'preference': return '#d97706';
      default: return '#64748b';
    }
  };

  const getStanceInfo = (polarity: number) => {
    if (polarity > 0.3) {
      return { label: `Advocating (+${polarity.toFixed(2)})`, cls: 'stance-positive' };
    }
    if (polarity < -0.3) {
      return { label: `Skeptical (${polarity.toFixed(2)})`, cls: 'stance-skeptical' };
    }
    return { label: `Neutral (${polarity.toFixed(2)})`, cls: 'stance-neutral' };
  };

  // Extract relevant topical tags from statement
  const extractTags = (text: string) => {
    const keywords = [
      'AI', 'Machine Learning', 'Python', 'PyTorch', 'Java', 'C++',
      'Distributed Systems', 'Transformers', 'FastAPI', 'Research',
      'Architecture', 'Databases', 'Interpretability', 'Neural'
    ];
    return keywords.filter(k => text.toLowerCase().includes(k.toLowerCase())).slice(0, 3);
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      {/* Header and Interactive Control Center */}
      <div className="glass-panel" style={{ padding: '24px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '16px', marginBottom: '16px' }}>
          <div>
            <h2 style={{ fontSize: '18px', fontWeight: 700, display: 'flex', alignItems: 'center', gap: '10px', color: 'var(--text-main)' }}>
              <Clock size={20} style={{ color: 'var(--accent-primary)' }} />
              <span>Visual Timeline</span>
            </h2>
          </div>

          {/* Search bar */}
          <div style={{ position: 'relative', width: '280px' }}>
            <Search size={14} style={{ position: 'absolute', left: '10px', top: '10px', color: 'var(--text-dim)' }} />
            <input
              type="text"
              placeholder="Filter timeline statements or docs..."
              className="input-field"
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
              style={{ paddingLeft: '32px', height: '34px', fontSize: '12.5px' }}
            />
          </div>
        </div>

        {/* Interactive Year Histogram Scrubber Bar */}
        <div style={{ background: '#f8fafc', padding: '14px 18px', borderRadius: '10px', border: '1px solid var(--border-subtle)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
            <span style={{ fontSize: '11px', fontWeight: 700, color: 'var(--text-dim)', letterSpacing: '0.04em' }}>
              TEMPORAL DENSITY SCRUBBER
            </span>
            <button
              onClick={() => setSelectedYear(null)}
              style={{
                background: selectedYear === null ? '#eff6ff' : 'transparent',
                color: selectedYear === null ? 'var(--accent-primary)' : 'var(--text-dim)',
                border: 'none',
                borderRadius: '5px',
                padding: '2px 8px',
                fontSize: '11px',
                fontWeight: 600,
                cursor: 'pointer'
              }}
            >
              Reset to All Years
            </button>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: `repeat(${YEARS.length}, 1fr)`, gap: '8px', alignItems: 'flex-end', height: '64px', paddingTop: '8px' }}>
            {YEARS.map(year => {
              const count = yearDistribution[year] || 0;
              const heightPct = Math.max((count / maxYearCount) * 100, 10);
              const isSelected = selectedYear === year;

              return (
                <div
                  key={year}
                  onClick={() => setSelectedYear(selectedYear === year ? null : year)}
                  style={{
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'center',
                    gap: '6px',
                    cursor: 'pointer',
                    height: '100%',
                    justifyContent: 'flex-end'
                  }}
                  title={`${year}: ${count} memories`}
                >
                  <div
                    style={{
                      width: '100%',
                      maxWidth: '36px',
                      height: `${heightPct}%`,
                      background: isSelected
                        ? 'linear-gradient(180deg, #2563eb 0%, #1d4ed8 100%)'
                        : count > 0
                        ? '#cbd5e1'
                        : '#e2e8f0',
                      borderRadius: '4px 4px 0 0',
                      transition: 'all 0.2s cubic-bezier(0.16, 1, 0.3, 1)',
                      boxShadow: isSelected ? '0 0 0 2px #93c5fd' : 'none'
                    }}
                  />
                  <span style={{
                    fontSize: '11px',
                    fontWeight: isSelected ? 800 : 500,
                    color: isSelected ? 'var(--accent-primary)' : 'var(--text-dim)',
                    fontFamily: 'var(--font-mono)'
                  }}>
                    {year}
                  </span>
                </div>
              );
            })}
          </div>
        </div>

        {/* Type Filter Pills Row */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '10px', marginTop: '14px', paddingTop: '12px', borderTop: '1px solid var(--border-subtle)' }}>
          <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap', alignItems: 'center' }}>
            <span style={{ fontSize: '11px', color: 'var(--text-dim)', fontWeight: 700, letterSpacing: '0.04em', display: 'flex', alignItems: 'center', gap: '4px' }}>
              <Filter size={11} />
              <span>TYPE:</span>
            </span>
            {MEMORY_TYPES.map(type => (
              <button
                key={type}
                onClick={() => setSelectedType(type)}
                style={{
                  padding: '3px 10px',
                  borderRadius: '6px',
                  border: '1px solid var(--border-subtle)',
                  background: selectedType === type ? '#eff6ff' : '#ffffff',
                  color: selectedType === type ? 'var(--accent-primary)' : 'var(--text-muted)',
                  borderColor: selectedType === type ? '#bfdbfe' : 'var(--border-subtle)',
                  fontSize: '12px',
                  fontWeight: selectedType === type ? 700 : 500,
                  cursor: 'pointer',
                  textTransform: 'capitalize',
                  transition: 'all 0.15s ease'
                }}
              >
                {type}
              </button>
            ))}
          </div>

          <span style={{ fontSize: '11.5px', color: 'var(--text-dim)', fontWeight: 600 }}>
            Showing {filteredItems.length} entries {selectedYear ? `(${selectedYear})` : ''}
          </span>
        </div>
      </div>

      {/* Timeline Stream */}
      <div style={{ position: 'relative', paddingLeft: '32px' }}>
        {/* Central Spine */}
        <div
          style={{
            position: 'absolute',
            left: '11px',
            top: '16px',
            bottom: '16px',
            width: '2px',
            background: 'var(--border-medium)'
          }}
        />

        {loading ? (
          <div style={{ padding: '50px', textAlign: 'center', color: 'var(--text-dim)' }}>
            Loading chronological memories...
          </div>
        ) : filteredItems.length === 0 ? (
          <div className="glass-panel" style={{ padding: '36px', textAlign: 'center', color: 'var(--text-muted)' }}>
            No memories match your active filters or search terms.
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
            {filteredItems.map((item, idx) => {
              const typeColor = getTypeColor(item.memory_type);
              const stance = getStanceInfo(item.stance_polarity);
              const tags = extractTags(item.statement);

              return (
                <div key={idx} style={{ position: 'relative' }}>
                  {/* Spine Node Dot */}
                  <div
                    style={{
                      position: 'absolute',
                      left: '-26px',
                      top: '18px',
                      width: '12px',
                      height: '12px',
                      borderRadius: '50%',
                      background: '#ffffff',
                      border: `2.5px solid ${typeColor}`,
                      boxShadow: `0 0 0 3px ${typeColor}25`
                    }}
                  />

                  {/* Card with interactive click */}
                  <div
                    className="glass-panel card-interactive"
                    onClick={() => setActiveItem(item)}
                    style={{
                      padding: '16px 20px',
                      display: 'flex',
                      flexDirection: 'column',
                      gap: '10px',
                      cursor: 'pointer',
                      borderLeft: `4px solid ${typeColor}`
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '8px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <span style={{ fontSize: '13.5px', fontWeight: 800, color: 'var(--text-main)', fontFamily: 'var(--font-mono)' }}>
                          {item.period}
                        </span>
                        <span className={`badge ${getBadgeClass(item.memory_type)}`}>
                          {item.memory_type}
                        </span>
                        <span style={{ fontSize: '11.5px', color: 'var(--text-dim)' }}>
                          {item.date_display}
                        </span>
                      </div>

                      <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                        <span className={`stance-pill ${stance.cls}`}>
                          {stance.label}
                        </span>

                        <span style={{ color: 'var(--text-dim)', fontSize: '11.5px', display: 'flex', alignItems: 'center', gap: '4px' }}>
                          <FileText size={12} style={{ color: 'var(--text-dim)' }} />
                          <span>{item.document_title}</span>
                        </span>

                        <ChevronRight size={14} style={{ color: 'var(--text-tertiary)' }} />
                      </div>
                    </div>

                    <p style={{ fontSize: '14px', color: 'var(--text-main)', lineHeight: '1.6', margin: 0, fontWeight: 500 }}>
                      "{item.statement}"
                    </p>

                    {/* Bottom strip: Extracted tags & Confidence */}
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '8px', paddingTop: '6px', borderTop: '1px solid var(--border-subtle)' }}>
                      <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap', alignItems: 'center' }}>
                        {tags.map((tag, tIdx) => (
                          <span key={tIdx} className="entity-tag">
                            #{tag.toLowerCase().replace(/\s+/g, '-')}
                          </span>
                        ))}
                      </div>

                      <span style={{ fontSize: '11px', color: 'var(--text-dim)', display: 'flex', alignItems: 'center', gap: '4px' }}>
                        <ShieldCheck size={12} style={{ color: 'var(--accent-emerald)' }} />
                        <span>Confidence: {(item.confidence * 100).toFixed(0)}%</span>
                      </span>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Interactive Detail Drawer Modal */}
      {activeItem && (
        <div style={{
          position: 'fixed',
          inset: 0,
          background: 'rgba(15, 23, 42, 0.45)',
          backdropFilter: 'blur(6px)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 1000,
          padding: '20px'
        }}>
          <div className="glass-panel" style={{
            width: '100%',
            maxWidth: '560px',
            padding: '24px',
            border: '1px solid var(--border-subtle)',
            boxShadow: 'var(--shadow-xl)',
            background: '#ffffff'
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span className={`badge ${getBadgeClass(activeItem.memory_type)}`}>
                  {activeItem.memory_type}
                </span>
                <span style={{ fontSize: '13px', fontWeight: 800, color: 'var(--accent-primary)', fontFamily: 'var(--font-mono)' }}>
                  {activeItem.period}
                </span>
              </div>
              <button
                onClick={() => setActiveItem(null)}
                style={{ background: 'transparent', border: 'none', cursor: 'pointer', color: 'var(--text-dim)' }}
              >
                <X size={18} />
              </button>
            </div>

            <div style={{
              background: '#f8fafc',
              border: '1px solid var(--border-subtle)',
              borderRadius: '8px',
              padding: '16px',
              marginBottom: '16px'
            }}>
              <p style={{ fontSize: '14.5px', color: 'var(--text-main)', lineHeight: '1.6', margin: 0, fontWeight: 500 }}>
                "{activeItem.statement}"
              </p>
            </div>

            {/* Metadata inspection grid */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px', fontSize: '12px', marginBottom: '16px' }}>
              <div style={{ padding: '10px', background: '#ffffff', border: '1px solid var(--border-subtle)', borderRadius: '6px' }}>
                <div style={{ color: 'var(--text-dim)', fontWeight: 700, fontSize: '10.5px', textTransform: 'uppercase', marginBottom: '2px' }}>Event Date</div>
                <div style={{ fontWeight: 600, color: 'var(--text-main)' }}>{activeItem.event_date}</div>
              </div>
              <div style={{ padding: '10px', background: '#ffffff', border: '1px solid var(--border-subtle)', borderRadius: '6px' }}>
                <div style={{ color: 'var(--text-dim)', fontWeight: 700, fontSize: '10.5px', textTransform: 'uppercase', marginBottom: '2px' }}>Source Document</div>
                <div style={{ fontWeight: 600, color: 'var(--text-main)' }}>{activeItem.document_title}</div>
              </div>
              <div style={{ padding: '10px', background: '#ffffff', border: '1px solid var(--border-subtle)', borderRadius: '6px' }}>
                <div style={{ color: 'var(--text-dim)', fontWeight: 700, fontSize: '10.5px', textTransform: 'uppercase', marginBottom: '2px' }}>Date Extraction Confidence</div>
                <div style={{ fontWeight: 600, color: 'var(--accent-emerald)' }}>{(activeItem.confidence * 100).toFixed(0)}% Verified</div>
              </div>
              <div style={{ padding: '10px', background: '#ffffff', border: '1px solid var(--border-subtle)', borderRadius: '6px' }}>
                <div style={{ color: 'var(--text-dim)', fontWeight: 700, fontSize: '10.5px', textTransform: 'uppercase', marginBottom: '2px' }}>Stance Polarity</div>
                <div style={{ fontWeight: 600, color: activeItem.stance_polarity >= 0 ? '#059669' : '#e11d48' }}>
                  {activeItem.stance_polarity > 0 ? `+${activeItem.stance_polarity.toFixed(2)}` : activeItem.stance_polarity.toFixed(2)}
                </div>
              </div>
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px' }}>
              <button
                className="btn btn-secondary"
                onClick={() => setActiveItem(null)}
              >
                Close Inspector
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default TimelineView;
