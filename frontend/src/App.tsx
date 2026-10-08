import React, { useState, useEffect } from 'react';
import {
  Sparkles, Clock, Layers, AlertTriangle, GitCompare,
  Network, FileText, FlaskConical, Activity,
  ChevronDown, Check, X, PenTool,
  LogOut, UserCheck
} from 'lucide-react';
import {
  api,
  API_BASE,
  type UserItem,
  type LodgeThoughtRequest
} from './api';
import { MemoryLaneLogo } from './components/MemoryLaneLogo';
import { AuthView } from './components/AuthView';
import { AskMemoryLaneView } from './components/AskMemoryLaneView';
import { TimelineView } from './components/TimelineView';
import { ChangeExplorerView } from './components/ChangeExplorerView';
import { ContradictionView } from './components/ContradictionView';
import { VersionDiffView } from './components/VersionDiffView';
import { MemoryGraphView } from './components/MemoryGraphView';
import { DocumentsView } from './components/DocumentsView';
import { ResearchStudioView } from './components/ResearchStudioView';

type ViewMode =
  | 'ask'
  | 'timeline'
  | 'changes'
  | 'contradictions'
  | 'versions'
  | 'graph'
  | 'documents'
  | 'research';

export const App: React.FC = () => {
  const [currentView, setCurrentView] = useState<ViewMode>('ask');
  const [backendHealthy, setBackendHealthy] = useState<boolean | null>(null);

  // Authentication State
  const [authenticatedUser, setAuthenticatedUser] = useState<UserItem | null>(null);
  const [checkingAuth, setCheckingAuth] = useState(true);

  // Multi-user state
  const [users, setUsers] = useState<UserItem[]>([]);
  const [selectedUserId, setSelectedUserId] = useState<string>('user_alex');
  const [userDropdownOpen, setUserDropdownOpen] = useState(false);

  // Modals state
  const [showLodgeModal, setShowLodgeModal] = useState(false);
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  // Lodge Thought Form state
  const [lodgeStatement, setLodgeStatement] = useState('');
  const [lodgeType, setLodgeType] = useState<LodgeThoughtRequest['memory_type']>('belief');
  const [lodgeDate, setLodgeDate] = useState('2026-10-06');
  const [lodgeContext, setLodgeContext] = useState('');
  const [lodgeSubmitting, setLodgeSubmitting] = useState(false);

  // Refresh trigger for views
  const [viewRefreshKey, setViewRefreshKey] = useState(0);

  const fetchUsers = async () => {
    try {
      const data = await api.getUsers();
      setUsers(data);
    } catch (err) {
      console.error('Failed to load users:', err);
    }
  };

  useEffect(() => {
    const checkHealth = () => {
      fetch(`${API_BASE}/health`)
        .then(res => res.ok ? res.json() : Promise.reject())
        .then(() => setBackendHealthy(true))
        .catch(() => setBackendHealthy(false));
    };
    checkHealth();
    const healthInterval = setInterval(checkHealth, 10000);

    // Verify session
    const checkSession = async () => {
      try {
        const user = await api.getMe();
        if (user) {
          setAuthenticatedUser(user);
          setSelectedUserId(user.id);
        }
      } catch (e) {
        console.error('Session check failed:', e);
      } finally {
        setCheckingAuth(false);
      }
    };

    checkSession();
    fetchUsers();

    return () => clearInterval(healthInterval);
  }, []);

  const handleAuthSuccess = (user: UserItem) => {
    setAuthenticatedUser(user);
    setSelectedUserId(user.id);
    showToast(`Welcome to your Memory Vault, ${user.display_name}!`);
    fetchUsers();
  };

  const handleLogout = async () => {
    await api.logout();
    setAuthenticatedUser(null);
    showToast('Signed out of Memory Lane.');
  };

  const currentUser = users.find((u: UserItem) => u.id === selectedUserId) || authenticatedUser || users[0] || null;

  const showToast = (msg: string) => {
    setToastMessage(msg);
    setTimeout(() => setToastMessage(null), 4000);
  };

  const handleLodgeThought = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!lodgeStatement.trim() || !currentUser) return;
    setLodgeSubmitting(true);
    try {
      await api.lodgeThought(currentUser.id, {
        statement: lodgeStatement.trim(),
        memory_type: lodgeType,
        event_date: lodgeDate,
        context_note: lodgeContext.trim() || undefined
      });
      setShowLodgeModal(false);
      setLodgeStatement('');
      setLodgeContext('');
      showToast(`Memory capsule lodged for ${currentUser.display_name}.`);
      setViewRefreshKey((prev: number) => prev + 1);
      await fetchUsers(); // Refresh counts
    } catch (err: any) {
      alert(`Failed to lodge thought: ${err.message || err}`);
    } finally {
      setLodgeSubmitting(false);
    }
  };

  // Loading indicator while verifying token
  if (checkingAuth) {
    return (
      <div style={{
        height: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: 'var(--bg-primary)',
        color: 'var(--text-muted)',
        fontFamily: 'var(--font-family)',
        gap: '12px'
      }}>
        <Activity size={22} style={{ color: 'var(--accent-primary)' }} />
        <span style={{ fontSize: '14px', fontWeight: 500 }}>Initializing Memory Lane Vault...</span>
      </div>
    );
  }

  // If not authenticated, render dedicated Auth View (Sign In & Registration)
  if (!authenticatedUser) {
    return <AuthView onAuthSuccess={handleAuthSuccess} />;
  }

  const navItems: Array<{ id: ViewMode; label: string; icon: React.ReactNode }> = [
    { id: 'ask', label: 'Ask Memory Lane', icon: <Sparkles size={17} /> },
    { id: 'timeline', label: 'Visual Timeline', icon: <Clock size={17} /> },
    { id: 'changes', label: 'Change Explorer', icon: <Layers size={17} /> },
    { id: 'contradictions', label: 'Contradiction Explorer', icon: <AlertTriangle size={17} /> },
    { id: 'versions', label: 'Version Diff', icon: <GitCompare size={17} /> },
    { id: 'graph', label: 'Memory Graph', icon: <Network size={17} /> },
    { id: 'documents', label: 'Document Studio', icon: <FileText size={17} /> },
    { id: 'research', label: 'Research & Benchmark', icon: <FlaskConical size={17} /> },
  ];

  const renderContent = () => {
    const key = `${selectedUserId}-${viewRefreshKey}`;
    switch (currentView) {
      case 'ask': return <AskMemoryLaneView key={key} userId={selectedUserId} />;
      case 'timeline': return <TimelineView key={key} userId={selectedUserId} />;
      case 'changes': return <ChangeExplorerView key={key} userId={selectedUserId} />;
      case 'contradictions': return <ContradictionView key={key} userId={selectedUserId} />;
      case 'versions': return <VersionDiffView key={key} userId={selectedUserId} />;
      case 'graph': return <MemoryGraphView key={key} userId={selectedUserId} />;
      case 'documents': return <DocumentsView key={key} userId={selectedUserId} />;
      case 'research': return <ResearchStudioView key={key} />;
    }
  };

  return (
    <div className="app-container">
      {/* Toast Notification */}
      {toastMessage && (
        <div style={{
          position: 'fixed',
          top: '20px',
          right: '24px',
          zIndex: 9999,
          background: '#ffffff',
          border: '1px solid var(--border-subtle)',
          boxShadow: 'var(--shadow-xl)',
          borderRadius: '10px',
          padding: '12px 18px',
          color: 'var(--text-main)',
          display: 'flex',
          alignItems: 'center',
          gap: '10px',
          fontSize: '13px',
          fontWeight: 600,
          animation: 'fadeIn 0.2s cubic-bezier(0.16, 1, 0.3, 1)'
        }}>
          <div style={{ width: '20px', height: '20px', borderRadius: '50%', background: '#ecfdf5', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <Check size={12} style={{ color: 'var(--accent-emerald)' }} />
          </div>
          <span>{toastMessage}</span>
        </div>
      )}

      {/* Sidebar Navigation */}
      <aside className="sidebar">
        {/* Brand header with Bespoke Logo */}
        <div style={{ padding: '6px 8px', marginBottom: '20px' }}>
          <MemoryLaneLogo size="md" />
        </div>

        {/* Current Active User Profile Card in Sidebar */}
        {currentUser && (
          <div style={{
            background: 'var(--bg-subtle)',
            border: '1px solid var(--border-subtle)',
            borderRadius: '10px',
            padding: '11px 12px',
            marginBottom: '18px'
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '8px' }}>
              <div style={{
                width: '32px',
                height: '32px',
                borderRadius: '8px',
                background: currentUser.avatar_color || '#3b82f6',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontWeight: 700,
                color: '#ffffff',
                fontSize: '13px',
                flexShrink: 0
              }}>
                {currentUser.display_name.charAt(0)}
              </div>
              <div style={{ overflow: 'hidden' }}>
                <div style={{ fontSize: '13px', fontWeight: 700, color: 'var(--text-main)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                  {currentUser.display_name}
                </div>
                <div style={{ fontSize: '11px', color: 'var(--text-dim)' }}>
                  @{currentUser.username}
                </div>
              </div>
            </div>
            <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
              <span className="badge badge-belief" style={{ fontSize: '10px', padding: '2px 7px' }}>
                {currentUser.tmu_count} Memories
              </span>
              <span className="badge badge-goal" style={{ fontSize: '10px', padding: '2px 7px' }}>
                {currentUser.document_count} Documents
              </span>
            </div>
          </div>
        )}

        <nav style={{ display: 'flex', flexDirection: 'column', gap: '2px', flex: 1 }}>
          {navItems.map(item => (
            <div
              key={item.id}
              className={`nav-item ${currentView === item.id ? 'active' : ''}`}
              onClick={() => setCurrentView(item.id)}
            >
              {item.icon}
              <span>{item.label}</span>
            </div>
          ))}
        </nav>

        {/* Backend health status pill */}
        <div style={{
          padding: '10px 12px',
          background: 'var(--bg-subtle)',
          borderRadius: '8px',
          border: '1px solid var(--border-subtle)',
          display: 'flex',
          alignItems: 'center',
          gap: '8px'
        }}>
          <span style={{
            width: '8px',
            height: '8px',
            borderRadius: '50%',
            background: backendHealthy ? 'var(--accent-emerald)' : 'var(--accent-amber)',
            boxShadow: backendHealthy ? '0 0 6px rgba(5, 150, 105, 0.4)' : 'none',
            flexShrink: 0
          }} />
          <div style={{ fontSize: '11.5px', color: 'var(--text-dim)' }}>
            Engine: <strong style={{ color: backendHealthy ? 'var(--accent-emerald)' : 'var(--text-muted)' }}>
              {backendHealthy === null ? 'Connecting...' : backendHealthy ? 'Active (Port 8000)' : 'Offline'}
            </strong>
          </div>
        </div>
      </aside>

      {/* Main Content Area */}
      <main className="main-content">
        <header className="top-header">
          {/* Left Title */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <span style={{ fontSize: '12px', color: 'var(--text-tertiary)', textTransform: 'uppercase', letterSpacing: '0.06em', fontWeight: 600 }}>
              Section
            </span>
            <span style={{ fontSize: '12px', color: 'var(--border-medium)' }}>/</span>
            <span style={{ fontSize: '14.5px', fontWeight: 700, color: 'var(--text-main)' }}>
              {navItems.find(i => i.id === currentView)?.label}
            </span>
          </div>

          {/* Right Controls: Lodge Button, Vault Selector, Sign Out */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            {/* Action: Lodge Current Thought / Capsule */}
            <button
              onClick={() => setShowLodgeModal(true)}
              className="btn btn-primary"
              style={{ padding: '7px 14px', fontSize: '12.5px' }}
            >
              <PenTool size={13} />
              <span>Capture Memory</span>
            </button>

            {/* User Vault Switcher Dropdown */}
            <div style={{ position: 'relative' }}>
              <button
                onClick={() => setUserDropdownOpen(!userDropdownOpen)}
                className="btn btn-secondary"
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                  padding: '6px 12px',
                  fontSize: '12.5px'
                }}
              >
                {currentUser && (
                  <span style={{
                    width: '18px',
                    height: '18px',
                    borderRadius: '5px',
                    background: currentUser.avatar_color || '#3b82f6',
                    display: 'inline-flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    fontSize: '10.5px',
                    fontWeight: 700,
                    color: '#ffffff'
                  }}>
                    {currentUser.display_name.charAt(0)}
                  </span>
                )}
                <span style={{ fontWeight: 600, color: 'var(--text-main)' }}>
                  {currentUser ? currentUser.display_name : 'Select Vault'}
                </span>
                <ChevronDown size={13} style={{ color: 'var(--text-dim)' }} />
              </button>

              {/* Dropdown Menu */}
              {userDropdownOpen && (
                <div style={{
                  position: 'absolute',
                  top: '115%',
                  right: 0,
                  width: '300px',
                  background: '#ffffff',
                  border: '1px solid var(--border-subtle)',
                  borderRadius: '10px',
                  boxShadow: 'var(--shadow-xl)',
                  zIndex: 100,
                  overflow: 'hidden',
                  padding: '6px'
                }}>
                  <div style={{ padding: '8px 10px', fontSize: '11px', fontWeight: 700, color: 'var(--text-dim)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                    User Vaults ({users.length})
                  </div>

                  <div style={{ display: 'flex', flexDirection: 'column', gap: '2px', maxHeight: '240px', overflowY: 'auto' }}>
                    {users.map((u: UserItem) => {
                      const isSelected = u.id === selectedUserId;
                      return (
                        <div
                          key={u.id}
                          onClick={() => {
                            setSelectedUserId(u.id);
                            setUserDropdownOpen(false);
                            showToast(`Switched active vault to ${u.display_name}`);
                          }}
                          style={{
                            padding: '8px 10px',
                            borderRadius: '6px',
                            cursor: 'pointer',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'space-between',
                            background: isSelected ? '#eff6ff' : 'transparent',
                            border: isSelected ? '1px solid #bfdbfe' : '1px solid transparent',
                            transition: 'all 0.15s ease'
                          }}
                        >
                          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                            <div style={{
                              width: '24px',
                              height: '24px',
                              borderRadius: '6px',
                              background: u.avatar_color || '#3b82f6',
                              display: 'flex',
                              alignItems: 'center',
                              justifyContent: 'center',
                              fontWeight: 700,
                              color: '#ffffff',
                              fontSize: '11px'
                            }}>
                              {u.display_name.charAt(0)}
                            </div>
                            <div>
                              <div style={{ fontSize: '12.5px', fontWeight: 600, color: 'var(--text-main)' }}>
                                {u.display_name}
                              </div>
                              <div style={{ fontSize: '10.5px', color: 'var(--text-dim)', maxWidth: '170px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                                {u.bio}
                              </div>
                            </div>
                          </div>
                          {isSelected && <Check size={14} style={{ color: 'var(--accent-primary)' }} />}
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}
            </div>

            {/* Signed-in User Pill & Sign Out Button */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', paddingLeft: '8px', borderLeft: '1px solid var(--border-subtle)' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '5px', fontSize: '12px', color: 'var(--text-muted)' }}>
                <UserCheck size={14} style={{ color: 'var(--accent-emerald)' }} />
                <span style={{ fontWeight: 600 }}>{authenticatedUser.username}</span>
              </div>

              <button
                onClick={handleLogout}
                title="Sign Out"
                className="btn btn-secondary"
                style={{ padding: '6px 10px', fontSize: '11.5px', gap: '5px' }}
              >
                <LogOut size={13} />
                <span>Exit</span>
              </button>
            </div>
          </div>
        </header>

        <div className="content-body">
          {renderContent()}
        </div>
      </main>

      {/* MODAL: Lodge Memory Capsule */}
      {showLodgeModal && (
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
            maxWidth: '600px',
            padding: '28px',
            border: '1px solid var(--border-subtle)',
            boxShadow: 'var(--shadow-xl)',
            background: '#ffffff'
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <div style={{ background: '#eff6ff', padding: '8px', borderRadius: '8px', color: 'var(--accent-primary)' }}>
                  <PenTool size={18} />
                </div>
                <div>
                  <h3 style={{ fontSize: '17px', fontWeight: 700, color: 'var(--text-main)' }}>
                    Lodge Memory Capsule
                  </h3>
                  <p style={{ fontSize: '12px', color: 'var(--text-dim)' }}>
                    Vault: <strong style={{ color: 'var(--text-main)' }}>{currentUser?.display_name}</strong>
                  </p>
                </div>
              </div>
              <button
                onClick={() => setShowLodgeModal(false)}
                style={{ background: 'transparent', border: 'none', color: 'var(--text-dim)', cursor: 'pointer', padding: '4px' }}
              >
                <X size={18} />
              </button>
            </div>

            <form onSubmit={handleLodgeThought} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              <div>
                <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: 'var(--text-muted)', marginBottom: '6px' }}>
                  Statement / Thought / Perspective *
                </label>
                <textarea
                  required
                  rows={4}
                  className="input-field"
                  placeholder="e.g. I currently believe that large language models should be complemented by local temporal memory stores, rather than relying solely on monolithic context windows."
                  value={lodgeStatement}
                  onChange={e => setLodgeStatement(e.target.value)}
                  style={{ resize: 'vertical' }}
                />
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '14px' }}>
                <div>
                  <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: 'var(--text-muted)', marginBottom: '6px' }}>
                    Memory Type
                  </label>
                  <select
                    className="input-field"
                    value={lodgeType}
                    onChange={e => setLodgeType(e.target.value as any)}
                  >
                    <option value="belief">Belief (Stance / Philosophical viewpoint)</option>
                    <option value="goal">Goal (Long-term aspiration or target)</option>
                    <option value="preference">Preference (Tooling or architectural choice)</option>
                    <option value="decision">Decision (Definitive pivot or commitment)</option>
                    <option value="interest">Interest (Curiosity or research area)</option>
                    <option value="fact">Fact (Milestone event)</option>
                  </select>
                </div>

                <div>
                  <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: 'var(--text-muted)', marginBottom: '6px' }}>
                    Event Date (t_event)
                  </label>
                  <input
                    type="date"
                    required
                    className="input-field"
                    value={lodgeDate}
                    onChange={e => setLodgeDate(e.target.value)}
                  />
                </div>
              </div>

              {/* Quick Date Presets */}
              <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                <span style={{ fontSize: '11px', color: 'var(--text-dim)', fontWeight: 600 }}>Quick Date:</span>
                <button
                  type="button"
                  className="btn btn-secondary"
                  style={{ fontSize: '11px', padding: '3px 8px' }}
                  onClick={() => setLodgeDate('2026-10-06')}
                >
                  Today (2026)
                </button>
                <button
                  type="button"
                  className="btn btn-secondary"
                  style={{ fontSize: '11px', padding: '3px 8px' }}
                  onClick={() => setLodgeDate('2021-04-15')}
                >
                  5 Years Ago (2021)
                </button>
                <button
                  type="button"
                  className="btn btn-secondary"
                  style={{ fontSize: '11px', padding: '3px 8px' }}
                  onClick={() => setLodgeDate('2019-06-10')}
                >
                  7 Years Ago (2019)
                </button>
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: 'var(--text-muted)', marginBottom: '6px' }}>
                  Context / Reflection Note (Optional)
                </label>
                <input
                  type="text"
                  className="input-field"
                  placeholder="e.g. Recorded during production architecture redesign"
                  value={lodgeContext}
                  onChange={e => setLodgeContext(e.target.value)}
                />
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', marginTop: '8px' }}>
                <button
                  type="button"
                  className="btn btn-secondary"
                  onClick={() => setShowLodgeModal(false)}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={lodgeSubmitting}
                  className="btn btn-primary"
                >
                  {lodgeSubmitting ? 'Indexing Capsule...' : 'Lodge to Memory Vault'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default App;
