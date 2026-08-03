import React, { useState, useEffect } from 'react';
import Navbar from '../components/Navbar';
import ProjectList from '../components/ProjectList';
import JoinProjectModal from '../components/JoinProjectModal';
import AddProjectModal from '../components/AddProjectModal';

const LandingPage = () => {
  const [systemProjects, setSystemProjects] = useState([]);
  const [projects, setProjects] = useState([]);
  const [isJoinModalOpen, setIsJoinModalOpen] = useState(false);
  const [isAddModalOpen, setIsAddModalOpen] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchProjects = async () => {
      try {
        setLoading(true);
        const response = await fetch('http://localhost:5000/api/inventory');
        if (!response.ok) {
          throw new Error('Failed to fetch projects');
        }
        const data = await response.json();
        const projectsArray = Array.isArray(data) ? data : (data.projects || []);

        // Map MongoDB schema to frontend schema expected by ProjectCard
        const formattedProjects = projectsArray.map(p => ({
          id: p._id || p.id,
          name: p.projectName || p.name,
          description: p.description,
          hardware: p.hwSets || p.hardware || {}
        }));

        setSystemProjects(formattedProjects);
        setProjects(formattedProjects);
      } catch (err) {
        console.error(err);
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    fetchProjects();
  }, []);

  const handleJoinProject = (newProject) => {
    // Check if project already exists to avoid duplicates
    if (projects.some((p) => p.id.toLowerCase() === newProject.id.toLowerCase())) {
      alert(`A project with ID "${newProject.id}" is already in your dashboard.`);
      return;
    }
    setProjects([...projects, newProject]);
    setIsJoinModalOpen(false);
  };

  const handleCreateProject = async (newProject) => {
    try {
      const response = await fetch('http://localhost:5000/create_project', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          projectId: newProject.id,
          projectName: newProject.name,
          description: newProject.description,
          hwSets: newProject.hardware
        })
      });

      if (!response.ok) {
        throw new Error('Backend returned an error');
      }

      setSystemProjects([...systemProjects, newProject]);
      setProjects([...projects, newProject]);
      setIsAddModalOpen(false);
    } catch (err) {
      console.error(err);
      alert('Warning: Could not save to backend. ' + err.message);
    }
  };

  return (
    <div className="app-container" id="landing-page-container">
      <Navbar
        onJoinClick={() => setIsJoinModalOpen(true)}
        onAddClick={() => setIsAddModalOpen(true)}
      />

      <main className="main-content" id="landing-page-main">
        <h1 className="page-title" id="landing-page-title">Hardware as a Service</h1>
        <p className="page-subtitle" id="landing-page-subtitle">
          Manage your active projects and hardware resource allocations.
        </p>

        <h2 id="projects-section-heading" style={{ marginBottom: '16px', fontSize: '1.5rem', fontWeight: '600' }}>
          Your Projects
        </h2>

        {loading ? (
          <p>Loading projects...</p>
        ) : error ? (
          <p>Error: {error}</p>
        ) : (
          <ProjectList projects={projects} />
        )}
      </main>

      <JoinProjectModal
        isOpen={isJoinModalOpen}
        onClose={() => setIsJoinModalOpen(false)}
        allSystemProjects={systemProjects}
        joinedProjectIds={projects.map((p) => p.id)}
        onJoin={handleJoinProject}
      />

      <AddProjectModal
        isOpen={isAddModalOpen}
        onClose={() => setIsAddModalOpen(false)}
        allSystemProjects={systemProjects}
        onCreateProject={handleCreateProject}
      />
    </div>
  );
};

export default LandingPage;
