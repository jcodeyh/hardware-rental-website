import React from 'react';
import ProjectCard from './ProjectCard';

export const MOCK_PROJECTS = [
  {
    id: 'proj-001',
    name: 'Quantum Simulation Lab',
    description: 'Running high-performance physics models to study quantum entanglement patterns using specialized GPU arrays.',
    hardware: { hw1: 15, hw2: 40 }
  },
  {
    id: 'proj-002',
    name: 'Neural Network Optimizer',
    description: 'Distributed training workloads for large-scale transformer-based language model testing and tuning.',
    hardware: { hw1: 30, hw2: 80 }
  },
  {
    id: 'proj-003',
    name: 'Autonomous Navigation Map Maker',
    description: 'Processing high-fidelity LiDAR and camera feeds to construct detailed 3D spatial environments.',
    hardware: { hw1: 0, hw2: 0 }
  },
  {
    id: 'proj-004',
    name: 'Protein Folding Predictor',
    description: 'Analyzing complex genetic sequencing data and modeling three-dimensional amino acid structure predictions.',
    hardware: { hw1: 5, hw2: 25 }
  }
];

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
