import React, { useState, useEffect } from 'react';
import { api, type BenchmarkRun, type PipelineMetric } from '../api';
import { FlaskConical, Play, BarChart3 } from 'lucide-react';

export const ResearchStudioView: React.FC = () => {
  const [runs, setRuns] = useState<BenchmarkRun[]>([]);
  const [latestRun, setLatestRun] = useState<BenchmarkRun | null>(null);
  const [running, setRunning] = useState(false);

  const loadRuns = async () => {
    try {
      const data = await api.getBenchmarkRuns();
      setRuns(data);
      if (data.length > 0) {
        setLatestRun(data[0]);
      }
    } catch (err) {
      console.error(err);
    }
  };

  useEffect(() => {
    loadRuns();
  }, []);

  const handleRunBenchmark = async () => {
    setRunning(true);
    try {
      const result = await api.runBenchmark(`Interactive Run #${runs.length + 1}`);
      setLatestRun(result);
      await loadRuns();
    } catch (err) {
      alert('Benchmark failed: ' + err);
    } finally {
      setRunning(false);
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      {/* Header */}
      <div className="glass-panel" style={{ padding: '24px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '16px' }}>
          <div>
            <h2 style={{ fontSize: '18px', fontWeight: 700, display: 'flex', alignItems: 'center', gap: '10px', color: 'var(--text-main)' }}>
              <FlaskConical size={20} style={{ color: 'var(--accent-primary)' }} />
              <span>Research Benchmarks</span>
            </h2>
          </div>

          <button
            className="btn btn-primary"
            onClick={handleRunBenchmark}
            disabled={running}
            style={{ padding: '9px 18px' }}
          >
            <Play size={15} />
            <span>{running ? 'Executing Benchmark...' : 'Run Comparative Benchmark'}</span>
          </button>
        </div>
      </div>

      {/* Latest Benchmark Results */}
      {latestRun && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          {/* Executive Summary Card */}
          <div className="glass-panel" style={{ padding: '20px', borderLeft: '4px solid var(--accent-primary)' }}>
            <div style={{ fontSize: '11.5px', fontWeight: 700, color: 'var(--accent-primary)', textTransform: 'uppercase', letterSpacing: '0.04em', marginBottom: '4px' }}>
              Latest Evaluation Summary ({latestRun.run_name})
            </div>
            <p style={{ fontSize: '14px', color: 'var(--text-main)', lineHeight: '1.6' }}>
              {latestRun.summary_findings}
            </p>
          </div>

          {/* Comparative Metrics Table */}
          <div className="glass-panel" style={{ padding: '24px' }}>
            <h3 style={{ fontSize: '14.5px', fontWeight: 700, marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--text-main)' }}>
              <BarChart3 size={17} style={{ color: 'var(--accent-indigo)' }} />
              <span>Architectural Comparison Matrix</span>
            </h3>

            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '13px' }}>
                <thead>
                  <tr style={{ borderBottom: '1px solid var(--border-subtle)', background: '#f8fafc', color: 'var(--text-dim)' }}>
                    <th style={{ padding: '10px 14px', fontWeight: 700, fontSize: '11.5px', letterSpacing: '0.03em' }}>RAG PIPELINE</th>
                    <th style={{ padding: '10px 14px', fontWeight: 700, fontSize: '11.5px', letterSpacing: '0.03em' }}>CHRONOLOGICAL ACCURACY (COA)</th>
                    <th style={{ padding: '10px 14px', fontWeight: 700, fontSize: '11.5px', letterSpacing: '0.03em' }}>TEMPORAL COVERAGE RECALL (TCR)</th>
                    <th style={{ padding: '10px 14px', fontWeight: 700, fontSize: '11.5px', letterSpacing: '0.03em' }}>CHANGE-POINT F1</th>
                    <th style={{ padding: '10px 14px', fontWeight: 700, fontSize: '11.5px', letterSpacing: '0.03em' }}>UNSUPPORTED CLAIM RATE</th>
                    <th style={{ padding: '10px 14px', fontWeight: 700, fontSize: '11.5px', letterSpacing: '0.03em' }}>LATENCY (MS)</th>
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(latestRun.metrics).map(([name, m]: [string, PipelineMetric]) => {
                    const isMemoryLane = name === 'memory_lane';
                    return (
                      <tr
                        key={name}
                        style={{
                          borderBottom: '1px solid var(--border-subtle)',
                          background: isMemoryLane ? '#eff6ff' : 'transparent',
                          fontWeight: isMemoryLane ? 600 : 400
                        }}
                      >
                        <td style={{ padding: '14px', color: isMemoryLane ? 'var(--accent-primary)' : 'var(--text-main)', textTransform: 'uppercase' }}>
                          <strong>{name.replace('_', ' ')}</strong>
                        </td>
                        <td style={{ padding: '14px', color: m.chronological_ordering_accuracy >= 0.8 ? 'var(--accent-emerald)' : 'var(--text-muted)' }}>
                          {(m.chronological_ordering_accuracy * 100).toFixed(1)}%
                        </td>
                        <td style={{ padding: '14px', color: m.temporal_coverage_recall >= 0.8 ? 'var(--accent-emerald)' : 'var(--accent-rose)' }}>
                          {(m.temporal_coverage_recall * 100).toFixed(1)}%
                        </td>
                        <td style={{ padding: '14px', color: m.change_point_f1 > 0 ? 'var(--accent-violet)' : 'var(--text-dim)' }}>
                          {(m.change_point_f1 * 100).toFixed(1)}%
                        </td>
                        <td style={{ padding: '14px', color: m.unsupported_claim_rate <= 0.1 ? 'var(--accent-emerald)' : 'var(--accent-rose)' }}>
                          {(m.unsupported_claim_rate * 100).toFixed(1)}%
                        </td>
                        <td style={{ padding: '14px', color: 'var(--text-muted)' }}>
                          {m.average_latency_ms.toFixed(1)} ms
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>

          {/* Research Questions Insights */}
          <div className="glass-panel" style={{ padding: '24px' }}>
            <h3 style={{ fontSize: '14.5px', fontWeight: 700, marginBottom: '16px', color: 'var(--text-main)' }}>
              Research Questions (RQ1 – RQ5) Findings
            </h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '14px' }}>
              <div style={{ padding: '14px', background: '#f8fafc', borderRadius: '8px', border: '1px solid var(--border-subtle)' }}>
                <h5 style={{ fontSize: '13px', color: 'var(--accent-cyan)', marginBottom: '4px', fontWeight: 700 }}>
                  RQ1: Temporal-Aware Retrieval vs Semantic RAG
                </h5>
                <p style={{ fontSize: '12.5px', color: 'var(--text-muted)', lineHeight: '1.5' }}>
                  Stratified sampling prevents density clustering around recent documents, expanding historical recall across multi-year queries.
                </p>
              </div>

              <div style={{ padding: '14px', background: '#f8fafc', borderRadius: '8px', border: '1px solid var(--border-subtle)' }}>
                <h5 style={{ fontSize: '13px', color: 'var(--accent-indigo)', marginBottom: '4px', fontWeight: 700 }}>
                  RQ2: Chronological Ordering & Belief Evolution
                </h5>
                <p style={{ fontSize: '12.5px', color: 'var(--text-muted)', lineHeight: '1.5' }}>
                  Organizing context by quad-event dates ensures that synthesis respects monotonic progression without time travel.
                </p>
              </div>

              <div style={{ padding: '14px', background: '#f8fafc', borderRadius: '8px', border: '1px solid var(--border-subtle)' }}>
                <h5 style={{ fontSize: '13px', color: 'var(--accent-violet)', marginBottom: '4px', fontWeight: 700 }}>
                  RQ3: Change-Point Detection Precision
                </h5>
                <p style={{ fontSize: '12.5px', color: 'var(--text-muted)', lineHeight: '1.5' }}>
                  Pairwise semantic drift and polarity sign inversion accurately isolate documented transition intervals.
                </p>
              </div>

              <div style={{ padding: '14px', background: '#f8fafc', borderRadius: '8px', border: '1px solid var(--border-subtle)' }}>
                <h5 style={{ fontSize: '13px', color: 'var(--accent-emerald)', marginBottom: '4px', fontWeight: 700 }}>
                  RQ4: Evidence Grounding & Claim Hallucination
                </h5>
                <p style={{ fontSize: '12.5px', color: 'var(--text-muted)', lineHeight: '1.5' }}>
                  Claim-level citation verification binds every assertion to document chunks, driving unsupported claim rate toward zero.
                </p>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default ResearchStudioView;
