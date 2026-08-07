import React, { useState } from 'react';
import authService from '../service/authService';

const JoinProjectModal = ({ isOpen, onClose, joinedProjectIds = [], allSystemProjects = [], onJoin }) => {
  const [projectId, setProjectId] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  if (!isOpen) return null;

  const handleSubmit = async (e) => {
    e.preventDefault();
    const cleanId = projectId.trim();
    if (!cleanId) {
      setError('Project ID is required.');
      return;
    }

    // Verify if project exists in system registry (fetched from /api/inventory)
    const matchedProject = allSystemProjects.find(
      (p) => p.id.toLowerCase() === cleanId.toLowerCase()
    );

    if (!matchedProject) {
      setError('Project ID does not exist. Check the ID and try again.');
      return;
    }

    // Verify if user is already a member locally
    if (joinedProjectIds.some((id) => id.toLowerCase() === cleanId.toLowerCase())) {
      setError('You have already joined this project.');
      return;
    }

    setError('');
    setLoading(true);

    try {
      // Call the backend to add the current user to the project's users array
      const result = await authService.joinProject({ projectId: cleanId });

      if (result.error) {
        setError(result.error);
        setLoading(false);
        return;
      }

      onJoin(matchedProject);
      setProjectId('');
    } catch (err) {
      setError('Network error: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleClose = () => {
    setProjectId('');
    setError('');
    onClose();
  };

  return (
    <div className="modal-overlay" onClick={handleClose} id="join-project-modal-overlay">
      <div className="modal-container" onClick={(e) => e.stopPropagation()} id="join-project-modal">
        <div className="modal-header">
          <h3 className="modal-title" id="modal-title-join">Join a Project</h3>
          <button className="modal-close-btn" onClick={handleClose} id="modal-close-x" aria-label="Close modal">
            &times;
          </button>
        </div>
        <form onSubmit={handleSubmit} className="modal-form" id="join-project-form">
          {error && <div className="modal-error" id="modal-error-message">{error}</div>}
          
          <div className="form-group">
            <label htmlFor="project-id">Project ID</label>
            <input
              type="text"
              id="project-id"
              value={projectId}
              onChange={(e) => setProjectId(e.target.value)}
              placeholder="e.g. PROJ-001"
              required
              autoFocus
            />
          </div>

          {/* Show available project IDs as a hint */}
          {allSystemProjects.length > 0 && (
            <div style={{ fontSize: '0.8rem', color: '#64748b', marginBottom: '12px' }}>
              Available projects: {allSystemProjects.map(p => (
                <span
                  key={p.id}
                  style={{ cursor: 'pointer', color: '#2563eb', marginRight: '8px', textDecoration: 'underline' }}
                  onClick={() => setProjectId(p.id)}
                >
                  {p.id}
                </span>
              ))}
            </div>
          )}

          <div className="modal-actions">
            <button type="button" className="btn btn-secondary" onClick={handleClose} id="modal-btn-cancel">
              Cancel
            </button>
            <button type="submit" className="btn btn-primary" id="modal-btn-submit" disabled={loading}>
              {loading ? 'Joining...' : 'Join Project'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default JoinProjectModal;
