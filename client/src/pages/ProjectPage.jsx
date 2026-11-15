import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { toast } from 'react-toastify';
import authService from '../service/authService';
import { useAuth } from '../context/AuthContext.jsx';

const QuantityModal = ({ isOpen, hwLabel, mode, maxQty, onConfirm, onClose }) => {
  const [qty, setQty] = useState('');
  const [error, setError] = useState('');

  if (!isOpen) return null;

  const handleSubmit = (e) => {
    e.preventDefault();
    const parsed = parseInt(qty, 10);
    if (!qty || isNaN(parsed) || parsed <= 0) {
      setError('Please enter a valid number.');
      return;
    }
    if (parsed > maxQty) {
      setError(mode === 'checkout'
        ? `Only ${maxQty} units remaining.`
        : `Only ${maxQty} units are checked out.`);
      return;
    }
    onConfirm(parsed);
    setQty('');
    setError('');
  };

  const handleClose = () => {
    setQty('');
    setError('');
    onClose();
  };

  return (
    <div className="modal-overlay" onClick={handleClose}>
      <div className="modal-container" onClick={(e) => e.stopPropagation()} style={{ maxWidth: '380px' }}>
        <div className="modal-header">
          <h2 className="modal-title">
            {mode === 'checkin' ? 'Check In' : 'Check Out'} — {hwLabel}
          </h2>
          <button className="modal-close-btn" onClick={handleClose} aria-label="Close">×</button>
        </div>

        <form className="modal-form" onSubmit={handleSubmit}>
          {error && <div className="modal-error">{error}</div>}
          <div className="form-group">
            <label htmlFor="qty-input">Quantity</label>
            <input
              id="qty-input"
              type="number"
              min="1"
              value={qty}
              onChange={(e) => { setQty(e.target.value); setError(''); }}
              placeholder={`Max: ${maxQty}`}
              autoFocus
            />
          </div>
          <div className="modal-actions">
            <button type="button" className="btn btn-secondary" onClick={handleClose}>Cancel</button>
            <button type="submit" className="btn btn-primary" id="modal-submit-btn">Submit</button>
          </div>
        </form>
      </div>
    </div>
  );
};

const toCount = (v) => {
  const n = Number(v);
  return Number.isFinite(n) && n > 0 ? n : 0;
};

