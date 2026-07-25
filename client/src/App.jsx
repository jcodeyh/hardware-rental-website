import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import Login from "./pages/login.jsx";
import Signup from "./pages/Signup.jsx";
import LandingPage from "./pages/LandingPage.jsx";
import "./LandingPage.css"

export default function App() {
  return (

      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Navigate to="/login" />} />
          <Route path="/login" element={<Login />} />
          <Route path="/signUp" element={<Signup />}/>
          <Route path="/landingPage" element={<LandingPage />}/>
        </Routes>
      </BrowserRouter>
  );
}