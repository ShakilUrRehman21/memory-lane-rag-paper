import React from 'react';

interface LogoProps {
  size?: 'sm' | 'md' | 'lg';
  showText?: boolean;
  className?: string;
}

export const MemoryLaneLogo: React.FC<LogoProps> = ({
  size = 'md',
  showText = true,
  className = ''
}) => {
  const dimensions = {
    sm: { icon: 28, text: '13px', sub: '9px' },
    md: { icon: 36, text: '14.5px', sub: '10px' },
    lg: { icon: 46, text: '20px', sub: '12px' }
  }[size];

  return (
    <div
      className={`logo-container ${className}`}
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: '10px',
        userSelect: 'none',
        cursor: 'pointer'
      }}
    >
      {/* Bespoke Geometric Temporal Emblem */}
      <div
        style={{
          width: `${dimensions.icon}px`,
          height: `${dimensions.icon}px`,
          borderRadius: size === 'lg' ? '12px' : '9px',
          background: 'linear-gradient(135deg, #eff6ff 0%, #e0e7ff 100%)',
          border: '1px solid #bfdbfe',
          boxShadow: '0 2px 8px rgba(37, 99, 235, 0.12), inset 0 1px 0 rgba(255, 255, 255, 0.8)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          position: 'relative',
          overflow: 'hidden',
          transition: 'all 0.25s cubic-bezier(0.16, 1, 0.3, 1)',
          flexShrink: 0
        }}
      >
        <svg
          viewBox="0 0 32 32"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
          style={{ width: '80%', height: '80%' }}
        >
          <defs>
            <linearGradient id="laneGradient" x1="4" y1="28" x2="28" y2="4" gradientUnits="userSpaceOnUse">
              <stop offset="0%" stopColor="#0284c7" />
              <stop offset="50%" stopColor="#2563eb" />
              <stop offset="100%" stopColor="#6366f1" />
            </linearGradient>
            <linearGradient id="dotGradient" x1="0" y1="0" x2="1" y2="1">
              <stop offset="0%" stopColor="#38bdf8" />
              <stop offset="100%" stopColor="#2563eb" />
            </linearGradient>
          </defs>

          {/* Temporal Lane Wave 1 (Upper Horizon) */}
          <path
            d="M5 21C10 21 11 11 17 11C23 11 24 16 27 16"
            stroke="url(#laneGradient)"
            strokeWidth="2.4"
            strokeLinecap="round"
            strokeLinejoin="round"
          />

          {/* Temporal Lane Wave 2 (Lower Progression) */}
          <path
            d="M5 16C8 16 9 21 15 21C21 21 22 7 27 7"
            stroke="#93c5fd"
            strokeWidth="1.6"
            strokeLinecap="round"
            strokeDasharray="2.5 2"
          />

          {/* Milestone Node 1: Origin */}
          <circle cx="7" cy="18.5" r="2.2" fill="#0284c7" />
          <circle cx="7" cy="18.5" r="1.1" fill="#ffffff" />

          {/* Milestone Node 2: Inflection Point */}
          <circle cx="16" cy="16" r="2.8" fill="#2563eb" />
          <circle cx="16" cy="16" r="1.3" fill="#ffffff" />

          {/* Milestone Node 3: Synthesis Horizon */}
          <circle cx="26" cy="11.5" r="2.2" fill="#6366f1" />
          <circle cx="26" cy="11.5" r="1.1" fill="#ffffff" />
        </svg>
      </div>

      {showText && (
        <div style={{ display: 'flex', flexDirection: 'column', lineHeight: 1.15 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <span
              style={{
                fontSize: dimensions.text,
                fontWeight: 800,
                letterSpacing: '-0.025em',
                color: 'var(--text-main)',
                fontFamily: 'var(--font-family)'
              }}
            >
              MEMORY LANE
            </span>
            <span
              style={{
                fontSize: '9px',
                fontWeight: 700,
                color: 'var(--accent-primary)',
                background: '#eff6ff',
                border: '1px solid #bfdbfe',
                padding: '1px 5px',
                borderRadius: '4px',
                letterSpacing: '0.04em',
                textTransform: 'uppercase'
              }}
            >
              RAG
            </span>
          </div>
          <span
            style={{
              fontSize: dimensions.sub,
              color: 'var(--text-dim)',
              fontWeight: 600,
              letterSpacing: '0.03em',
              textTransform: 'uppercase'
            }}
          >
            Longitudinal Intelligence
          </span>
        </div>
      )}
    </div>
  );
};
