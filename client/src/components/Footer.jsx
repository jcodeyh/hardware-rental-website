import React from 'react';

const Footer = () => {
  return (
    <footer className="footer" id="main-footer">
      <button className="btn btn-danger" id="footer-btn-logout">
        Logout
      </button>
      <div className="footer-text" id="footer-copyright">
        HaaS (Hardware as a Service) Portal &copy; 2026. All rights reserved.
      </div>
    </footer>
  );
};

export default Footer;
