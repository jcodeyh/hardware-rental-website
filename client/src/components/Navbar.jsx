import React from 'react';

const Navbar = ({ onJoinClick, onAddClick }) => {
  return (
    <nav className="navbar" id="main-navbar">
      <div className="navbar-brand" id="navbar-logo">HaaS Portal</div>
      <div className="navbar-right">
        <span className="navbar-username" id="navbar-user-display">
          Welcome, <strong>User123</strong>
        </span>
        <div className="navbar-actions">
          <button className="btn btn-secondary" id="navbar-btn-join" onClick={onJoinClick}>
            Join Project
          </button>
          <button className="btn btn-primary" id="navbar-btn-add" onClick={onAddClick}>
            Add New Project
          </button>
        </div>
      </div>
    </nav>
  );
};

export default Navbar;
