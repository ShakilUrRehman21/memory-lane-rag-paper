import React, { useState } from 'react';
import { api, type QueryResponse, type GroundedClaim } from '../api';
import {
  Send, Clock, AlertTriangle, ShieldCheck,
  ArrowRight, Layers, Copy, Check, Calendar,
  Compass, TrendingUp, Database, FileText,
  Sparkles, ExternalLink
} from 'lucide-react';

interface AskMemoryLaneViewProps {
  userId?: string;
}

export const AskMemoryLaneView: React.FC<AskMemoryLaneViewProps> = ({ userId = 'default_user' }) => {
  const [query, setQuery] = useState('');
  const [pipeline, setPipeline] = useState<'memory_lane' | 'temporal' | 'baseline'>('memory_lane');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<QueryResponse | null>(null);
  const [activeTab, setActiveTab] = useState<'chronology' | 'evidence' | 'shifts'>('chronology');
  const [activeClaim, setActiveClaim] = useState<GroundedClaim | null>(null);
  const [copied, setCopied] = useState(false);

  const curatedTopics = [
    {
      title: 'AI Architecture Evolution',
      category: 'Belief Stance',
      query: 'How has my thinking about AI changed?',
      color: '#0284c7',
      bg: '#f0f9ff'
    },
    {
      title: 'Career & Strategic Horizons',
      category: 'Goal Trajectory',
      query: 'What changed between my 2020 and 2026 goals?',
      color: '#059669',
      bg: '#ecfdf5'
    },
    {
      title: 'Tooling & Stack Decisions',
      category: 'Preference & Tech',
      query: 'What did I think about Java in 2022?',
      color: '#7c3aed',
      bg: '#f5f3ff'
    }
  ];

  const handleSearch = async (queryText?: string) => {
    const q = queryText || query;
    if (!q.trim()) return;
    setLoading(true);
    setActiveClaim(null);

    try {
      const data = await api.ask(q, pipeline, 8, userId);
      setResult(data);
      if (data.grounded_claims.length > 0) {
        setActiveClaim(data.grounded_claims[0]);
      }
    } catch (err) {
      console.error(err);
      alert('Failed to execute query. Check that the backend server is running.');
    } finally {
      setLoading(false);
    }
  };

  const handleCopyAnswer = () => {
    if (!result?.answer) return;
    navigator.clipboard.writeText(result.answer);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const getMemoryBadgeClass = (type: string) => {
    switch (type.toLowerCase()) {
      case 'belief': return 'badge-belief';
      case 'goal': return 'badge-goal';
      case 'decision': return 'badge-decision';
      case 'preference': return 'badge-preference';
      default: return 'badge-event';
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

  // Helper to cleanly parse answer text into structured sections
  const parseAnswerSections = (rawAnswer: string) => {
    const lines = rawAnswer.split('\n').map(l => l.trim()).filter(Boolean);
    const overviewLines: string[] = [];
    const milestoneLines: { date: string; text: string; source: string }[] = [];
    const shiftLines: string[] = [];
    const reversalLines: string[] = [];

    let currentSection: 'overview' | 'milestones' | 'shifts' | 'reversals' = 'overview';

    for (const line of lines) {
      if (line.includes('Identified Transitions & Shifts')) {
        currentSection = 'shifts';
        continue;
      }
      if (line.includes('Potential Stance Reversals')) {
        currentSection = 'reversals';
        continue;
      }

      // Check if line is a bullet milestone: • **YYYY-MM**: Statement *(Source: ...)*
      const bulletMatch = line.match(/^•\s*\*\*([^*]+)\*\*:\s*(.*?)(?:\s*\*\((?:Source:\s*)?([^*]+)\)\*)?$/);
      if (bulletMatch) {
        currentSection = 'milestones';
        milestoneLines.push({
          date: bulletMatch[1].trim(),
          text: bulletMatch[2].trim(),
          source: (bulletMatch[3] || 'Document').trim()
        });
        continue;
      }

      if (currentSection === 'shifts' && (line.startsWith('-') || line.startsWith('•'))) {
        shiftLines.push(line.replace(/^[-•]\s*/, ''));
        continue;
      }

      if (currentSection === 'reversals' && (line.startsWith('-') || line.startsWith('•'))) {
        reversalLines.push(line.replace(/^[-•]\s*/, ''));
        continue;
      }

      if (currentSection === 'overview') {
        overviewLines.push(line);
      }
    }

    return {
      overview: overviewLines.join(' '),
      milestones: milestoneLines,
      shifts: shiftLines,
      reversals: reversalLines
    };
  };

  const parsed = result?.answer ? parseAnswerSections(result.answer) : null;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      {/* Visual Metric Stat Strip */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '12px' }}>
        <div className="glass-panel" style={{ padding: '14px 18px', display: 'flex', alignItems: 'center', gap: '12px' }}>
          <div style={{ width: '36px', height: '36px', borderRadius: '8px', background: '#eff6ff', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#2563eb' }}>
            <Calendar size={18} />
          </div>
          <div>
            <div style={{ fontSize: '11px', fontWeight: 700, color: 'var(--text-dim)', letterSpacing: '0.04em' }}>COGNITIVE HORIZON</div>
            <div style={{ fontSize: '15px', fontWeight: 800, color: 'var(--text-main)' }}>2019 — 2026</div>
          </div>
        </div>

        <div className="glass-panel" style={{ padding: '14px 18px', display: 'flex', alignItems: 'center', gap: '12px' }}>
          <div style={{ width: '36px', height: '36px', borderRadius: '8px', background: '#ecfdf5', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#059669' }}>
            <Database size={18} />
          </div>
          <div>
            <div style={{ fontSize: '11px', fontWeight: 700, color: 'var(--text-dim)', letterSpacing: '0.04em' }}>INDEXED MEMORIES</div>
            <div style={{ fontSize: '15px', fontWeight: 800, color: 'var(--text-main)' }}>16 Quad-Date TMUs</div>
          </div>
        </div>

        <div className="glass-panel" style={{ padding: '14px 18px', display: 'flex', alignItems: 'center', gap: '12px' }}>
          <div style={{ width: '36px', height: '36px', borderRadius: '8px', background: '#f5f3ff', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#7c3aed' }}>
            <TrendingUp size={18} />
          </div>
          <div>
            <div style={{ fontSize: '11px', fontWeight: 700, color: 'var(--text-dim)', letterSpacing: '0.04em' }}>TRACKED REVERSALS</div>
            <div style={{ fontSize: '15px', fontWeight: 800, color: 'var(--text-main)' }}>3 Inflections</div>
          </div>
        </div>

        <div className="glass-panel" style={{ padding: '14px 18px', display: 'flex', alignItems: 'center', gap: '12px' }}>
          <div style={{ width: '36px', height: '36px', borderRadius: '8px', background: '#f0f9ff', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#0284c7' }}>
            <ShieldCheck size={18} />
          </div>
          <div>
            <div style={{ fontSize: '11px', fontWeight: 700, color: 'var(--text-dim)', letterSpacing: '0.04em' }}>CITATION RIGOR</div>
            <div style={{ fontSize: '15px', fontWeight: 800, color: 'var(--text-main)' }}>100% Grounded</div>
          </div>
        </div>
      </div>

      {/* Modern Search & Pipeline Input */}
      <div className="glass-panel" style={{ padding: '20px 24px' }}>
        <div style={{ display: 'flex', gap: '10px' }}>
          <div style={{ position: 'relative', flex: 1 }}>
            <input
              type="text"
              className="input-field"
              placeholder="Query historical perspectives, career shifts, or stance evolutions..."
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
              style={{ padding: '11px 16px', fontSize: '14.5px' }}
            />
          </div>

          <button
            className="btn btn-primary"
            onClick={() => handleSearch()}
            disabled={loading || !query.trim()}
            style={{ padding: '11px 20px', minWidth: '108px' }}
          >
            {loading ? <Clock size={16} className="spin" /> : <Send size={16} />}
            <span>{loading ? 'Synthesizing...' : 'Inquire'}</span>
          </button>
        </div>

        {/* Pipeline selector row */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '14px', flexWrap: 'wrap', gap: '8px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ fontSize: '11px', color: 'var(--text-dim)', fontWeight: 700, letterSpacing: '0.03em' }}>REASONING ENGINE:</span>
            <div style={{ display: 'flex', background: '#f1f5f9', padding: '2px', borderRadius: '6px', border: '1px solid var(--border-subtle)' }}>
              {[
                { id: 'memory_lane', label: 'Longitudinal Memory Lane' },
                { id: 'temporal', label: 'Temporal Only' },
                { id: 'baseline', label: 'Baseline RAG' }
              ].map(p => (
                <button
                  key={p.id}
                  onClick={() => setPipeline(p.id as any)}
                  style={{
                    padding: '3px 10px',
                    borderRadius: '5px',
                    border: 'none',
                    fontSize: '11.5px',
                    fontWeight: 600,
                    cursor: 'pointer',
                    background: pipeline === p.id ? '#ffffff' : 'transparent',
                    color: pipeline === p.id ? 'var(--accent-primary)' : 'var(--text-dim)',
                    boxShadow: pipeline === p.id ? 'var(--shadow-xs)' : 'none',
                    transition: 'all 0.15s ease'
                  }}
                >
                  {p.label}
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* If No Query Has Run Yet: Interactive Curated Topic Cards */}
      {!result && !loading && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Compass size={16} style={{ color: 'var(--accent-primary)' }} />
            <span style={{ fontSize: '13px', fontWeight: 700, color: 'var(--text-main)', letterSpacing: '0.02em' }}>
              RECOMMENDED INQUIRIES
            </span>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '14px' }}>
            {curatedTopics.map((topic, i) => (
              <div
                key={i}
                className="glass-panel interactive-card"
                onClick={() => { setQuery(topic.query); handleSearch(topic.query); }}
                style={{
                  padding: '18px 20px',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '8px',
                  borderLeft: `4px solid ${topic.color}`
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ fontSize: '11px', fontWeight: 700, color: topic.color, background: topic.bg, padding: '2px 8px', borderRadius: '4px' }}>
                    {topic.category}
                  </span>
                  <ArrowRight size={14} style={{ color: topic.color }} />
                </div>
                <h4 style={{ fontSize: '14px', fontWeight: 700, color: 'var(--text-main)' }}>
                  {topic.title}
                </h4>
                <p style={{ fontSize: '12.5px', color: 'var(--text-muted)', lineHeight: '1.45', margin: 0 }}>
                  "{topic.query}"
                </p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Query Loading State */}
      {loading && (
        <div className="glass-panel" style={{ padding: '40px', textAlign: 'center', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '12px' }}>
          <div style={{ width: '40px', height: '40px', borderRadius: '50%', background: '#eff6ff', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#2563eb' }}>
            <Clock size={20} />
          </div>
          <span style={{ fontSize: '14px', fontWeight: 600, color: 'var(--text-main)' }}>
            Synthesizing longitudinal perspective...
          </span>
          <span style={{ fontSize: '12px', color: 'var(--text-dim)' }}>
            Retrieving chronological memory fragments and aligning semantic drift
          </span>
        </div>
      )}

      {/* Query Results View */}
      {result && !loading && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '18px' }}>
          {/* Main Answer Header & Executive Synthesis Card */}
          <div className="glass-panel" style={{ padding: '22px 24px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px', borderBottom: '1px solid var(--border-subtle)', paddingBottom: '14px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
                <span className="badge badge-belief">{result.detected_intent}</span>
                <span style={{ fontSize: '11.5px', color: 'var(--text-dim)' }}>
                  {result.execution_time_ms}ms · {result.timeline.length} milestone points
                </span>
                <span style={{ fontSize: '11.5px', color: 'var(--accent-emerald)', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '4px' }}>
                  <ShieldCheck size={13} />
                  <span>Grounding Verified</span>
                </span>
              </div>

              <button
                onClick={handleCopyAnswer}
                className="btn btn-secondary"
                style={{ padding: '4px 10px', fontSize: '11.5px', gap: '5px' }}
              >
                {copied ? <Check size={13} style={{ color: 'var(--accent-emerald)' }} /> : <Copy size={13} />}
                <span>{copied ? 'Copied' : 'Copy'}</span>
              </button>
            </div>

            {/* Executive Synthesis Lead Paragraph */}
            {parsed?.overview && (
              <div style={{
                background: '#f8fafc',
                border: '1px solid var(--border-subtle)',
                borderRadius: '8px',
                padding: '16px 18px',
                marginBottom: '20px',
                borderLeft: '4px solid var(--accent-primary)'
              }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '6px' }}>
                  <Sparkles size={14} style={{ color: 'var(--accent-primary)' }} />
                  <span style={{ fontSize: '11px', fontWeight: 700, color: 'var(--accent-primary)', letterSpacing: '0.04em' }}>
                    EXECUTIVE LONGITUDINAL SYNTHESIS
                  </span>
                </div>
                <p style={{ fontSize: '14px', lineHeight: '1.65', color: 'var(--text-main)', margin: 0, fontWeight: 500 }}>
                  {parsed.overview}
                </p>
              </div>
            )}

            {/* Chronological Milestone Journey (Parsed Visual Cards) */}
            {parsed && parsed.milestones.length > 0 ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', marginBottom: '16px' }}>
                <div style={{ fontSize: '11.5px', fontWeight: 700, color: 'var(--text-dim)', letterSpacing: '0.04em', marginBottom: '4px' }}>
                  CHRONOLOGICAL PROGRESSION
                </div>
                <div className="stepper-container">
                  {parsed.milestones.map((m, idx) => {
                    // Try to match corresponding timeline point for stance
                    const matchedTp = result.timeline.find(t => t.period === m.date || t.date_display.startsWith(m.date));
                    const stance = matchedTp ? getStanceInfo(matchedTp.stance_polarity) : null;
                    const memType = matchedTp?.memory_type || 'observation';

                    return (
                      <div key={idx} className="stepper-item">
                        <div className="stepper-spine" />
                        <div className="stepper-node">
                          {idx + 1}
                        </div>
                        <div className="stepper-content">
                          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '8px', marginBottom: '6px' }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                              <span style={{ fontSize: '13px', fontWeight: 800, color: 'var(--accent-primary)', fontFamily: 'var(--font-mono)' }}>
                                {m.date}
                              </span>
                              <span className={`badge ${getMemoryBadgeClass(memType)}`}>
                                {memType}
                              </span>
                            </div>

                            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                              {stance && (
                                <span className={`stance-pill ${stance.cls}`}>
                                  {stance.label}
                                </span>
                              )}
                              <span style={{ fontSize: '11.5px', color: 'var(--text-dim)', display: 'flex', alignItems: 'center', gap: '4px' }}>
                                <FileText size={12} />
                                <span>{m.source}</span>
                              </span>
                            </div>
                          </div>

                          <p style={{ fontSize: '13.5px', color: 'var(--text-main)', lineHeight: '1.6', margin: 0 }}>
                            "{m.text}"
                          </p>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            ) : (
              /* Fallback if answer wasn't formatted as bullets */
              <div style={{ fontSize: '14px', lineHeight: '1.7', color: 'var(--text-main)', whiteSpace: 'pre-wrap', marginBottom: '16px' }}>
                {result.answer}
              </div>
            )}

            {/* Identified Transitions Strip if detected in answer */}
            {parsed && parsed.shifts.length > 0 && (
              <div style={{ marginTop: '16px', background: '#f5f3ff', border: '1px solid #ddd6fe', borderRadius: '8px', padding: '14px 16px' }}>
                <div style={{ fontSize: '11px', fontWeight: 700, color: 'var(--accent-violet)', letterSpacing: '0.04em', marginBottom: '8px' }}>
                  IDENTIFIED PERSPECTIVE SHIFTS
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                  {parsed.shifts.map((s, idx) => (
                    <div key={idx} style={{ fontSize: '12.5px', color: 'var(--text-main)', display: 'flex', alignItems: 'flex-start', gap: '8px' }}>
                      <ArrowRight size={14} style={{ color: 'var(--accent-violet)', marginTop: '2px', flexShrink: 0 }} />
                      <span>{s}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Uncertainty callout if applicable */}
            {result.uncertainty_notes.length > 0 && (
              <div style={{
                marginTop: '16px',
                padding: '12px 14px',
                background: '#fffbeb',
                border: '1px solid #fde68a',
                borderRadius: '8px',
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                fontSize: '12px',
                color: '#92400e'
              }}>
                <AlertTriangle size={15} style={{ flexShrink: 0, color: 'var(--accent-amber)' }} />
                <span>{result.uncertainty_notes[0]}</span>
              </div>
            )}
          </div>

          {/* Deep Dive Segmented Workspace */}
          <div className="glass-panel" style={{ padding: '20px 24px' }}>
            <div style={{ display: 'flex', gap: '8px', borderBottom: '1px solid var(--border-subtle)', paddingBottom: '12px', marginBottom: '16px' }}>
              <button
                onClick={() => setActiveTab('chronology')}
                style={{
                  padding: '5px 12px',
                  borderRadius: '6px',
                  border: 'none',
                  fontSize: '12.5px',
                  fontWeight: 600,
                  cursor: 'pointer',
                  background: activeTab === 'chronology' ? '#eff6ff' : 'transparent',
                  color: activeTab === 'chronology' ? 'var(--accent-primary)' : 'var(--text-dim)',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px'
                }}
              >
                <Clock size={14} />
                <span>Milestone Grid ({result.timeline.length})</span>
              </button>

              <button
                onClick={() => setActiveTab('evidence')}
                style={{
                  padding: '5px 12px',
                  borderRadius: '6px',
                  border: 'none',
                  fontSize: '12.5px',
                  fontWeight: 600,
                  cursor: 'pointer',
                  background: activeTab === 'evidence' ? '#eff6ff' : 'transparent',
                  color: activeTab === 'evidence' ? 'var(--accent-primary)' : 'var(--text-dim)',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px'
                }}
              >
                <ShieldCheck size={14} />
                <span>Evidence & Citations ({result.grounded_claims.length})</span>
              </button>

              {result.detected_changes.length > 0 && (
                <button
                  onClick={() => setActiveTab('shifts')}
                  style={{
                    padding: '5px 12px',
                    borderRadius: '6px',
                    border: 'none',
                    fontSize: '12.5px',
                    fontWeight: 600,
                    cursor: 'pointer',
                    background: activeTab === 'shifts' ? '#eff6ff' : 'transparent',
                    color: activeTab === 'shifts' ? 'var(--accent-primary)' : 'var(--text-dim)',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '6px'
                  }}
                >
                  <Layers size={14} />
                  <span>Detected Shifts ({result.detected_changes.length})</span>
                </button>
              )}
            </div>

            {/* TAB 1: Chronological Grid */}
            {activeTab === 'chronology' && (
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '12px' }}>
                {result.timeline.map((tp, idx) => {
                  const stance = getStanceInfo(tp.stance_polarity);
                  return (
                    <div
                      key={idx}
                      className="glass-panel card-interactive"
                      style={{
                        padding: '14px 16px',
                        background: '#ffffff',
                        borderRadius: '8px',
                        border: '1px solid var(--border-subtle)',
                        display: 'flex',
                        flexDirection: 'column',
                        gap: '8px'
                      }}
                    >
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <span style={{ fontSize: '13.5px', fontWeight: 800, color: 'var(--accent-primary)', fontFamily: 'var(--font-mono)' }}>
                          {tp.period}
                        </span>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                          <span className={`badge ${getMemoryBadgeClass(tp.memory_type)}`}>{tp.memory_type}</span>
                          <span className={`stance-pill ${stance.cls}`}>{stance.label}</span>
                        </div>
                      </div>

                      <p style={{ fontSize: '12.5px', color: 'var(--text-main)', lineHeight: '1.5', margin: 0 }}>
                        "{tp.statement}"
                      </p>

                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: 'auto', paddingTop: '8px', borderTop: '1px solid var(--border-subtle)', fontSize: '11px', color: 'var(--text-dim)' }}>
                        <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                          <FileText size={12} />
                          <span>{tp.document_title}</span>
                        </span>
                        <span>{tp.date_display}</span>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}

            {/* TAB 2: Evidence & Grounding */}
            {activeTab === 'evidence' && (
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
                {/* Claims list */}
                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                  {result.grounded_claims.map((claim, idx) => {
                    const isSelected = activeClaim?.claim_id === claim.claim_id;
                    return (
                      <div
                        key={idx}
                        onClick={() => setActiveClaim(claim)}
                        style={{
                          padding: '10px 12px',
                          borderRadius: '8px',
                          background: isSelected ? '#eff6ff' : '#f8fafc',
                          border: `1px solid ${isSelected ? '#93c5fd' : 'var(--border-subtle)'}`,
                          cursor: 'pointer',
                          transition: 'all 0.15s ease'
                        }}
                      >
                        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '3px' }}>
                          <span style={{ fontSize: '11px', fontWeight: 700, color: isSelected ? 'var(--accent-primary)' : 'var(--text-dim)' }}>
                            Claim #{idx + 1}
                          </span>
                          <span style={{ fontSize: '10.5px', color: 'var(--accent-emerald)', fontWeight: 600 }}>
                            {(claim.confidence * 100).toFixed(0)}% conf
                          </span>
                        </div>
                        <p style={{ fontSize: '12px', color: 'var(--text-main)', margin: 0, lineHeight: '1.4' }}>
                          {claim.claim_text}
                        </p>
                      </div>
                    );
                  })}
                </div>

                {/* Active Citation passage */}
                <div>
                  {activeClaim ? (
                    <div style={{ padding: '16px', background: '#f8fafc', borderRadius: '8px', border: '1px solid var(--border-subtle)', height: '100%' }}>
                      <div style={{ fontSize: '11px', fontWeight: 700, color: 'var(--text-dim)', textTransform: 'uppercase', marginBottom: '8px', letterSpacing: '0.04em' }}>
                        SOURCE PASSAGE CITATION
                      </div>
                      {activeClaim.source_citations.length > 0 ? (
                        activeClaim.source_citations.map((cite, cIdx) => (
                          <div key={cIdx} style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
                            <div style={{ fontSize: '11px', color: 'var(--accent-primary)', fontWeight: 600, marginBottom: '6px', display: 'flex', alignItems: 'center', gap: '4px' }}>
                              <ExternalLink size={12} />
                              <span>{cite.document_title} ({cite.date})</span>
                            </div>
                            <blockquote style={{ borderLeft: '3px solid var(--accent-primary)', paddingLeft: '10px', fontStyle: 'italic', color: 'var(--text-main)', margin: 0, background: '#ffffff', padding: '8px 10px', borderRadius: '0 4px 4px 0', border: '1px solid var(--border-subtle)', borderLeftWidth: '3px', borderLeftColor: 'var(--accent-primary)' }}>
                              "{cite.statement}"
                            </blockquote>
                          </div>
                        ))
                      ) : (
                        <div style={{ fontSize: '12px', color: 'var(--text-dim)', fontStyle: 'italic' }}>
                          Inferred longitudinal change relation grounded across multiple temporal anchor points.
                        </div>
                      )}
                    </div>
                  ) : (
                    <div style={{ padding: '30px', textAlign: 'center', color: 'var(--text-dim)', fontSize: '12px' }}>
                      Select a claim from the left to view exact document citation
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* TAB 3: Detected Shifts */}
            {activeTab === 'shifts' && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                {result.detected_changes.map((cp, idx) => (
                  <div key={idx} style={{ padding: '14px', background: '#f8fafc', borderRadius: '8px', border: '1px solid var(--border-subtle)', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '8px' }}>
                    <div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
                        <span style={{ fontSize: '13px', fontWeight: 700, color: 'var(--text-main)' }}>{cp.topic_or_entity}</span>
                        <span className="badge badge-reversal">{cp.change_type}</span>
                        <span style={{ fontSize: '11px', color: 'var(--text-dim)' }}>
                          {cp.from_period.slice(0, 7)} → {cp.to_period.slice(0, 7)}
                        </span>
                      </div>
                      <p style={{ fontSize: '12px', color: 'var(--text-muted)', margin: 0 }}>
                        From: "{cp.earlier_statement}" → To: "{cp.later_statement}"
                      </p>
                    </div>
                    <span style={{ fontSize: '12px', fontWeight: 700, color: 'var(--accent-amber)', background: '#fffbeb', border: '1px solid #fde68a', padding: '2px 8px', borderRadius: '4px' }}>
                      Delta {cp.magnitude}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default AskMemoryLaneView;
