import React, { useState, useEffect, useMemo, useRef } from 'react';
import { api } from '../api';
import {
  Network, Info, Calendar, Search, ZoomIn, ZoomOut,
  RotateCcw, ArrowRight, FileText
} from 'lucide-react';

interface MemoryGraphViewProps {
  userId?: string;
}

export const MemoryGraphView: React.FC<MemoryGraphViewProps> = ({ userId = 'default_user' }) => {
  const [graphData, setGraphData] = useState<{ nodes: any[]; edges: any[]; summary: string } | null>(null);
  const [loading, setLoading] = useState(true);
  const [selectedNode, setSelectedNode] = useState<any | null>(null);
  const [hoveredNodeId, setHoveredNodeId] = useState<string | null>(null);

  // Filters & Search
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedTypeFilter, setSelectedTypeFilter] = useState<string>('all');
  const [selectedEdgeFilter, setSelectedEdgeFilter] = useState<string>('all');
  const [viewMode, setViewMode] = useState<'canvas' | 'table'>('canvas');

  // Canvas zoom & pan
  const [zoomLevel, setZoomLevel] = useState<number>(1);
  const [panOffset, setPanOffset] = useState<{ x: number; y: number }>({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState(false);
  const [dragStart, setDragStart] = useState<{ x: number; y: number }>({ x: 0, y: 0 });
  const svgRef = useRef<SVGSVGElement | null>(null);

  useEffect(() => {
    const fetchGraph = async () => {
      setLoading(true);
      try {
        const data = await api.getGraph(userId);
        setGraphData(data);
        if (data.nodes.length > 0) {
          setSelectedNode(data.nodes[0]);
        } else {
          setSelectedNode(null);
        }
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    };
    fetchGraph();
  }, [userId]);

  const getNodeColor = (type: string) => {
    switch (type.toLowerCase()) {
      case 'belief': return '#0284c7';
      case 'goal': return '#059669';
      case 'decision': return '#7c3aed';
      case 'preference': return '#d97706';
      default: return '#64748b';
    }
  };

  const getNodeBg = (type: string) => {
    switch (type.toLowerCase()) {
      case 'belief': return '#f0f9ff';
      case 'goal': return '#ecfdf5';
      case 'decision': return '#f5f3ff';
      case 'preference': return '#fffbeb';
      default: return '#f1f5f9';
    }
  };

  // Filtered nodes and edges
  const filteredNodes = useMemo(() => {
    if (!graphData?.nodes) return [];
    return graphData.nodes.filter(n => {
      const matchesType = selectedTypeFilter === 'all' || n.type.toLowerCase() === selectedTypeFilter.toLowerCase();
      const matchesSearch = !searchQuery.trim() ||
        n.label.toLowerCase().includes(searchQuery.toLowerCase()) ||
        n.full_text.toLowerCase().includes(searchQuery.toLowerCase()) ||
        n.date.includes(searchQuery);
      return matchesType && matchesSearch;
    });
  }, [graphData, selectedTypeFilter, searchQuery]);

  const filteredEdges = useMemo(() => {
    if (!graphData?.edges) return [];
    const validNodeIds = new Set(filteredNodes.map(n => n.id));
    return graphData.edges.filter(e => {
      const matchesEdgeType = selectedEdgeFilter === 'all' || e.type.toLowerCase() === selectedEdgeFilter.toLowerCase();
      const nodesExist = validNodeIds.has(e.source) && validNodeIds.has(e.target);
      return matchesEdgeType && nodesExist;
    });
  }, [graphData, filteredNodes, selectedEdgeFilter]);

  // Compute 2D node coordinates along chronological columns
  const nodePositions = useMemo(() => {
    const positions: Record<string, { x: number; y: number; year: string }> = {};
    if (!filteredNodes.length) return positions;

    // Group nodes by year
    const byYear: Record<string, any[]> = {};
    filteredNodes.forEach(node => {
      const year = (node.date || '2024').slice(0, 4);
      if (!byYear[year]) byYear[year] = [];
      byYear[year].push(node);
    });

    const sortedYears = Object.keys(byYear).sort();
    const colWidth = 220;
    const startX = 80;

    sortedYears.forEach((year, colIdx) => {
      const nodesInYear = byYear[year];
      const x = startX + colIdx * colWidth;
      const rowSpacing = 95;
      const startY = 80;

      nodesInYear.forEach((node, rowIdx) => {
        const y = startY + rowIdx * rowSpacing;
        positions[node.id] = { x, y, year };
      });
    });

    return positions;
  }, [filteredNodes]);

  // Pan and drag handling
  const handleMouseDown = (e: React.MouseEvent) => {
    setIsDragging(true);
    setDragStart({ x: e.clientX - panOffset.x, y: e.clientY - panOffset.y });
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    if (!isDragging) return;
    setPanOffset({
      x: e.clientX - dragStart.x,
      y: e.clientY - dragStart.y
    });
  };

  const handleMouseUp = () => setIsDragging(false);

  const resetView = () => {
    setZoomLevel(1);
    setPanOffset({ x: 0, y: 0 });
  };

  // Connected nodes lookup for highlighting on hover
  const connectedNodeIds = useMemo(() => {
    if (!hoveredNodeId) return new Set<string>();
    const nodeIds = new Set<string>([hoveredNodeId]);
    graphData?.edges.forEach(e => {
      if (e.source === hoveredNodeId) nodeIds.add(e.target);
      if (e.target === hoveredNodeId) nodeIds.add(e.source);
    });
    return nodeIds;
  }, [hoveredNodeId, graphData]);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      {/* Header and Interactive Control Bar */}
      <div className="glass-panel" style={{ padding: '20px 24px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '14px' }}>
          <div>
            <h2 style={{ fontSize: '18px', fontWeight: 700, display: 'flex', alignItems: 'center', gap: '10px', color: 'var(--text-main)' }}>
              <Network size={20} style={{ color: 'var(--accent-primary)' }} />
              <span>Memory Graph</span>
            </h2>
          </div>

          {/* View switcher */}
          <div style={{ display: 'flex', background: '#f1f5f9', padding: '3px', borderRadius: '8px', border: '1px solid var(--border-subtle)' }}>
            <button
              onClick={() => setViewMode('canvas')}
              style={{
                padding: '5px 12px',
                borderRadius: '6px',
                border: 'none',
                fontSize: '12px',
                fontWeight: 600,
                cursor: 'pointer',
                background: viewMode === 'canvas' ? '#ffffff' : 'transparent',
                color: viewMode === 'canvas' ? 'var(--accent-primary)' : 'var(--text-dim)',
                boxShadow: viewMode === 'canvas' ? 'var(--shadow-xs)' : 'none',
                transition: 'all 0.15s ease'
              }}
            >
              Interactive Canvas
            </button>
            <button
              onClick={() => setViewMode('table')}
              style={{
                padding: '5px 12px',
                borderRadius: '6px',
                border: 'none',
                fontSize: '12px',
                fontWeight: 600,
                cursor: 'pointer',
                background: viewMode === 'table' ? '#ffffff' : 'transparent',
                color: viewMode === 'table' ? 'var(--accent-primary)' : 'var(--text-dim)',
                boxShadow: viewMode === 'table' ? 'var(--shadow-xs)' : 'none',
                transition: 'all 0.15s ease'
              }}
            >
              Relational Matrix
            </button>
          </div>
        </div>

        {/* Filters and search row */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '10px', marginTop: '16px', paddingTop: '14px', borderTop: '1px solid var(--border-subtle)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flex: 1, maxWidth: '380px' }}>
            <div style={{ position: 'relative', width: '100%' }}>
              <Search size={14} style={{ position: 'absolute', left: '10px', top: '10px', color: 'var(--text-dim)' }} />
              <input
                type="text"
                placeholder="Search memory nodes or statements..."
                className="input-field"
                value={searchQuery}
                onChange={e => setSearchQuery(e.target.value)}
                style={{ paddingLeft: '32px', paddingRight: '12px', height: '34px', fontSize: '12.5px' }}
              />
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
              <span style={{ fontSize: '11px', fontWeight: 700, color: 'var(--text-dim)', letterSpacing: '0.04em' }}>NODE TYPE:</span>
              <select
                className="input-field"
                value={selectedTypeFilter}
                onChange={e => setSelectedTypeFilter(e.target.value)}
                style={{ width: '120px', height: '34px', fontSize: '12px', padding: '4px 8px' }}
              >
                <option value="all">All Types</option>
                <option value="belief">Belief</option>
                <option value="goal">Goal</option>
                <option value="decision">Decision</option>
                <option value="preference">Preference</option>
              </select>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
              <span style={{ fontSize: '11px', fontWeight: 700, color: 'var(--text-dim)', letterSpacing: '0.04em' }}>EDGE TYPE:</span>
              <select
                className="input-field"
                value={selectedEdgeFilter}
                onChange={e => setSelectedEdgeFilter(e.target.value)}
                style={{ width: '130px', height: '34px', fontSize: '12px', padding: '4px 8px' }}
              >
                <option value="all">All Relations</option>
                <option value="evolves_from">Evolves From</option>
                <option value="contradicts">Contradicts</option>
                <option value="supports">Supports</option>
                <option value="follows">Follows</option>
              </select>
            </div>

            {viewMode === 'canvas' && (
              <div style={{ display: 'flex', alignItems: 'center', gap: '4px', marginLeft: '6px' }}>
                <button
                  className="btn btn-secondary"
                  onClick={() => setZoomLevel(prev => Math.min(prev + 0.15, 2.0))}
                  title="Zoom In"
                  style={{ padding: '6px 8px', height: '34px' }}
                >
                  <ZoomIn size={14} />
                </button>
                <button
                  className="btn btn-secondary"
                  onClick={() => setZoomLevel(prev => Math.max(prev - 0.15, 0.5))}
                  title="Zoom Out"
                  style={{ padding: '6px 8px', height: '34px' }}
                >
                  <ZoomOut size={14} />
                </button>
                <button
                  className="btn btn-secondary"
                  onClick={resetView}
                  title="Reset View"
                  style={{ padding: '6px 8px', height: '34px' }}
                >
                  <RotateCcw size={14} />
                </button>
              </div>
            )}
          </div>
        </div>
      </div>

      {loading ? (
        <div style={{ padding: '60px', textAlign: 'center', color: 'var(--text-dim)', background: '#ffffff', borderRadius: '12px', border: '1px solid var(--border-subtle)' }}>
          Computing temporal graph topology...
        </div>
      ) : !graphData || filteredNodes.length === 0 ? (
        <div className="glass-panel" style={{ padding: '40px', textAlign: 'center', color: 'var(--text-muted)' }}>
          No memories found matching the current graph filter criteria.
        </div>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 2.2fr) minmax(320px, 1fr)', gap: '20px' }}>
          {/* Main Visual Canvas Panel */}
          {viewMode === 'canvas' ? (
            <div
              className="glass-panel"
              style={{
                position: 'relative',
                height: '620px',
                overflow: 'hidden',
                background: '#ffffff',
                border: '1px solid var(--border-subtle)',
                userSelect: 'none',
                cursor: isDragging ? 'grabbing' : 'grab'
              }}
              onMouseDown={handleMouseDown}
              onMouseMove={handleMouseMove}
              onMouseUp={handleMouseUp}
              onMouseLeave={handleMouseUp}
            >
              {/* Canvas Background Grid Pattern */}
              <svg
                width="100%"
                height="100%"
                style={{ position: 'absolute', inset: 0, pointerEvents: 'none' }}
              >
                <defs>
                  <pattern id="graphGrid" width="30" height="30" patternUnits="userSpaceOnUse">
                    <circle cx="2" cy="2" r="1" fill="#e2e8f0" />
                  </pattern>
                </defs>
                <rect width="100%" height="100%" fill="url(#graphGrid)" />
              </svg>

              {/* Status Pill in Corner */}
              <div
                style={{
                  position: 'absolute',
                  top: '14px',
                  left: '16px',
                  zIndex: 10,
                  background: 'rgba(255, 255, 255, 0.92)',
                  backdropFilter: 'blur(6px)',
                  border: '1px solid var(--border-subtle)',
                  borderRadius: '6px',
                  padding: '4px 10px',
                  fontSize: '11.5px',
                  color: 'var(--text-dim)',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                  boxShadow: 'var(--shadow-xs)'
                }}
              >
                <span>{filteredNodes.length} Nodes</span>
                <span>·</span>
                <span>{filteredEdges.length} Active Edges</span>
                <span>·</span>
                <span>Zoom: {(zoomLevel * 100).toFixed(0)}%</span>
              </div>

              {/* Interactive SVG World with Transform */}
              <svg
                ref={svgRef}
                width="100%"
                height="100%"
                style={{ width: '100%', height: '100%', position: 'absolute', inset: 0 }}
              >
                <defs>
                  {/* Marker Arrows */}
                  <marker id="arrow-default" viewBox="0 0 10 10" refX="22" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
                    <path d="M 0 1 L 9 5 L 0 9 z" fill="#94a3b8" />
                  </marker>
                  <marker id="arrow-evolves" viewBox="0 0 10 10" refX="22" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
                    <path d="M 0 1 L 9 5 L 0 9 z" fill="#7c3aed" />
                  </marker>
                  <marker id="arrow-contradicts" viewBox="0 0 10 10" refX="22" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
                    <path d="M 0 1 L 9 5 L 0 9 z" fill="#e11d48" />
                  </marker>
                  <marker id="arrow-supports" viewBox="0 0 10 10" refX="22" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
                    <path d="M 0 1 L 9 5 L 0 9 z" fill="#059669" />
                  </marker>
                </defs>

                <g transform={`translate(${panOffset.x}, ${panOffset.y}) scale(${zoomLevel})`}>
                  {/* EDGES */}
                  {filteredEdges.map(edge => {
                    const src = nodePositions[edge.source];
                    const dst = nodePositions[edge.target];
                    if (!src || !dst) return null;

                    const isHighlighted = hoveredNodeId && (edge.source === hoveredNodeId || edge.target === hoveredNodeId);
                    const isDimmed = hoveredNodeId && !isHighlighted;

                    // Edge styling
                    let strokeColor = '#cbd5e1';
                    let markerId = 'arrow-default';
                    let dashArray = 'none';

                    if (edge.type === 'contradicts') {
                      strokeColor = isHighlighted ? '#e11d48' : '#f87171';
                      markerId = 'arrow-contradicts';
                      dashArray = '4 3';
                    } else if (edge.type === 'evolves_from') {
                      strokeColor = isHighlighted ? '#7c3aed' : '#a78bfa';
                      markerId = 'arrow-evolves';
                    } else if (edge.type === 'supports') {
                      strokeColor = isHighlighted ? '#059669' : '#34d399';
                      markerId = 'arrow-supports';
                    }

                    // Cubic Bezier curve for smooth aesthetic paths
                    const dx = dst.x - src.x;
                    const cx1 = src.x + dx * 0.5;
                    const cy1 = src.y;
                    const cx2 = src.x + dx * 0.5;
                    const cy2 = dst.y;
                    const pathData = `M ${src.x} ${src.y} C ${cx1} ${cy1}, ${cx2} ${cy2}, ${dst.x} ${dst.y}`;

                    return (
                      <g key={edge.id} style={{ opacity: isDimmed ? 0.2 : 1, transition: 'opacity 0.2s ease' }}>
                        <path
                          d={pathData}
                          fill="none"
                          stroke={strokeColor}
                          strokeWidth={isHighlighted ? 2.6 : 1.5}
                          strokeDasharray={dashArray}
                          markerEnd={`url(#${markerId})`}
                        />
                      </g>
                    );
                  })}

                  {/* NODES */}
                  {filteredNodes.map(node => {
                    const pos = nodePositions[node.id];
                    if (!pos) return null;

                    const isSelected = selectedNode?.id === node.id;
                    const isHovered = hoveredNodeId === node.id;
                    const isConnected = connectedNodeIds.has(node.id);
                    const isDimmed = hoveredNodeId && !isHovered && !isConnected;
                    const color = getNodeColor(node.type);
                    const bg = getNodeBg(node.type);

                    return (
                      <g
                        key={node.id}
                        transform={`translate(${pos.x}, ${pos.y})`}
                        onClick={(e) => { e.stopPropagation(); setSelectedNode(node); }}
                        onMouseEnter={() => setHoveredNodeId(node.id)}
                        onMouseLeave={() => setHoveredNodeId(null)}
                        style={{
                          cursor: 'pointer',
                          opacity: isDimmed ? 0.25 : 1,
                          transition: 'opacity 0.2s ease, transform 0.2s ease'
                        }}
                      >
                        {/* Outer Glow Ring on Selected / Hover */}
                        {(isSelected || isHovered) && (
                          <circle
                            r="28"
                            fill="none"
                            stroke={color}
                            strokeWidth="2"
                            strokeDasharray={isSelected ? 'none' : '3 3'}
                            style={{ opacity: 0.6 }}
                          />
                        )}

                        {/* Node Card / Circular Badge */}
                        <circle
                          r="18"
                          fill={bg}
                          stroke={color}
                          strokeWidth={isSelected ? 3 : 2}
                          style={{
                            filter: isSelected ? 'drop-shadow(0 4px 8px rgba(37,99,235,0.25))' : 'drop-shadow(0 1px 3px rgba(0,0,0,0.06))',
                            transition: 'all 0.15s ease'
                          }}
                        />

                        {/* Center Type Dot */}
                        <circle
                          r="6"
                          fill={color}
                        />

                        {/* Node Label Box */}
                        <g transform="translate(24, -14)">
                          <rect
                            x="-4"
                            y="-4"
                            width={Math.min(node.label.length * 6.5 + 40, 160)}
                            height="28"
                            rx="5"
                            fill="#ffffff"
                            stroke={isSelected ? color : '#e2e8f0'}
                            strokeWidth="1"
                            style={{ filter: 'drop-shadow(0 1px 2px rgba(0,0,0,0.05))' }}
                          />
                          <text
                            x="4"
                            y="14"
                            fontSize="10"
                            fontWeight="700"
                            fill={color}
                            fontFamily="var(--font-family)"
                          >
                            [{node.date.slice(0, 4)}]
                          </text>
                          <text
                            x="42"
                            y="14"
                            fontSize="11"
                            fontWeight="600"
                            fill="#0f172a"
                            fontFamily="var(--font-family)"
                          >
                            {node.label.length > 18 ? node.label.slice(0, 18) + '...' : node.label}
                          </text>
                        </g>
                      </g>
                    );
                  })}
                </g>
              </svg>

              {/* Legend overlay in bottom left */}
              <div
                style={{
                  position: 'absolute',
                  bottom: '14px',
                  left: '16px',
                  zIndex: 10,
                  background: 'rgba(255, 255, 255, 0.94)',
                  backdropFilter: 'blur(8px)',
                  border: '1px solid var(--border-subtle)',
                  borderRadius: '8px',
                  padding: '8px 12px',
                  display: 'flex',
                  gap: '12px',
                  fontSize: '11px',
                  boxShadow: 'var(--shadow-sm)'
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
                  <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#0284c7' }} />
                  <span style={{ color: 'var(--text-dim)', fontWeight: 500 }}>Belief</span>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
                  <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#059669' }} />
                  <span style={{ color: 'var(--text-dim)', fontWeight: 500 }}>Goal</span>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
                  <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#7c3aed' }} />
                  <span style={{ color: 'var(--text-dim)', fontWeight: 500 }}>Decision</span>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
                  <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#d97706' }} />
                  <span style={{ color: 'var(--text-dim)', fontWeight: 500 }}>Preference</span>
                </div>
              </div>
            </div>
          ) : (
            /* Relational Matrix Table View */
            <div className="glass-panel" style={{ padding: '24px', overflowY: 'auto', maxHeight: '620px' }}>
              <h3 style={{ fontSize: '14.5px', fontWeight: 700, marginBottom: '16px', color: 'var(--text-main)' }}>
                Directed Longitudinal Relationships ({filteredEdges.length})
              </h3>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                {filteredEdges.map((edge, idx) => {
                  const srcNode = graphData?.nodes.find(n => n.id === edge.source);
                  const dstNode = graphData?.nodes.find(n => n.id === edge.target);
                  return (
                    <div
                      key={idx}
                      style={{
                        padding: '12px 14px',
                        borderRadius: '8px',
                        background: '#f8fafc',
                        border: '1px solid var(--border-subtle)',
                        display: 'flex',
                        flexDirection: 'column',
                        gap: '6px'
                      }}
                    >
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <span className={`badge ${edge.type === 'contradicts' ? 'badge-reversal' : edge.type === 'evolves_from' ? 'badge-decision' : 'badge-goal'}`}>
                          {edge.type}
                        </span>
                        <span style={{ fontSize: '11px', color: 'var(--text-dim)' }}>
                          Confidence: {(edge.confidence * 100).toFixed(0)}%
                        </span>
                      </div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '12.5px', color: 'var(--text-main)', marginTop: '2px' }}>
                        <span style={{ fontWeight: 600 }}>[{srcNode?.date.slice(0, 4)}] {srcNode?.label}</span>
                        <ArrowRight size={13} style={{ color: 'var(--accent-primary)', flexShrink: 0 }} />
                        <span style={{ fontWeight: 600 }}>[{dstNode?.date.slice(0, 4)}] {dstNode?.label}</span>
                      </div>
                      <div style={{ fontSize: '11.5px', color: 'var(--text-dim)', fontStyle: 'italic' }}>
                        {edge.rationale}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Node Inspector Drawer */}
          <div className="glass-panel" style={{ padding: '24px', display: 'flex', flexDirection: 'column' }}>
            <h3 style={{ fontSize: '14.5px', fontWeight: 700, marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--text-main)' }}>
              <Info size={16} style={{ color: 'var(--accent-primary)' }} />
              <span>Selected Node Details</span>
            </h3>

            {selectedNode ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '14px', flex: 1 }}>
                <div>
                  <span style={{ fontSize: '11px', color: 'var(--text-dim)', fontWeight: 700, letterSpacing: '0.04em' }}>MEMORY TYPE</span>
                  <div style={{ marginTop: '3px' }}>
                    <span className="badge badge-belief" style={{ textTransform: 'capitalize' }}>{selectedNode.type}</span>
                  </div>
                </div>

                <div>
                  <span style={{ fontSize: '11px', color: 'var(--text-dim)', fontWeight: 700, letterSpacing: '0.04em' }}>EVENT DATE (t_event)</span>
                  <div style={{ fontSize: '13px', color: 'var(--text-main)', marginTop: '3px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <Calendar size={13} style={{ color: 'var(--accent-primary)' }} />
                    <span style={{ fontWeight: 600 }}>{selectedNode.date}</span>
                  </div>
                </div>

                <div>
                  <span style={{ fontSize: '11px', color: 'var(--text-dim)', fontWeight: 700, letterSpacing: '0.04em' }}>SOURCE DOCUMENT</span>
                  <div style={{ fontSize: '12.5px', color: 'var(--text-muted)', marginTop: '3px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <FileText size={12} style={{ color: 'var(--text-dim)' }} />
                    <span>{selectedNode.document_title}</span>
                  </div>
                </div>

                <div>
                  <span style={{ fontSize: '11px', color: 'var(--text-dim)', fontWeight: 700, letterSpacing: '0.04em' }}>EXACT PROPOSITION</span>
                  <blockquote style={{
                    fontSize: '13px',
                    color: 'var(--text-main)',
                    lineHeight: '1.5',
                    marginTop: '5px',
                    borderLeft: '3px solid var(--accent-primary)',
                    padding: '8px 12px',
                    background: '#f8fafc',
                    borderRadius: '0 6px 6px 0'
                  }}>
                    "{selectedNode.full_text}"
                  </blockquote>
                </div>

                {selectedNode.entities && selectedNode.entities.length > 0 && (
                  <div>
                    <span style={{ fontSize: '11px', color: 'var(--text-dim)', fontWeight: 700, letterSpacing: '0.04em' }}>KEY ENTITIES</span>
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px', marginTop: '5px' }}>
                      {selectedNode.entities.map((e: string, i: number) => (
                        <span key={i} className="badge badge-event">{e}</span>
                      ))}
                    </div>
                  </div>
                )}

                {/* Stance polarity meter */}
                <div style={{ marginTop: 'auto', paddingTop: '14px', borderTop: '1px solid var(--border-subtle)' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '11.5px', marginBottom: '4px' }}>
                    <span style={{ color: 'var(--text-dim)', fontWeight: 600 }}>Polarity Index</span>
                    <span style={{ fontWeight: 700, color: selectedNode.polarity > 0 ? 'var(--accent-emerald)' : selectedNode.polarity < 0 ? 'var(--accent-rose)' : 'var(--text-dim)' }}>
                      {selectedNode.polarity > 0 ? `+${selectedNode.polarity.toFixed(2)}` : selectedNode.polarity.toFixed(2)}
                    </span>
                  </div>
                  <div style={{ width: '100%', height: '6px', background: '#e2e8f0', borderRadius: '3px', overflow: 'hidden', position: 'relative' }}>
                    <div
                      style={{
                        position: 'absolute',
                        left: '50%',
                        width: '2px',
                        height: '100%',
                        background: '#94a3b8'
                      }}
                    />
                    <div
                      style={{
                        position: 'absolute',
                        left: selectedNode.polarity < 0 ? `${50 + selectedNode.polarity * 50}%` : '50%',
                        width: `${Math.abs(selectedNode.polarity) * 50}%`,
                        height: '100%',
                        background: selectedNode.polarity >= 0 ? 'var(--accent-emerald)' : 'var(--accent-rose)',
                        borderRadius: '2px'
                      }}
                    />
                  </div>
                </div>
              </div>
            ) : (
              <div style={{ color: 'var(--text-dim)', fontSize: '13px' }}>
                Select a memory node from the canvas to view detailed attributes and relational connections.
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default MemoryGraphView;
