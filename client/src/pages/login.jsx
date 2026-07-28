import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { useAuth } from '../context/AuthContext.jsx'
import { toast } from "react-toastify";
import AuthService from '../service/AuthService.js';

export default function Login() {
  const [userName, setUserName] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  // const [loading, setLoading] = useState(false)

  async function handleSubmit(e) {
    e.preventDefault();
    let requestObject = {
      "userName" : userName,
      "password" :password,
    }
    // setError("");
    try{
      let response = AuthService.login(requestObject)
      localStorage.setItem("userName", response.userName)
      toast.success("Login Functionality");
      console.log("inside login function")

    }
    catch (error) {
    console.log(error);
    toast.error("Login failed.");
  }
  }

  return (
    <div>
      <div className="container">
      <h1>Log in</h1>
      <form onSubmit={handleSubmit}>
        <div>
          <label htmlFor="userName">User Name</label>
          <input id="userName" value={userName} onChange={(e) => setUserName(e.target.value)}/>
        </div>

        <div>
          <label htmlFor="password">Password</label>
          <input id="password" type="password" value={password} onChange={(e) => setPassword(e.target.value)}/>
        </div>

        <div className="row">
          <div className="col-lg-12 full-width">
            <button type="submit">Log in</button>
          </div>
        </div>
      </form>

      <div className='signUpLink'> Don't have an account? <Link to="/signUp">Sign up</Link></div>
    </div>
    </div>
  )
}
