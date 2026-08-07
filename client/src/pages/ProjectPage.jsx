import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';

// Simple popup modal for quantity input
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
    if (mode === 'checkout' && parsed > maxQty) {
      setError(`Only ${maxQty} units available.`);
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
          <button className="modal-close-btn" onClick={handleClose}>×</button>
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
              placeholder={mode === 'checkout' ? `Max: ${maxQty}` : 'Enter amount'}
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

const ProjectPage = () => {
  const { projectId } = useParams();
  const navigate = useNavigate();

  const [project, setProject] = useState(null);
  const [hwSets, setHwSets] = useState([]);
  const [projectHardware, setProjectHardware] = useState({});
  const [availability, setAvailability] = useState({});
  const [modal, setModal] = useState({ open: false, hw: null, mode: null });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        // Using the existing routes from app.py (both are GET routes)
        const projRes = await fetch(`http://localhost:5000/get_project_info?projectId=${encodeURIComponent(projectId)}`, {
          method: 'GET',
          headers: { 'Content-Type': 'application/json' },
          credentials: 'include'
        });
        const hwRes = await fetch(`http://localhost:5000/get_all_hw_names`, {
          method: 'GET',
          credentials: 'include'
        });

        if (!projRes.ok || !hwRes.ok) {
          throw new Error('Failed to fetch data from backend');
        }

        const projData = await projRes.json();
        const hwData = await hwRes.json();

        const hwArray = Array.isArray(hwData) ? hwData : (hwData.hardware || []);

        // format projData based on MongoDB projects collection schema
        const p = {
          id: projData._id || projData.id || projectId,
          name: projData.projectName || projData.name || 'Unknown Project',
          description: projData.description || '',
          hardware: projData.hwSets || projData.hardware || {}
        };
        setProject(p);
        setProjectHardware(p.hardware);

        // format hwData based on MongoDB hardware collection schema
        const formattedHw = hwArray.map(h => ({
          key: h.hwName || h.id || h._id, // use hwName as key
          label: h.hwName || h.name || 'Unknown',
          capacity: h.capacity || 0,
          availability: h.availability || 0
        }));
        setHwSets(formattedHw);

        // Initial availability from DB
        const availMap = {};
        formattedHw.forEach(h => {
          availMap[h.key] = h.availability;
        });
        setAvailability(availMap);

      } catch (err) {
        console.error(err);
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [projectId]);

  if (loading) return <div style={{ padding: '2rem' }}>Loading project and hardware details...</div>;
  if (error) return <div style={{ padding: '2rem', color: 'red' }}>Error: {error}</div>;

  if (!project) {
    return (
      <div style={{ padding: '2rem' }}>
        <p>Project not found: {projectId}</p>
        <button className="btn btn-secondary" onClick={() => navigate('/')}>Go Back</button>
      </div>
    );
  }

  const openModal = (hw, mode) => setModal({ open: true, hw, mode });
  const closeModal = () => setModal({ open: false, hw: null, mode: null });

  const handleConfirm = (qty) => {
    const { hw, mode } = modal;
    if (mode === 'checkin') {
      setProjectHardware((prev) => ({ ...prev, [hw.key]: Math.max(0, (prev[hw.key] || 0) - qty) }));
      setAvailability((prev) => ({ ...prev, [hw.key]: Math.min(hw.capacity, (prev[hw.key] || 0) + qty) }));
    } else {
      setProjectHardware((prev) => ({ ...prev, [hw.key]: (prev[hw.key] || 0) + qty }));
      setAvailability((prev) => ({ ...prev, [hw.key]: (prev[hw.key] || 0) - qty }));
    }
    closeModal();
  };

  return (
    <div className="app-container" id="project-page-container">
      {/* Navbar */}
      <nav className="navbar" id="project-navbar">
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
          <button className="btn btn-secondary" onClick={() => navigate('/')}>← Back</button>
          <span className="navbar-brand">HaaS Portal</span>
        </div>
        <span style={{ fontFamily: 'monospace', fontSize: '0.9rem', color: '#475569' }}>
          Project ID: <strong>{project.id}</strong>
        </span>
        <span className="navbar-username">Welcome, <strong>User123</strong></span>
      </nav>

      <main className="main-content" id="project-page-main">
        <h1 className="page-title">{project.name}</h1>
        <p className="page-subtitle">{project.description}</p>

        <h2 style={{ marginBottom: '16px' }}>Hardware Sets</h2>

        {/* Hardware table */}
        <table id="hardware-table" style={{ width: '100%', borderCollapse: 'collapse', background: '#fff', borderRadius: '8px', overflow: 'hidden', boxShadow: '0 1px 3px rgba(0,0,0,0.08)' }}>
          <thead>
            <tr style={{ background: '#f1f5f9', textAlign: 'left' }}>
              <th style={thStyle}>Hardware Set</th>
              <th style={thStyle}>Capacity</th>
              <th style={thStyle}>Availability</th>
              <th style={thStyle}>Check In</th>
              <th style={thStyle}>Check Out</th>
            </tr>
          </thead>
          <tbody>
            {hwSets.map((hw, i) => (
              <tr
                key={hw.key}
                id={`hw-row-${hw.key}`}
                style={{ borderTop: i > 0 ? '1px solid #e2e8f0' : 'none' }}
              >
                <td style={tdStyle}><strong>{hw.label}</strong></td>
                <td style={tdStyle}>{hw.capacity} units</td>
                <td style={tdStyle}>
                  <span style={{ color: availability[hw.key] > 0 ? '#16a34a' : '#dc2626', fontWeight: '600' }}>
                    {availability[hw.key]} / {hw.capacity}
                  </span>
                </td>
                <td style={tdStyle}>
                  <button
                    id={`btn-checkin-${hw.key}`}
                    className="btn btn-secondary"
                    disabled={!projectHardware[hw.key]}
                    onClick={() => openModal(hw, 'checkin')}
                  >
                    Check In
                  </button>
                </td>
                <td style={tdStyle}>
                  <button
                    id={`btn-checkout-${hw.key}`}
                    className="btn btn-primary"
                    disabled={!availability[hw.key]}
                    onClick={() => openModal(hw, 'checkout')}
                  >
                    Check Out
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>

        {/* Small info note */}
        <p style={{ marginTop: '12px', fontSize: '0.85rem', color: '#94a3b8' }}>
          This project currently holds: 
          {hwSets.length === 0 ? ' None' : hwSets.map((hw, idx) => (
            <span key={hw.key}>
               {' '}{hw.label} — <strong>{projectHardware[hw.key] || 0}</strong> units
              {idx < hwSets.length - 1 ? ' | ' : ''}
            </span>
          ))}
        </p>
      </main>

      <QuantityModal
        isOpen={modal.open}
        hwLabel={modal.hw?.label}
        mode={modal.mode}
        maxQty={modal.hw ? availability[modal.hw.key] : 0}
        onConfirm={handleConfirm}
        onClose={closeModal}
      />
    </div>
  );
};

// inline style helpers
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
