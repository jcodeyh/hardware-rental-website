import React, { useState } from 'react';

const JoinProjectModal = ({ isOpen, onClose, joinedProjectIds = [], onJoin }) => {
  const [projectId, setProjectId] = useState('');
  const [error, setError] = useState('');

  if (!isOpen) return null;

  const handleSubmit = (e) => {
    e.preventDefault();
    const cleanId = projectId.trim();
    
    if (!cleanId) {
      setError('Project ID is required.');
      return;
    }

    // Verify if project exists in system registry
    const matchedProject = SYSTEM_PROJECTS.find(
      (p) => p.id.toLowerCase() === cleanId.toLowerCase()
    );

    if (!matchedProject) {
      setError('Project ID does not exist.');
      return;
    }

    // Verify if user is already a member
    if (joinedProjectIds.some((id) => id.toLowerCase() === cleanId.toLowerCase())) {
      setError('You have already joined this project.');
      return;
    }
    setError('');
    onJoin({
      id: projectCode.trim(),
      name: projectName.trim(),
      description: projectDesc.trim(),
      hardware: { hw1: 0, hw2: 0 }
    });
    setProjectCode('');
    setProjectName('');
    setProjectDesc('');
  };

  return (
    <div className="modal-overlay" onClick={onClose} id="join-project-modal-overlay">
      <div className="modal-container" onClick={(e) => e.stopPropagation()} id="join-project-modal">
        <div className="modal-header">
          <h3 className="modal-title" id="modal-title-join">Join a Project</h3>
          <button className="modal-close-btn" onClick={onClose} id="modal-close-x" aria-label="Close modal">
            &times;
          </button>
        </div>
        <form onSubmit={handleSubmit} className="modal-form" id="join-project-form">
          {error && <div className="modal-error" id="modal-error-message">{error}</div>}
          
          <div className="form-group">
            <label htmlFor="project-code">Project Code</label>
            <input
              type="text"
              id="project-code"
              value={projectCode}
              onChange={(e) => setProjectCode(e.target.value)}
              placeholder="e.g. proj-005"
              required
            />
          </div>

          <div className="form-group">
            <label htmlFor="project-name">Project Name</label>
            <input type="text" id="project-name" value={projectName} onChange={(e) => setProjectName(e.target.value)}
              placeholder="e.g. Bio-Informatics Modeler"
              required
            />
          </div>

          <div className="form-group">
            <label htmlFor="project-desc">Description</label>
            <textarea id="project-desc" value={projectDesc} onChange={(e) => setProjectDesc(e.target.value)}
            placeholder="Describe the goals and scope of the project..."
            rows={4} required
            />
          </div>

          <div className="modal-actions">
            <button type="button" className="btn btn-secondary" onClick={onClose} id="modal-btn-cancel">
              Cancel
            </button>
            <button type="submit" className="btn btn-primary" id="modal-btn-submit">
              Join Project
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default JoinProjectModal;
