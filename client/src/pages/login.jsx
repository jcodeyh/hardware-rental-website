import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { useAuth } from '../context/AuthContext.jsx'
import { toast } from "react-toastify";
import AuthService from '../service/authService.js';

export default function Login() {
  const [userName, setUserName] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const navigate = useNavigate();
  const { login } = useAuth();

  async function handleSubmit(e) {
    e.preventDefault();
    let requestObject = {
      "username" : userName,
      "password" :password,
    }
    try{
      let response = await AuthService.login(requestObject)
      if(response && response.data){
        console.log("Logged in successfully")
        localStorage.setItem("username", response.data)
        login(response.data) // set token in AuthContext
        navigate('/landingPage')
      }
      else {
        toast.error("Login failed: " + (response.error || "Invalid credentials"))
      }
    }
    catch (error) {
      toast.error("Login failed: network error");
    }
  }

  function clearForm (e){
    e.preventDefault();
    setUserName('')
    setPassword('')
  }

  return (
    <div className='page'>
      <div className="container">
      <h1>Log in</h1>
      <form className='mt-4'>
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
            <div className="row">
              <div className="col-lg-6">
                <button className='secondary' onClick={clearForm}>Clear</button>
              </div>

              <div className="col-lg-6">
                <button className={`${((userName == "") || (password == "") ) ? 'btn-disabled' : 'button'}`} disabled={((userName == "") || (password == "") )? true : false  } onClick={handleSubmit}>Log in</button>
              </div>
            </div>
          </div>
        </div>
      </form>

      <div className='signUpLink mt-4'> Don't have an account? <Link to="/signUp">Sign up</Link></div>
    </div>
    </div>
  )
}