const ProjectPage = () => {
  const { projectId } = useParams();
  const navigate = useNavigate();
  const { user, logout } = useAuth();

  const [project, setProject] = useState(null);
  const [rows, setRows] = useState([]);
  const [modal, setModal] = useState({ open: false, hw: null, mode: null });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let ignore = false;
    const fetchData = async () => {
      try {
        setLoading(true);
        const projData = await authService.getProjectInfo(projectId);
        if (ignore) return;
        if (projData.error) {
          setError(projData.error);
          return;
        }
        const info = projData.projectInfo;
        if (!info) {
          setProject(null);
          return;
        }
        setProject({
          id: info.projectId,
          name: info.projectName,
          description: info.projectDesc || '',
        });
        setRows((info.hardwareList || []).map((h) => ({
          key: h.hardwareId,
          label: h.name || h.hardwareId,
          allocation: toCount(h.allocation),
          reserved: toCount(h.reserved),
          out: toCount(h.out),
          remaining: toCount(h.remaining),
        })));
      } catch (err) {
        if (!ignore) setError(err.message);
      } finally {
        if (!ignore) setLoading(false);
      }
    };

    fetchData();
    return () => {
      ignore = true;
    };
  }, [projectId]);

  if (loading) return <div style={{ padding: '2rem' }}>Loading project and hardware details...</div>;
  if (error) return <div style={{ padding: '2rem', color: 'red' }}>Error: {error}</div>;

  if (!project) {
    return (
      <div style={{ padding: '2rem' }}>
        <p>Project not found: {projectId}</p>
        <button className="btn btn-secondary" onClick={() => navigate('/landingPage')}>Go Back</button>
      </div>
    );
  }

  const openModal = (hw, mode) => setModal({ open: true, hw, mode });
  const closeModal = () => setModal({ open: false, hw: null, mode: null });

  const handleConfirm = async (qty) => {
    const { hw, mode } = modal;
    try {
      const action = {
        projectId: project.id,
        hardwareId: hw.key,
        quantity: qty,
        requestId: crypto.randomUUID()
      };
      const result = mode === 'checkin'
        ? await authService.checkIn(action)
        : await authService.checkOut(action);

      if (result.error) {
        toast.error(result.error);
        return;
      }

      const delta = mode === 'checkin' ? -qty : qty;
      setRows((prev) => prev.map((r) => (r.key === hw.key
        ? { ...r, out: Math.max(0, r.out + delta), remaining: Math.max(0, r.remaining - delta) }
        : r)));
      toast.success(`${mode === 'checkin' ? 'Checked in' : 'Checked out'} ${qty} × ${hw.label}`);
    } catch (err) {
      toast.error('Network error: ' + err.message);
    } finally {
      closeModal();
    }
  };

  const handleLogout = async () => {
    try {
      await authService.logout();
    } catch (err) {
      console.error('Logout error:', err);
    } finally {
      logout();
      navigate('/login');
    }
  };

  const modalRow = modal.hw ? rows.find((r) => r.key === modal.hw.key) : null;
  const maxQty = modalRow ? (modal.mode === 'checkin' ? modalRow.out : modalRow.remaining) : 0;

  return (
    <div className="app-container" id="project-page-container">
      <nav className="navbar" id="project-navbar">
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
          <button className="btn btn-secondary" onClick={() => navigate('/landingPage')}>← Back</button>
          <span className="navbar-brand">HaaS Portal</span>
        </div>
        <span style={{ fontFamily: 'monospace', fontSize: '0.9rem', color: '#475569' }}>
          Project ID: <strong>{project.id}</strong>
        </span>
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
          <span className="navbar-username">
            Welcome, <strong>{user?.username || 'User'}</strong>
          </span>
          <button className="btn btn-danger" onClick={handleLogout}>Logout</button>
        </div>
      </nav>

      <main className="main-content" id="project-page-main">
        <h1 className="page-title">{project.name}</h1>
        <p className="page-subtitle">{project.description}</p>

        <h2 style={{ marginBottom: '16px' }}>Hardware</h2>

        {rows.length === 0 ? (
          <p style={{ color: '#64748b' }}>No hardware is allocated to this project.</p>
        ) : (
          <table id="hardware-table" style={{ width: '100%', borderCollapse: 'collapse', background: '#fff', borderRadius: '8px', overflow: 'hidden', boxShadow: '0 1px 3px rgba(0,0,0,0.08)' }}>
            <thead>
              <tr style={{ background: '#f1f5f9', textAlign: 'left' }}>
                <th style={thStyle}>Hardware</th>
                <th style={thStyle}>Planned</th>
                <th style={thStyle}>Reserved</th>
                <th style={thStyle}>Out</th>
                <th style={thStyle}>Remaining</th>
                <th style={thStyle}>Check In</th>
                <th style={thStyle}>Check Out</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((hw, i) => (
                <tr
                  key={hw.key}
                  id={`hw-row-${hw.key}`}
                  style={{ borderTop: i > 0 ? '1px solid #e2e8f0' : 'none' }}
                >
                  <td style={tdStyle}><strong>{hw.label}</strong></td>
                  <td style={tdStyle} data-label="planned">{hw.allocation}</td>
                  <td style={tdStyle} data-label="reserved">{hw.reserved}</td>
                  <td style={tdStyle} data-label="out">{hw.out}</td>
                  <td style={tdStyle} data-label="remaining">
                    <span style={{ color: hw.remaining > 0 ? '#16a34a' : '#dc2626', fontWeight: '600' }}>
                      {hw.remaining}
                    </span>
                  </td>
                  <td style={tdStyle}>
                    <button
                      id={`btn-checkin-${hw.key}`}
                      className="btn btn-secondary"
                      disabled={hw.out <= 0}
                      onClick={() => openModal(hw, 'checkin')}
                    >
                      Check In
                    </button>
                  </td>
                  <td style={tdStyle}>
                    <button
                      id={`btn-checkout-${hw.key}`}
                      className="btn btn-primary"
                      disabled={hw.remaining <= 0}
                      onClick={() => openModal(hw, 'checkout')}
                    >
                      Check Out
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}

        <p style={{ marginTop: '12px', fontSize: '0.85rem', color: '#94a3b8' }}>
          Planned is what the project asked for, reserved is what the Hardware service is holding for it,
          out is checked out now, and remaining is what can still be checked out.
        </p>
      </main>

      <QuantityModal
        isOpen={modal.open}
        hwLabel={modal.hw?.label}
        mode={modal.mode}
        maxQty={maxQty}
        onConfirm={handleConfirm}
        onClose={closeModal}
      />
    </div>
  );
};

const thStyle = {
  padding: '12px 16px',
  fontSize: '0.85rem',
  fontWeight: '600',
  color: '#475569',
  textTransform: 'uppercase',
  letterSpacing: '0.04em',
};

const tdStyle = {
  padding: '16px',
  fontSize: '0.95rem',
  color: '#1e293b',
  verticalAlign: 'middle',
};

export default ProjectPage;
