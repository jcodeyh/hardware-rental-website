import React from 'react';
import ProjectCard from './ProjectCard';

const ProjectList = ({ projects, onLeave }) => {
  return (
    <div className="project-list-container">
      <div className="project-grid" id="project-list-grid">
        {projects.map((project) => (
          <ProjectCard key={project.id} project={project} onLeave={onLeave} />
        ))}
      </div>
    </div>
  );
};

export default ProjectList;
