import React from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import authService from '../service/authService';
import NotificationBell from './NotificationBell';

const Navbar = ({ onJoinClick, onAddClick }) => {
  const navigate = useNavigate();
  const { user, logout } = useAuth();
  const username = user?.username || 'User';

  const handleLogout = async () => {
    try {
      await authService.logout();
    } catch (err) {
      console.error('Logout error:', err);
    } finally {
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
          <button className="btn btn-outline" id="navbar-btn-dashboard" onClick={() => navigate('/dashboard')}>
            Dashboard
          </button>
          <button className="btn btn-outline" id="navbar-btn-join" onClick={onJoinClick}>
            Join Project
          </button>
          <button className="btn btn-primary" id="navbar-btn-add" onClick={onAddClick}>
            Add New Project
          </button>
          <button className="btn btn-danger" id="navbar-btn-logout" onClick={handleLogout}>
            Logout
          </button>
           <div className="notification-bell">
          <NotificationBell userId={user?.userId} />
        </div>
        </div>
      </div>
    </nav>
  );
};

export default Navbar;
