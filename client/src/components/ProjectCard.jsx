import React from 'react';
import { useNavigate } from 'react-router-dom';
import { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import authService from '../service/authService';
import { toast } from 'react-toastify';

const ProjectCard = ({ project, onLeave}) => {
  const { id, name, description, hardware = {} } = project;
  const navigate = useNavigate();
const { user } = useAuth();
const [leaving, setLeaving] = useState(false);

const handleLeave = async (e) => {
  e.stopPropagation(); // Prevent opening the project
  if (leaving) return;

  if (!user?.userId || !user?.orgId) {
    toast.error('Please log in again.');
    return;
  }

  if (!window.confirm(`Leave project "${name}"?`)) return;

  const requestObject = {
    orgId: user.orgId,
    projectId: id,
    userId: user.userId
  };

  setLeaving(true);
  try {
    const result = await authService.leaveProject(requestObject);

    if (result?.error) {
      toast.error(result.error);
      return;
    }
    toast.success('You left the project.');
    await onLeave?.();
  } catch (err) {
    toast.error('Could not leave project: ' + err.message);
  } finally {
    setLeaving(false);
  }
};
  // Extract hardware keys (e.g., "HW set 1", "HW set 2" or "hw1", "hw2")
  const hwEntries = Object.entries(hardware);

  return (
    <div
      className="project-card"
      id={`project-card-${id}`}
      onClick={() => navigate(`/project/${id}`)}
      style={{ cursor: 'pointer' }}
    >
      <div className="project-card-header">
        <h3 className="project-card-title">{name}</h3>
        <span className="project-card-id">ID: {id}</span>
      </div>
      <p className="project-card-desc">{description}</p>

      <div className="project-card-footer">
        <div className="project-hw-info">
          {hwEntries.length === 0 ? (
            <div style={{ color: '#94a3b8', fontSize: '0.8rem' }}>No hardware checked out</div>
          ) : (
            hwEntries.map(([hwName, qty]) => (
              <div key={hwName}>
                <span className="hw-bold">{hwName}:</span> {qty} units
              </div>
            ))
          )}
        </div>
        <button
          className="btn btn-primary"
          id={`btn-open-project-${id}`}
          onClick={(e) => {
            e.stopPropagation();
            navigate(`/project/${id}`);
          }}
        >
          Open →
        </button>

        <button
          type="button"
          className='secondary'
          id={`btn-leave-project-${id}`}
          onClick={handleLeave}
          disabled={leaving}
        >
          {leaving ? 'Leaving...' : 'Leave'}
        </button>
      </div>
    </div>
  );
};

export default ProjectCard;
