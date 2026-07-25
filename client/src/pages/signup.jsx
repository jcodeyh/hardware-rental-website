import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { toast } from "react-toastify";
export default function Signup() {
  const [userName, setUserName] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const navigate = useNavigate();
  function submitSignUp(e) {
    e.preventDefault();
    toast.success("Sign-Up Functionality");
    navigate('/login')
  }

  return (
    <div>
      <div className="container">
      <h1>Sign Up</h1>
      <form onSubmit={submitSignUp}>
        <div>
          <label htmlFor="userName">User Name</label>
          <input id="userName" value={userName} placeholder='Enter User Name' onChange={(e) => setUserName(e.target.value)}/>
        </div>

        <div>
          <label htmlFor="password">Password</label>
          <input id="password" type="password" value={password} placeholder='Enter New Password' onChange={(e) => setPassword(e.target.value)}/>
        </div>

         <div>
          <label htmlFor="confirmPassword">Confirm Password</label>
          <input id="confirmPassword" type="password" value={confirmPassword} placeholder='Enter Confirm Password' onChange={(e) => setConfirmPassword(e.target.value)}/>
        </div>

        <div className="row">
          <div className="col-lg-12 full-width">
            <button type="submit" disabled="">Sign Up</button>
          </div>
        </div>
      </form>

    </div>
    </div>
  )
}
