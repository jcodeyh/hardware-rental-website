import React, { useEffect, useState } from 'react';
import authService from '../service/authService';

const AddProjectModal = ({ isOpen, onClose, allSystemProjects = [], onCreateProject }) => {
  const [projectId, setProjectId] = useState('');
  const [projectName, setProjectName] = useState('');
  const [projectDescription, setProjectDescription] = useState('');
  const [budget, setBudget] = useState('');
  const [error, setError] = useState('');
  const [hardware, setHardware] = useState([]);
  const [allocations, setAllocations] = useState({});

  useEffect(() => {
    if (!isOpen) return;
    let ignore = false;
    authService.getHardware()
      .then((data) => {
        if (!ignore && !data.error) setHardware(data.items || []);
      })
      .catch(() => {});
    return () => {
      ignore = true;
    };
  }, [isOpen]);

  if (!isOpen) return null;

  const handleSubmit = (e) => {
    e.preventDefault();
    const cleanId = projectId.trim();
    const cleanName = projectName.trim();
    const cleanDesc = projectDescription.trim();

    const parsedBudget = Number(budget);

    if (!cleanId || !cleanName || !cleanDesc || budget === '') {
      setError('All fields (Project ID, Name, Description, and Budget) are required.');
      return;
    }

    if (!Number.isInteger(parsedBudget) || parsedBudget < 0) {
      setError('Budget must be a whole number of 0 or more.');
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

    const hardwareList = [];
    for (const hw of hardware) {
      const raw = allocations[hw.id];
      if (raw === undefined || raw === '') continue;
      const allocation = Number(raw);
      if (!Number.isInteger(allocation) || allocation < 0) {
        setError(`Allocation for ${hw.name} must be a whole number of 0 or more.`);
        return;
      }
      if (allocation > 0) hardwareList.push({ hardwareId: hw.id, allocation });
    }

    setError('');
    const newProject = {
      id: cleanId,
      name: cleanName,
      description: cleanDesc,
      budget: parsedBudget,
      hardwareList
    };

    onCreateProject(newProject);
    handleClose();
  };

  const handleClose = () => {
    setProjectId('');
    setProjectName('');
    setProjectDescription('');
    setBudget('');
    setAllocations({});
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

          <div className="form-group">
            <label htmlFor="add-project-budget">Budget</label>
            <input
              type="number"
              id="add-project-budget"
              min="0"
              step="1"
              value={budget}
              onChange={(e) => setBudget(e.target.value)}
              placeholder="e.g. 20000"
              required
            />
          </div>

          {hardware.length > 0 && (
            <fieldset className="form-group" id="add-project-hardware">
              <legend style={{ fontSize: '0.9rem', fontWeight: 600 }}>Hardware allocation (optional)</legend>
              {hardware.map((hw) => (
                <div key={hw.id} className="form-group">
                  <label htmlFor={`add-project-alloc-${hw.id}`}>
                    {hw.name}{hw.available !== undefined ? ` (${hw.available} available)` : ''}
                  </label>
                  <input
                    type="number"
                    id={`add-project-alloc-${hw.id}`}
                    min="0"
                    step="1"
                    value={allocations[hw.id] ?? ''}
                    onChange={(e) => setAllocations((prev) => ({ ...prev, [hw.id]: e.target.value }))}
                    placeholder="0"
                  />
                </div>
              ))}
            </fieldset>
          )}

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
