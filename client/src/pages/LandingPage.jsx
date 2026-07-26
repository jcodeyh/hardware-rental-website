import React, { useState } from 'react';
import Navbar from '../components/Navbar';
import ProjectList, { MOCK_PROJECTS } from '../components/ProjectList';
import JoinProjectModal from '../components/JoinProjectModal';
// import Footer from '../components/Footer';

const LandingPage = () => {
  const [projects, setProjects] = useState(MOCK_PROJECTS);
  const [isJoinModalOpen, setIsJoinModalOpen] = useState(false);

  const handleJoinProject = (newProject) => {
    // Check if project code already exists to avoid duplicates
    if (projects.some((p) => p.id.toLowerCase() === newProject.id.toLowerCase())) {
      alert(`A project with code "${newProject.id}" is already in your dashboard.`);
      return;
    }
    setProjects([...projects, newProject]);
    setIsJoinModalOpen(false);
  };

  return (
    <div className="app-container" id="landing-page-container">
      <Navbar onJoinClick={() => setIsJoinModalOpen(true)} />
      
      <main className="main-content" id="landing-page-main">
        <h1 className="page-title" id="landing-page-title">Hardware as a Service</h1>
        <p className="page-subtitle" id="landing-page-subtitle">
          Manage your active projects and hardware resource allocations.
        </p>
        
        <h2 id="projects-section-heading" style={{ marginBottom: '16px', fontSize: '1.5rem', fontWeight: '600' }}>
          Your Projects
        </h2>
        
        <ProjectList projects={projects} />
      </main>

      <JoinProjectModal
        isOpen={isJoinModalOpen}
        onClose={() => setIsJoinModalOpen(false)}
        onJoin={handleJoinProject}
      />
    </div>
  );
};

export default LandingPage;
