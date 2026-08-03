import React from 'react';
import ProjectCard from './ProjectCard';

const ProjectList = ({ projects }) => {
  return (
    <div className="project-list-container">
      <div className="project-grid" id="project-list-grid">
        {projects.map((project) => (
          <ProjectCard key={project.id} project={project} />
        ))}
      </div>
    </div>
  );
};

export default ProjectList;
