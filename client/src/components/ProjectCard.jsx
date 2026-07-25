import React from 'react';

const ProjectCard = ({ project }) => {
  const { id, name, description, status, hardware } = project;

  return (
    <div className="project-card" id={`project-card-${id}`}>
      <div className="project-card-header">
        <h3 className="project-card-title">{name}</h3>
        <span className="project-card-id">ID: {id}</span>
      </div>
      <p className="project-card-desc">{description}</p>
      
      <div className="project-card-footer">
        <div className="project-hw-info">
          <div><span className="hw-bold">HWSet 1:</span> {hardware.hw1 || 0} / 50 units</div>
          <div><span className="hw-bold">HWSet 2:</span> {hardware.hw2 || 0} / 100 units</div>
        </div>
      </div>
    </div>
  );
};

export default ProjectCard;
