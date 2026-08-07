import React from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import authService from '../service/authService';

const Navbar = ({ onJoinClick, onAddClick }) => {
  const navigate = useNavigate();
  const { logout } = useAuth();
  const rawUser = localStorage.getItem('username');
  const username = (rawUser && rawUser !== 'undefined') ? rawUser : 'User';

  const handleLogout = async () => {
    try {
      await authService.logout();
    } catch (err) {
      console.error('Logout error:', err);
    } finally {
      localStorage.removeItem('username');
      logout();
      navigate('/login');
    }
  };

  return (
    <nav className="navbar" id="main-navbar">
      <div className="navbar-brand" id="navbar-logo">HaaS Portal</div>
      <div className="navbar-right">
        <span className="navbar-username" id="navbar-user-display">
          Welcome, <strong>{username}</strong>
        </span>
        <div className="navbar-actions">
          <button className="btn btn-secondary" id="navbar-btn-join" onClick={onJoinClick}>
            Join Project
          </button>
          <button className="btn btn-primary" id="navbar-btn-add" onClick={onAddClick}>
            Add New Project
          </button>
          <button className="btn btn-danger" id="navbar-btn-logout" onClick={handleLogout}>
            Logout
          </button>
        </div>
      </div>
    </nav>
  );
};

export default Navbar;
