import { useState } from 'react'
import { useNavigate, useLocation, Link } from 'react-router-dom'
import { useAuth } from '../context/AuthContext.jsx'
import { toast } from "react-toastify";
import AuthService from '../service/authService.js';

const CODE_PATTERN = /^\d{6}$/

function targetPath(state) {
  const from = state?.from
  if (from?.pathname && from.pathname !== '/login') {
    return `${from.pathname}${from.search || ''}${from.hash || ''}`
  }
  return '/landingPage'
}

export default function Login() {
  const [userName, setUserName] = useState('')
  const [password, setPassword] = useState('')
  const [step, setStep] = useState('password')
  const [setupInfo, setSetupInfo] = useState(null)
  const [code, setCode] = useState('')
  const [busy, setBusy] = useState(false)
  const navigate = useNavigate();
  const location = useLocation();
  const { setUser } = useAuth();

  function finish(user) {
    setUser(user)
    toast.success(`Welcome, ${user.username}`)
    navigate(targetPath(location.state), { replace: true })
  }

  function startOver() {
    setStep('password')
    setSetupInfo(null)
    setCode('')
    setPassword('')
  }

  async function handlePassword(e) {
    e.preventDefault();
    if (!userName || !password) return
    setBusy(true)
    try {
      const response = await AuthService.login({ username: userName, password })
      if (response.error) {
        if (response.status === 429) {
          toast.error("Too many login attempts. Please wait a few minutes and try again.")
        } else if (response.status === 401) {
          toast.error("Login failed: invalid username or password")
        } else {
          toast.error("Login failed: " + response.error)
        }
        return
      }
      if (response.user && !response.nextStep) {
        finish(response.user)
        return
      }
      if (response.nextStep === '2fa_setup') {
        const setup = await AuthService.setupTwoFactor()
        if (setup.error || !setup.qrCodeDataUrl) {
          toast.error("Could not start authenticator setup: " + (setup.error || "no QR code returned"))
          return
        }
        setSetupInfo({ qrCodeDataUrl: setup.qrCodeDataUrl, secret: setup.secret })
        setCode('')
        setStep('2fa_setup')
        return
      }
      if (response.nextStep === '2fa_verify') {
        setCode('')
        setStep('2fa_verify')
        return
      }
      toast.error("Login failed: unexpected response from the server")
    }
    catch {
      toast.error("Login failed: network error");
    }
    finally {
      setBusy(false)
    }
  }

  async function handleVerify(e) {
    e.preventDefault();
    if (!CODE_PATTERN.test(code)) {
      toast.error("Enter the 6-digit code from your authenticator app")
      return
    }
    setBusy(true)
    try {
      const response = await AuthService.verifyTwoFactor(code)
      if (response.user && !response.error) {
        finish(response.user)
        return
      }
      const expired = response.status === 440 || response.status === 409 ||
        (response.status === 401 && /expire|log ?in again/i.test(response.error || ''))
      if (expired) {
        toast.error("Your sign-in timed out. Please enter your password again.")
        startOver()
        return
      }
      toast.error(response.status === 401 ? "That code is not valid. Try the current code." : "Verification failed: " + response.error)
      setCode('')
    }
    catch {
      toast.error("Verification failed: network error");
    }
    finally {
      setBusy(false)
    }
  }

  function clearForm(e){
    e.preventDefault();
    setUserName('')
    setPassword('')
  }

  const passwordDisabled = busy || userName === '' || password === ''
  const codeDisabled = busy || !CODE_PATTERN.test(code)

  return (
    <div className='page'>
      <div className="container">
      <h1>Log in</h1>

      {step === 'password' && (
        <form className='mt-4' onSubmit={handlePassword}>
          <div>
            <label htmlFor="userName">User Name</label>
            <input id="userName" autoComplete="username" value={userName} onChange={(e) => setUserName(e.target.value)}/>
          </div>

          <div>
            <label htmlFor="password">Password</label>
            <input id="password" type="password" autoComplete="current-password" value={password} onChange={(e) => setPassword(e.target.value)}/>
          </div>

          <div className="row">
            <div className="col-lg-12 full-width">
              <div className="row">
                <div className="col-lg-6">
                  <button type="button" className='secondary' onClick={clearForm}>Clear</button>
                </div>

                <div className="col-lg-6">
                  <button type="submit" className={passwordDisabled ? 'btn-disabled' : 'button'} disabled={passwordDisabled}>Log in</button>
                </div>
              </div>
            </div>
          </div>
        </form>
      )}

      {step !== 'password' && (
        <form className='mt-4' onSubmit={handleVerify}>
          {step === '2fa_setup' && setupInfo && (
            <div className="mb-3">
              <p>Set up two-factor authentication. Scan this QR code with an authenticator app such as Google Authenticator, then enter the 6-digit code it shows.</p>
              <img src={setupInfo.qrCodeDataUrl} alt="QR code for your authenticator app" style={{ display: 'block', width: 200, height: 200, margin: '0 auto 12px' }} />
              {setupInfo.secret && (
                <p style={{ fontSize: 14 }}>
                  Can't scan it? Enter this key manually: <code data-testid="totp-secret" style={{ wordBreak: 'break-all' }}>{setupInfo.secret}</code>
                </p>
              )}
            </div>
          )}
          {step === '2fa_verify' && (
            <p>Enter the 6-digit code from your authenticator app.</p>
          )}

          <div>
            <label htmlFor="totpCode">Authentication code</label>
            <input
              id="totpCode"
              inputMode="numeric"
              autoComplete="one-time-code"
              maxLength={6}
              pattern="\d{6}"
              value={code}
              onChange={(e) => setCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
              autoFocus
            />
          </div>

          <div className="row">
            <div className="col-lg-12 full-width">
              <div className="row">
                <div className="col-lg-6">
                  <button type="button" className='secondary' onClick={startOver}>Back</button>
                </div>

                <div className="col-lg-6">
                  <button type="submit" className={codeDisabled ? 'btn-disabled' : 'button'} disabled={codeDisabled}>Verify</button>
                </div>
              </div>
            </div>
          </div>
        </form>
      )}

      <div className='signUpLink mt-4'> Don't have an account? <Link to="/signUp">Sign up</Link></div>
    </div>
    </div>
  )
}
