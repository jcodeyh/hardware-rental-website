import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { toast } from "react-toastify";
import AuthService from '../service/authService.js';
export default function Signup() {
  const [userName, setUserName] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [agencyCode, setAgencyCode] = useState('')
  const navigate = useNavigate();
  async function handleSubmit(e) {
    e.preventDefault();

    e.preventDefault();
    let requestObject = {
      agencyCode: agencyCode,
      username: userName,
      password: password,
    }
    try {
      let response = await AuthService.signup(requestObject)

      if (response?.user) {
        console.log("Sign-Up  successful")
        toast.success("Sign-Up  successful")
        navigate('/login')
      }
      else if (response && response.error) {
        toast.error(response.error)
      }
      else {
        toast.error("signup failed with some other status-code")
      }
    }
    catch (error) {
      toast.error(error.message || 'Registration failed');
    }
  }

  function clearForm(e) {
    e.preventDefault();
    setUserName('')
    setPassword('')
    setConfirmPassword('')
  }

  return (
    <div className='page'>
      <div className="container">
        <h1>Sign Up</h1>
        <form className='mt-4'>
          <div>
            <label htmlFor="userName">User Name</label>
            <input id="userName" value={userName} onChange={(e) => setUserName(e.target.value)} />
          </div>

          <div>
            <label htmlFor="agencyCode">Agency</label>
            <select
              id="agencyCode"
              className="form-select"
              value={agencyCode}
              onChange={(e) => setAgencyCode(e.target.value)}
              required
            >
              <option value="">Select an agency</option>
              <option value="AUS">Austin</option>
              <option value="DAL">Dallas</option>
              <option value="TEX">Texas</option>
            </select>
          </div>

          <div>
            <label htmlFor="password">Password</label>
            <input id="password" type="password" value={password} onChange={(e) => setPassword(e.target.value)} />
          </div>

          <div>
            <label htmlFor="confirmPassword">Confirm Password</label>
            <input id="confirmPassword" type="password" value={confirmPassword} onChange={(e) => setConfirmPassword(e.target.value)} />
          </div>

          <div className="row">
            <div className="col-lg-12 full-width">
              <div className="row">
                <div className="col-lg-6">
                  <button type="button" className='secondary' onClick={clearForm}>Clear</button>
                </div>

                <div className="col-lg-6">
                  <button
                    className={
                      !userName.trim() || !agencyCode || !password || !confirmPassword ||
                        password !== confirmPassword
                        ? 'btn-disabled'
                        : 'button'
                    }
                    disabled={
                      !userName.trim() || !agencyCode || !password || !confirmPassword ||
                      password !== confirmPassword
                    }
                    onClick={handleSubmit}
                  >
                    Sign Up
                  </button>
                </div>
              </div>
            </div>
          </div>
        </form>
        <div className='signUpLink mt-4'>Already have an account? <Link to="/login">Login</Link></div>

      </div>
    </div>
  )
}
