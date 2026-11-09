import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { toast } from "react-toastify";
import AuthService from '../service/authService.js';

const USERNAME_PATTERN = /^[A-Za-z0-9._-]{3,50}$/

export function validateSignup({ userName, password, confirmPassword, agencyCode }) {
  const errors = {}
  if (userName && !USERNAME_PATTERN.test(userName)) {
    errors.userName = 'Use 3–50 letters, digits, dots, underscores or hyphens.'
  }
  if (password && (password.length < 8 || password.length > 72)) {
    errors.password = 'Password must be 8–72 characters.'
  }
  if (confirmPassword && password !== confirmPassword) {
    errors.confirmPassword = 'Passwords do not match.'
  }
  const complete = userName && password && confirmPassword && ['AUS', 'DAL', 'TEX'].includes(agencyCode)
  return { errors, valid: !!complete && Object.keys(errors).length === 0 }
}

export default function Signup() {
  const [userName, setUserName] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [agencyCode, setAgencyCode] = useState('')
  const [busy, setBusy] = useState(false)
  const navigate = useNavigate();

  const { errors, valid } = validateSignup({ userName, password, confirmPassword, agencyCode })

  async function handleSubmit(e) {
    e.preventDefault();
    if (!valid) return
    setBusy(true)
    try {
      const response = await AuthService.signup({
        username: userName,
        password: password,
        agencyCode: agencyCode,
      })

      if (response?.user && !response.error) {
        toast.success("Account created. When you first log in you will set up an authenticator app (such as Google Authenticator) for two-factor sign-in.", { autoClose: 10000 })
        navigate('/login')
      }
      else if (response.status === 409) {
        toast.error("That username is already taken.")
      }
      else {
        toast.error(response.error || "Sign-up failed")
      }
    }
    catch (error) {
      toast.error(error.message || 'Registration failed');
    }
    finally {
      setBusy(false)
    }
  }

  function clearForm(e) {
    e.preventDefault();
    setUserName('')
    setPassword('')
    setConfirmPassword('')
    setAgencyCode('')
  }

  const disabled = busy || !valid

  return (
    <div className='page'>
      <div className="container">
        <h1>Sign Up</h1>
        <form className='mt-4' onSubmit={handleSubmit}>
          <div>
            <label htmlFor="userName">User Name</label>
            <input id="userName" autoComplete="username" maxLength={50} value={userName} onChange={(e) => setUserName(e.target.value.trim())} aria-describedby="userName-help" />
            <div id="userName-help" className={errors.userName ? 'error' : 'form-text mb-2'}>
              {errors.userName || '3–50 characters: letters, digits, . _ -'}
            </div>
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
            <input id="password" type="password" autoComplete="new-password" maxLength={72} value={password} onChange={(e) => setPassword(e.target.value)} aria-describedby="password-help" />
            <div id="password-help" className={errors.password ? 'error' : 'form-text mb-2'}>
              {errors.password || '8–72 characters'}
            </div>
          </div>

          <div>
            <label htmlFor="confirmPassword">Confirm Password</label>
            <input id="confirmPassword" type="password" autoComplete="new-password" maxLength={72} value={confirmPassword} onChange={(e) => setConfirmPassword(e.target.value)} />
            {errors.confirmPassword && <div className="error">{errors.confirmPassword}</div>}
          </div>

          <p className="form-text">After signing up, your first login will ask you to set up an authenticator app for two-factor sign-in.</p>

          <div className="row">
            <div className="col-lg-12 full-width">
              <div className="row">
                <div className="col-lg-6">
                  <button type="button" className='secondary' onClick={clearForm}>Clear</button>
                </div>

                <div className="col-lg-6">
                  <button type="submit" className={disabled ? 'btn-disabled' : 'button'} disabled={disabled}>
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
