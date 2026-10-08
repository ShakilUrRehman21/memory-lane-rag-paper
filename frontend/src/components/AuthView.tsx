import React, { useState } from 'react';
import { api, type UserItem } from '../api';
import { MemoryLaneLogo } from './MemoryLaneLogo';
import {
  Lock, User, Eye, EyeOff,
  ArrowRight, ShieldCheck, AlertCircle
} from 'lucide-react';

interface AuthViewProps {
  onAuthSuccess: (user: UserItem) => void;
}

export const AuthView: React.FC<AuthViewProps> = ({ onAuthSuccess }) => {
  const [mode, setMode] = useState<'signin' | 'register'>('signin');
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Sign In Form
  const [signInIdentifier, setSignInIdentifier] = useState('');
  const [signInPassword, setSignInPassword] = useState('');

  // Register Form
  const [regName, setRegName] = useState('');
  const [regUsername, setRegUsername] = useState('');
  const [regEmail, setRegEmail] = useState('');
  const [regPassword, setRegPassword] = useState('');
  const [regBio, setRegBio] = useState('');
  const [regColor, setRegColor] = useState('#2563eb');

  const handleSignIn = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!signInIdentifier.trim() || !signInPassword) return;
    setLoading(true);
    setError(null);
    try {
      const res = await api.login({
        username_or_email: signInIdentifier.trim(),
        password: signInPassword,
      });
      onAuthSuccess(res.user);
    } catch (err: any) {
      setError(err.message || 'Failed to sign in. Please verify your credentials.');
    } finally {
      setLoading(false);
    }
  };

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!regUsername.trim() || !regEmail.trim() || !regPassword) return;
    setLoading(true);
    setError(null);
    try {
      const res = await api.register({
        display_name: regName.trim() || regUsername.trim(),
        username: regUsername.trim().toLowerCase().replace(/\s+/g, '_'),
        email: regEmail.trim().toLowerCase(),
        password: regPassword,
        bio: regBio.trim() || 'Personal Memory Lane Archive',
        avatar_color: regColor,
      });
      onAuthSuccess(res.user);
    } catch (err: any) {
      setError(err.message || 'Registration failed. Username or email may already be taken.');
    } finally {
      setLoading(false);
    }
  };

  const handleQuickDemoLogin = async (username: string) => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.login({
        username_or_email: username,
        password: 'password123',
      });
      onAuthSuccess(res.user);
    } catch (err: any) {
      setError(err.message || 'Failed to sign into demo account.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{
      minHeight: '100vh',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      background: 'linear-gradient(180deg, #f8fafc 0%, #f1f5f9 100%)',
      padding: '24px'
    }}>
      <div style={{ width: '100%', maxWidth: '480px' }}>
        {/* Brand Header */}
        <div style={{ textAlign: 'center', marginBottom: '28px', display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
          <MemoryLaneLogo size="lg" />
          <p style={{ fontSize: '13px', color: 'var(--text-dim)', marginTop: '8px' }}>
            Longitudinal Intelligence & Quad-Date Reasoning Architecture
          </p>
        </div>

        {/* Auth Glass Card */}
        <div className="glass-panel" style={{
          padding: '32px',
          border: '1px solid var(--border-subtle)',
          boxShadow: 'var(--shadow-xl)',
          background: '#ffffff'
        }}>
          {/* Tabs */}
          <div style={{
            display: 'grid',
            gridTemplateColumns: '1fr 1fr',
            background: '#f1f5f9',
            padding: '4px',
            borderRadius: '9px',
            marginBottom: '24px',
            border: '1px solid var(--border-subtle)'
          }}>
            <button
              type="button"
              onClick={() => { setMode('signin'); setError(null); }}
              style={{
                background: mode === 'signin' ? '#ffffff' : 'transparent',
                color: mode === 'signin' ? 'var(--accent-primary)' : 'var(--text-dim)',
                boxShadow: mode === 'signin' ? 'var(--shadow-xs)' : 'none',
                border: 'none',
                borderRadius: '7px',
                padding: '8px 0',
                fontSize: '13px',
                fontWeight: 600,
                cursor: 'pointer',
                transition: 'all 0.15s ease'
              }}
            >
              Sign In
            </button>
            <button
              type="button"
              onClick={() => { setMode('register'); setError(null); }}
              style={{
                background: mode === 'register' ? '#ffffff' : 'transparent',
                color: mode === 'register' ? 'var(--accent-primary)' : 'var(--text-dim)',
                boxShadow: mode === 'register' ? 'var(--shadow-xs)' : 'none',
                border: 'none',
                borderRadius: '7px',
                padding: '8px 0',
                fontSize: '13px',
                fontWeight: 600,
                cursor: 'pointer',
                transition: 'all 0.15s ease'
              }}
            >
              Create Account
            </button>
          </div>

          {/* Error Banner */}
          {error && (
            <div style={{
              background: '#fff1f2',
              border: '1px solid #fecdd3',
              borderRadius: '8px',
              padding: '10px 14px',
              color: '#be123c',
              fontSize: '12.5px',
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              marginBottom: '18px'
            }}>
              <AlertCircle size={16} style={{ flexShrink: 0 }} />
              <span>{error}</span>
            </div>
          )}

          {/* SIGN IN FORM */}
          {mode === 'signin' ? (
            <form onSubmit={handleSignIn} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              <div>
                <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: 'var(--text-muted)', marginBottom: '6px' }}>
                  Email or Username
                </label>
                <div style={{ position: 'relative' }}>
                  <User size={16} style={{ position: 'absolute', left: '12px', top: '11px', color: 'var(--text-dim)' }} />
                  <input
                    type="text"
                    required
                    placeholder="e.g. alex_chen or alex@memorylane.ai"
                    className="input-field"
                    style={{ paddingLeft: '38px' }}
                    value={signInIdentifier}
                    onChange={e => setSignInIdentifier(e.target.value)}
                  />
                </div>
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: 'var(--text-muted)', marginBottom: '6px' }}>
                  Password
                </label>
                <div style={{ position: 'relative' }}>
                  <Lock size={16} style={{ position: 'absolute', left: '12px', top: '11px', color: 'var(--text-dim)' }} />
                  <input
                    type={showPassword ? 'text' : 'password'}
                    required
                    placeholder="Enter your account password"
                    className="input-field"
                    style={{ paddingLeft: '38px', paddingRight: '38px' }}
                    value={signInPassword}
                    onChange={e => setSignInPassword(e.target.value)}
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    style={{
                      position: 'absolute',
                      right: '12px',
                      top: '11px',
                      background: 'none',
                      border: 'none',
                      color: 'var(--text-dim)',
                      cursor: 'pointer'
                    }}
                  >
                    {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                  </button>
                </div>
              </div>

              <button
                type="submit"
                disabled={loading}
                className="btn btn-primary"
                style={{
                  width: '100%',
                  padding: '10px',
                  marginTop: '6px',
                  fontSize: '13.5px'
                }}
              >
                {loading ? 'Authenticating...' : 'Sign In to Vault'}
              </button>
            </form>
          ) : (
            /* REGISTER FORM */
            <form onSubmit={handleRegister} style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
              <div>
                <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: 'var(--text-muted)', marginBottom: '6px' }}>
                  Full Name
                </label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Dr. Elena Rostova"
                  className="input-field"
                  value={regName}
                  onChange={e => setRegName(e.target.value)}
                />
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
                <div>
                  <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: 'var(--text-muted)', marginBottom: '6px' }}>
                    Username *
                  </label>
                  <input
                    type="text"
                    required
                    placeholder="elena_rostova"
                    className="input-field"
                    value={regUsername}
                    onChange={e => setRegUsername(e.target.value)}
                  />
                </div>
                <div>
                  <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: 'var(--text-muted)', marginBottom: '6px' }}>
                    Email *
                  </label>
                  <input
                    type="email"
                    required
                    placeholder="elena@example.com"
                    className="input-field"
                    value={regEmail}
                    onChange={e => setRegEmail(e.target.value)}
                  />
                </div>
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: 'var(--text-muted)', marginBottom: '6px' }}>
                  Create Password (min 6 characters) *
                </label>
                <div style={{ position: 'relative' }}>
                  <Lock size={16} style={{ position: 'absolute', left: '12px', top: '11px', color: 'var(--text-dim)' }} />
                  <input
                    type={showPassword ? 'text' : 'password'}
                    required
                    minLength={6}
                    placeholder="Choose a secure password"
                    className="input-field"
                    style={{ paddingLeft: '38px', paddingRight: '38px' }}
                    value={regPassword}
                    onChange={e => setRegPassword(e.target.value)}
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    style={{
                      position: 'absolute',
                      right: '12px',
                      top: '11px',
                      background: 'none',
                      border: 'none',
                      color: 'var(--text-dim)',
                      cursor: 'pointer'
                    }}
                  >
                    {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                  </button>
                </div>
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: 'var(--text-muted)', marginBottom: '6px' }}>
                  Professional Bio / Domain Focus
                </label>
                <input
                  type="text"
                  placeholder="e.g. AI Systems Lead -> Longitudinal Memory"
                  className="input-field"
                  value={regBio}
                  onChange={e => setRegBio(e.target.value)}
                />
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: 'var(--text-muted)', marginBottom: '6px' }}>
                  Vault Accent Color
                </label>
                <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                  {['#2563eb', '#059669', '#7c3aed', '#d97706', '#e11d48', '#0891b2'].map(c => (
                    <div
                      key={c}
                      onClick={() => setRegColor(c)}
                      style={{
                        width: '24px',
                        height: '24px',
                        borderRadius: '6px',
                        background: c,
                        cursor: 'pointer',
                        border: regColor === c ? '2px solid #0f172a' : '2px solid transparent',
                        transform: regColor === c ? 'scale(1.15)' : 'scale(1)',
                        transition: 'all 0.15s ease'
                      }}
                    />
                  ))}
                </div>
              </div>

              <button
                type="submit"
                disabled={loading}
                className="btn btn-primary"
                style={{
                  width: '100%',
                  padding: '10px',
                  marginTop: '6px',
                  fontSize: '13.5px'
                }}
              >
                {loading ? 'Creating Private Vault...' : 'Create Account & Private Vault'}
              </button>
            </form>
          )}

          {/* Quick Demo Accounts Helper */}
          <div style={{ marginTop: '24px', paddingTop: '20px', borderTop: '1px solid var(--border-subtle)' }}>
            <div style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              marginBottom: '10px'
            }}>
              <span style={{ fontSize: '11px', fontWeight: 700, color: 'var(--text-dim)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                1-Click Demo Profiles (Pre-seeded Archives)
              </span>
              <span className="badge badge-goal" style={{ fontSize: '9.5px', padding: '2px 6px' }}>
                Instant Access
              </span>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
              <button
                type="button"
                onClick={() => handleQuickDemoLogin('alex_chen')}
                disabled={loading}
                className="btn btn-secondary"
                style={{
                  width: '100%',
                  justifyContent: 'space-between',
                  padding: '8px 12px',
                  fontSize: '12.5px'
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#2563eb' }} />
                  <strong style={{ color: 'var(--text-main)' }}>Alex Chen</strong>
                  <span style={{ color: 'var(--text-dim)', fontSize: '11.5px' }}>2019–2026 (AI Researcher)</span>
                </div>
                <ArrowRight size={13} style={{ color: 'var(--accent-primary)' }} />
              </button>

              <button
                type="button"
                onClick={() => handleQuickDemoLogin('sophia_taylor')}
                disabled={loading}
                className="btn btn-secondary"
                style={{
                  width: '100%',
                  justifyContent: 'space-between',
                  padding: '8px 12px',
                  fontSize: '12.5px'
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#059669' }} />
                  <strong style={{ color: 'var(--text-main)' }}>Dr. Sophia Taylor</strong>
                  <span style={{ color: 'var(--text-dim)', fontSize: '11.5px' }}>2020–2026 (Genomics Lead)</span>
                </div>
                <ArrowRight size={13} style={{ color: 'var(--accent-emerald)' }} />
              </button>

              <button
                type="button"
                onClick={() => handleQuickDemoLogin('marcus_vance')}
                disabled={loading}
                className="btn btn-secondary"
                style={{
                  width: '100%',
                  justifyContent: 'space-between',
                  padding: '8px 12px',
                  fontSize: '12.5px'
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#7c3aed' }} />
                  <strong style={{ color: 'var(--text-main)' }}>Marcus Vance</strong>
                  <span style={{ color: 'var(--text-dim)', fontSize: '11.5px' }}>2018–2026 (SaaS Founder)</span>
                </div>
                <ArrowRight size={13} style={{ color: 'var(--accent-violet)' }} />
              </button>
            </div>
          </div>
        </div>

        {/* Security Footnote */}
        <div style={{
          marginTop: '16px',
          textAlign: 'center',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          gap: '6px',
          color: 'var(--text-dim)',
          fontSize: '11.5px'
        }}>
          <ShieldCheck size={14} style={{ color: 'var(--accent-emerald)' }} />
          <span>Each user's timelines, embeddings, and change-points are isolated.</span>
        </div>
      </div>
    </div>
  );
};

export default AuthView;
