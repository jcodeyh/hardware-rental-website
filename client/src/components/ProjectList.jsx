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

export const SYSTEM_PROJECTS = [
  ...MOCK_PROJECTS,
  {
    id: 'proj-005',
    name: 'Genomics Data Pipeline',
    description: 'High-throughput sequencing analysis and pipeline execution for multi-omic dataset visualization.',
    hardware: { hw1: 10, hw2: 30 }
  },
  {
    id: 'proj-006',
    name: 'Climate Modeling System',
    description: 'Simulating global weather patterns and atmospheric changes using planetary-scale grid configurations.',
    hardware: { hw1: 20, hw2: 50 }
  },
  {
    id: 'proj-007',
    name: 'Financial Risk Analyzer',
    description: 'Real-time market simulation and credit risk forecasting using advanced statistical models.',
    hardware: { hw1: 8, hw2: 12 }
  },
  {
    id: 'proj-008',
    name: 'Cyber Security Threat Detector',
    description: 'Processing real-time network flow telemetry to detect anomalies and model security threats.',
    hardware: { hw1: 12, hw2: 45 }
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
