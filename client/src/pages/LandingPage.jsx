import React, { useState, useEffect } from 'react';
import Navbar from '../components/Navbar';
import ProjectList from '../components/ProjectList';
import JoinProjectModal from '../components/JoinProjectModal';
import AddProjectModal from '../components/AddProjectModal';
import authService from '../service/authService';

const LandingPage = () => {
  const [systemProjects, setSystemProjects] = useState([]);
  const [projects, setProjects] = useState([]);
  const [isJoinModalOpen, setIsJoinModalOpen] = useState(false);
  const [isAddModalOpen, setIsAddModalOpen] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchProjects = async () => {
    try {
      setLoading(true);

      // Fetch all system projects for registry lookup
      const systemData = await authService.getInventory();
      const sysArray = Array.isArray(systemData) ? systemData : (systemData.projects || []);
      const formattedSystem = sysArray.map(p => ({
        id: p.projectId || p._id,
        name: p.projectName || p.name,
        description: p.description,
        hardware: p.hwSets || p.hardware || {}
      }));
      setSystemProjects(formattedSystem);

      // Fetch ONLY projects the logged-in user has joined or created
      const userData = await authService.getUserProjects();
      const userArray = Array.isArray(userData) ? userData : (userData.projects || []);
      const formattedUser = userArray.map(p => ({
        id: p.projectId || p._id,
        name: p.projectName || p.name,
        description: p.description,
        hardware: p.hwSets || p.hardware || {}
      }));
      setProjects(formattedUser);
    } catch (err) {
      console.error(err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchProjects();
  }, []);

  const handleJoinProject = async (newProject) => {
    // Re-fetch user projects from backend after joining
    await fetchProjects();
    setIsJoinModalOpen(false);
  };

  const handleCreateProject = async (newProject) => {
    try {
      const result = await authService.createProject({
        projectId: newProject.id,
        projectName: newProject.name,
        description: newProject.description,
        hwSets: newProject.hardware
      });

      if (result.error) {
        alert('Could not create project: ' + result.error);
        return;
      }

      // Re-fetch user projects from backend after creating
      await fetchProjects();
      setIsAddModalOpen(false);
    } catch (err) {
      console.error(err);
      alert('Network error: ' + err.message);
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
        ) : projects.length === 0 ? (
          <div style={{ padding: '24px', background: '#fff', borderRadius: '8px', border: '1px solid #e2e8f0', textAlign: 'center' }}>
            <p style={{ margin: 0, color: '#64748b' }}>
              You have not joined or created any projects yet. Click <strong>Join Project</strong> or <strong>Add New Project</strong> above to get started!
            </p>
          </div>
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
