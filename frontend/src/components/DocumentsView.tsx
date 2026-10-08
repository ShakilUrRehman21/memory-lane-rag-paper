import React, { useState, useEffect, useMemo } from 'react';
import { api, type DocumentItem } from '../api';
import { FileText, Upload, Plus, Trash2, Search, X, ShieldCheck } from 'lucide-react';

interface DocumentsViewProps {
  userId?: string;
}

export const DocumentsView: React.FC<DocumentsViewProps> = ({ userId = 'default_user' }) => {
  const [docs, setDocs] = useState<DocumentItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [showNoteModal, setShowNoteModal] = useState(false);
  const [selectedDoc, setSelectedDoc] = useState<DocumentItem | null>(null);
  const [noteTitle, setNoteTitle] = useState('');
  const [noteDate, setNoteDate] = useState('2024-05-01');
  const [noteContent, setNoteContent] = useState('');
  const [uploading, setUploading] = useState(false);

  const loadDocuments = async () => {
    setLoading(true);
    try {
      const data = await api.getDocuments(userId);
      setDocs(data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadDocuments();
  }, [userId]);

  const filteredDocs = useMemo(() => {
    if (!searchQuery.trim()) return docs;
    const q = searchQuery.toLowerCase();
    return docs.filter(d =>
      d.title.toLowerCase().includes(q) ||
      (d.document_date && d.document_date.includes(q)) ||
      d.file_type.toLowerCase().includes(q)
    );
  }, [docs, searchQuery]);

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    try {
      await api.uploadDocument(file, undefined, undefined, userId);
      await loadDocuments();
    } catch (err) {
      alert('Upload failed: ' + err);
    } finally {
      setUploading(false);
    }
  };

  const handleAddNote = async () => {
    if (!noteTitle.trim() || !noteContent.trim()) return;
    setUploading(true);
    try {
      await api.addTextDocument(noteTitle, noteContent, noteDate, userId);
      setShowNoteModal(false);
      setNoteTitle('');
      setNoteContent('');
      await loadDocuments();
    } catch (err) {
      alert('Failed to save note: ' + err);
    } finally {
      setUploading(false);
    }
  };

  const handleDelete = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!confirm('Are you sure you want to delete this document and all its indexed temporal memories?')) return;
    try {
      await api.deleteDocument(id);
      if (selectedDoc?.id === id) setSelectedDoc(null);
      await loadDocuments();
    } catch (err) {
      alert('Delete failed: ' + err);
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      {/* Header & Actions */}
      <div className="glass-panel" style={{ padding: '24px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '16px' }}>
          <div>
            <h2 style={{ fontSize: '18px', fontWeight: 700, display: 'flex', alignItems: 'center', gap: '10px', color: 'var(--text-main)' }}>
              <FileText size={20} style={{ color: 'var(--accent-primary)' }} />
              <span>Document Studio</span>
            </h2>
          </div>

          <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
            <label className="btn btn-primary" style={{ cursor: 'pointer' }}>
              <Upload size={15} />
              <span>{uploading ? 'Processing...' : 'Upload File'}</span>
              <input
                type="file"
                accept=".txt,.md,.pdf,.docx"
                onChange={handleFileUpload}
                style={{ display: 'none' }}
                disabled={uploading}
              />
            </label>
            <button className="btn btn-secondary" onClick={() => setShowNoteModal(true)}>
              <Plus size={15} />
              <span>Add Text Entry</span>
            </button>
          </div>
        </div>

        {/* Search Bar */}
        <div style={{ position: 'relative', marginTop: '16px', maxWidth: '360px' }}>
          <Search size={14} style={{ position: 'absolute', left: '11px', top: '10px', color: 'var(--text-dim)' }} />
          <input
            type="text"
            className="input-field"
            placeholder="Search indexed documents by title or date..."
            value={searchQuery}
            onChange={e => setSearchQuery(e.target.value)}
            style={{ paddingLeft: '32px', height: '34px', fontSize: '12.5px' }}
          />
        </div>
      </div>

      {/* Note Creation Modal */}
      {showNoteModal && (
        <div className="glass-panel" style={{ padding: '24px', border: '1px solid var(--accent-primary)', boxShadow: 'var(--shadow-lg)' }}>
          <h3 style={{ fontSize: '15px', fontWeight: 700, marginBottom: '14px', color: 'var(--text-main)' }}>
            Create Historical Note Entry
          </h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: '12px' }}>
              <div>
                <label style={{ fontSize: '11px', color: 'var(--text-dim)', fontWeight: 700, letterSpacing: '0.04em' }}>ENTRY TITLE</label>
                <input
                  type="text"
                  className="input-field"
                  placeholder="e.g. 2024 Project Journal"
                  value={noteTitle}
                  onChange={e => setNoteTitle(e.target.value)}
                  style={{ marginTop: '4px' }}
                />
              </div>
              <div>
                <label style={{ fontSize: '11px', color: 'var(--text-dim)', fontWeight: 700, letterSpacing: '0.04em' }}>DOCUMENT DATE (YYYY-MM-DD)</label>
                <input
                  type="text"
                  className="input-field"
                  value={noteDate}
                  onChange={e => setNoteDate(e.target.value)}
                  style={{ marginTop: '4px' }}
                />
              </div>
            </div>
            <div>
              <label style={{ fontSize: '11px', color: 'var(--text-dim)', fontWeight: 700, letterSpacing: '0.04em' }}>CONTENT</label>
              <textarea
                className="input-field"
                rows={5}
                placeholder="Write or paste your historical reflections, goals, or notes here..."
                value={noteContent}
                onChange={e => setNoteContent(e.target.value)}
                style={{ marginTop: '4px', resize: 'vertical' }}
              />
            </div>
            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', marginTop: '6px' }}>
              <button className="btn btn-secondary" onClick={() => setShowNoteModal(false)}>
                Cancel
              </button>
              <button className="btn btn-primary" onClick={handleAddNote} disabled={uploading}>
                Save & Index Entry
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Documents Grid / Table */}
      <div className="glass-panel" style={{ padding: '24px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
          <h3 style={{ fontSize: '14.5px', fontWeight: 700, color: 'var(--text-main)' }}>
            Indexed Documents ({filteredDocs.length})
          </h3>
          <span style={{ fontSize: '11.5px', color: 'var(--text-dim)' }}>
            Click any document to inspect extraction metadata
          </span>
        </div>

        {loading ? (
          <div style={{ padding: '30px', textAlign: 'center', color: 'var(--text-dim)' }}>
            Loading document library...
          </div>
        ) : filteredDocs.length === 0 ? (
          <div style={{ padding: '40px', textAlign: 'center', color: 'var(--text-muted)' }}>
            No documents found.
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
            {filteredDocs.map(doc => (
              <div
                key={doc.id}
                className="glass-panel card-interactive"
                onClick={() => setSelectedDoc(doc)}
                style={{
                  padding: '16px 18px',
                  borderRadius: '8px',
                  background: '#ffffff',
                  border: '1px solid var(--border-subtle)',
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  flexWrap: 'wrap',
                  gap: '12px',
                  cursor: 'pointer'
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
                  <div style={{ background: '#eff6ff', padding: '10px', borderRadius: '8px', color: 'var(--accent-primary)' }}>
                    <FileText size={20} />
                  </div>
                  <div>
                    <h4 style={{ fontSize: '14px', fontWeight: 600, color: 'var(--text-main)' }}>
                      {doc.title}
                    </h4>
                    <div style={{ display: 'flex', gap: '12px', fontSize: '11.5px', color: 'var(--text-dim)', marginTop: '2px', flexWrap: 'wrap' }}>
                      <span>Date: <strong style={{ color: 'var(--accent-primary)', fontFamily: 'var(--font-mono)' }}>{doc.document_date || 'Inferred in text'}</strong></span>
                      <span>Format: {doc.file_type.toUpperCase()}</span>
                      <span>{(doc.file_size / 1024).toFixed(1)} KB</span>
                    </div>
                  </div>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
                  <div style={{ display: 'flex', gap: '6px' }}>
                    <span className="badge badge-event">{doc.chunk_count} Chunks</span>
                    <span className="badge badge-belief">{doc.tmu_count} TMUs</span>
                  </div>
                  <button
                    onClick={(e) => handleDelete(doc.id, e)}
                    style={{
                      background: 'transparent',
                      border: 'none',
                      color: 'var(--text-dim)',
                      cursor: 'pointer',
                      padding: '6px',
                      borderRadius: '6px'
                    }}
                    title="Delete document"
                  >
                    <Trash2 size={16} style={{ color: 'var(--accent-rose)' }} />
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Document Inspector Modal */}
      {selectedDoc && (
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
            maxWidth: '540px',
            padding: '24px',
            border: '1px solid var(--border-subtle)',
            boxShadow: 'var(--shadow-xl)',
            background: '#ffffff'
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <FileText size={18} style={{ color: 'var(--accent-primary)' }} />
                <span style={{ fontSize: '15px', fontWeight: 700, color: 'var(--text-main)' }}>
                  {selectedDoc.title}
                </span>
              </div>
              <button
                onClick={() => setSelectedDoc(null)}
                style={{ background: 'transparent', border: 'none', cursor: 'pointer', color: 'var(--text-dim)' }}
              >
                <X size={18} />
              </button>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px', fontSize: '12px', marginBottom: '16px' }}>
              <div style={{ padding: '10px', background: '#f8fafc', border: '1px solid var(--border-subtle)', borderRadius: '6px' }}>
                <div style={{ color: 'var(--text-dim)', fontWeight: 700, fontSize: '10.5px', textTransform: 'uppercase', marginBottom: '2px' }}>Document Date</div>
                <div style={{ fontWeight: 600, color: 'var(--accent-primary)', fontFamily: 'var(--font-mono)' }}>{selectedDoc.document_date || 'Inferred'}</div>
              </div>
              <div style={{ padding: '10px', background: '#f8fafc', border: '1px solid var(--border-subtle)', borderRadius: '6px' }}>
                <div style={{ color: 'var(--text-dim)', fontWeight: 700, fontSize: '10.5px', textTransform: 'uppercase', marginBottom: '2px' }}>Indexed Chunks</div>
                <div style={{ fontWeight: 600, color: 'var(--text-main)' }}>{selectedDoc.chunk_count} Chunks</div>
              </div>
              <div style={{ padding: '10px', background: '#f8fafc', border: '1px solid var(--border-subtle)', borderRadius: '6px' }}>
                <div style={{ color: 'var(--text-dim)', fontWeight: 700, fontSize: '10.5px', textTransform: 'uppercase', marginBottom: '2px' }}>Extracted TMUs</div>
                <div style={{ fontWeight: 600, color: 'var(--accent-emerald)' }}>{selectedDoc.tmu_count} Quad-Date Memories</div>
              </div>
              <div style={{ padding: '10px', background: '#f8fafc', border: '1px solid var(--border-subtle)', borderRadius: '6px' }}>
                <div style={{ color: 'var(--text-dim)', fontWeight: 700, fontSize: '10.5px', textTransform: 'uppercase', marginBottom: '2px' }}>Ingestion Status</div>
                <div style={{ fontWeight: 600, color: 'var(--accent-emerald)', display: 'flex', alignItems: 'center', gap: '4px' }}>
                  <ShieldCheck size={12} />
                  <span>Fully Indexed & Grounded</span>
                </div>
              </div>
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
              <button
                className="btn btn-secondary"
                onClick={() => setSelectedDoc(null)}
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default DocumentsView;
