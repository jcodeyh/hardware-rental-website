import React, { useState } from 'react';

const AddProjectModal = ({ isOpen, onClose, allSystemProjects = [], onCreateProject }) => {
  const [projectId, setProjectId] = useState('');
  const [projectName, setProjectName] = useState('');
  const [projectDescription, setProjectDescription] = useState('');
  const [error, setError] = useState('');

  if (!isOpen) return null;

  const handleSubmit = (e) => {
    e.preventDefault();
    const cleanId = projectId.trim();
    const cleanName = projectName.trim();
    const cleanDesc = projectDescription.trim();

    if (!cleanId || !cleanName || !cleanDesc) {
      setError('All fields (Project ID, Name, and Description) are required.');
      return;
    }

    // Check if Project ID already exists in the system registry
    const idExists = allSystemProjects.some(
      (p) => p.id.toLowerCase() === cleanId.toLowerCase()
    );

    if (idExists) {
      setError(`Project ID "${cleanId}" already exists. Please choose a different Project ID.`);
      return;
    }

    setError('');
    const newProject = {
      id: cleanId,
      name: cleanName,
      description: cleanDesc,
      hardware: { hw1: 0, hw2: 0 }
    };

    onCreateProject(newProject);
    handleClose();
  };

  const handleClose = () => {
    setProjectId('');
    setProjectName('');
    setProjectDescription('');
    setError('');
    onClose();
  };

  return (
    <div className="modal-overlay" onClick={handleClose} id="add-project-modal-overlay">
      <div className="modal-container" onClick={(e) => e.stopPropagation()} id="add-project-modal">
        <div className="modal-header">
          <h3 className="modal-title" id="modal-title-add">Create New Project</h3>
          <button className="modal-close-btn" onClick={handleClose} id="modal-close-x" aria-label="Close modal">
            &times;
          </button>
        </div>
        <form onSubmit={handleSubmit} className="modal-form" id="add-project-form">
          {error && <div className="modal-error" id="modal-error-message-add">{error}</div>}
          
          <div className="form-group">
            <label htmlFor="add-project-id">Project ID</label>
            <input
              type="text"
              id="add-project-id"
              value={projectId}
              onChange={(e) => setProjectId(e.target.value)}
              placeholder="e.g. proj-009"
              required
              autoFocus
            />
          </div>

          <div className="form-group">
            <label htmlFor="add-project-name">Project Name</label>
            <input
              type="text"
              id="add-project-name"
              value={projectName}
              onChange={(e) => setProjectName(e.target.value)}
              placeholder="e.g. AI Vision Engine"
              required
            />
          </div>

          <div className="form-group">
            <label htmlFor="add-project-description">Project Description</label>
            <textarea
              id="add-project-description"
              rows={3}
              value={projectDescription}
              onChange={(e) => setProjectDescription(e.target.value)}
              placeholder="Brief description of the project and its goals..."
              required
            />
          </div>

          <div className="modal-actions">
            <button type="button" className="btn btn-secondary" onClick={handleClose} id="modal-add-btn-cancel">
              Cancel
            </button>
            <button type="submit" className="btn btn-primary" id="modal-add-btn-submit">
              Create Project
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default AddProjectModal;
