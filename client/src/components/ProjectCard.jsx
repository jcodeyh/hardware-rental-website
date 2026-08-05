import React from 'react';
import { useNavigate } from 'react-router-dom';

const ProjectCard = ({ project }) => {
  const { id, name, description, hardware } = project;
  const navigate = useNavigate();

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
          <div>
            <span className="hw-bold">HWSet 1:</span> {hardware?.hw1 || 0} / 50 units
          </div>
          <div>
            <span className="hw-bold">HWSet 2:</span> {hardware?.hw2 || 0} / 100 units
          </div>
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
      </div>
    </div>
  );
};

export default ProjectCard;
