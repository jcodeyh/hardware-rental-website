import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import Login from "./pages/login.jsx";
import Signup from "./pages/signup.jsx";
import LandingPage from "./pages/LandingPage.jsx";
import ProjectPage from "./pages/ProjectPage.jsx";
import "./LandingPage.css"

export default function App() {
  return (
      <BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
        <Routes>
          <Route path="/" element={<Navigate to="/login" />} />
          <Route path="/login" element={<Login />} />
          <Route path="/signUp" element={<Signup />}/>
          <Route path="/landingPage" element={<LandingPage />}/>
          <Route path="/project/:projectId" element={<ProjectPage />}/>
        </Routes>
      </BrowserRouter>
  );
}