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
  const navigate = useNavigate(); 
  async function handleSubmit(e) {
    e.preventDefault();
    let requestObject = {
      "username" : userName,
      "password" :password,
    }
    // navigate('/landingPage')
    // setError("");
    try{
      let response = AuthService.login(requestObject)
      localStorage.setItem("username", response.userName)
      toast.success("Login Functionality");
      console.log("Logged in successfully")
      if(response.statusCode == 200){
        useNavigate('/landingPage')
      }
      else {
        toast.error("Login failed with some other status-code")
      }
    }
    catch (error) {
    console.log(error);
    toast.error("Login failed");
  }
  }

  function clearForm (){
    e.preventDefault();
    setUserName('')
    setPassword('')
  }

  return (
    <div>
      <div className="container">
      <h1>Log in</h1>
      <form>
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
                <button className={`${((userName == "") || (password == "") ) ? 'btn-disabled' : 'btn-primary'}`} disabled={((userName == "") || (password == "") )? true : false  } onClick={handleSubmit}>Log in</button>
              </div>
            </div>
          </div>
        </div>
      </form>

      <div className='signUpLink'> Don't have an account? <Link to="/signUp">Sign up</Link></div>
    </div>
    </div>
  )
}
