import React from "react";
import ReactDOM from "react-dom/client";
import "bootstrap/dist/css/bootstrap.min.css";
import App from "./App.jsx";
import "./index.css";

import { ToastContainer } from "react-toastify";
import "react-toastify/dist/ReactToastify.css";

ReactDOM.createRoot(document.getElementById("root")).render(
     <>
    <App />
    <ToastContainer
      position="top-right"
      autoClose={5000}
      closeButton:true
      style={{ zIndex: 9999 }}
    />
  </>
);