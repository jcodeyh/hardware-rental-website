import { describe, it, expect, vi, beforeEach } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { Route } from 'react-router-dom'
import { toast } from 'react-toastify'
import Login from './login.jsx'
import { mockFetch, renderRoutes, callsTo } from '../test/utils.jsx'

vi.mock('react-toastify', () => ({
  toast: { success: vi.fn(), error: vi.fn(), warning: vi.fn() },
}))

const user = { userId: 'u1', username: 'alice', orgId: 'AUS' }
const routes = [<Route key="login" path="/login" element={<Login />} />]

async function submitPassword() {
  const ui = userEvent.setup()
  await ui.type(screen.getByLabelText('User Name'), 'alice')
  await ui.type(screen.getByLabelText('Password'), 'correct-horse')
  await ui.click(screen.getByRole('button', { name: 'Log in' }))
  return ui
}

describe('Login', () => {
  beforeEach(() => {
    vi.mocked(toast.error).mockClear()
  })

  it('logs in directly when nextStep is null and goes back to the intended page', async () => {
    const fetchMock = mockFetch({
      'GET /api/app/auth/me': [401, { error: 'Please log in' }],
      'POST /api/app/auth/login': [200, { user, nextStep: null }],
    })
    renderRoutes(routes, [{ pathname: '/login', state: { from: { pathname: '/dashboard' } } }])
    await submitPassword()
    expect(await screen.findByTestId('location')).toHaveTextContent('/dashboard')
    const [, options] = callsTo(fetchMock, 'POST', '/api/app/auth/login')[0]
    expect(JSON.parse(options.body)).toEqual({ username: 'alice', password: 'correct-horse' })
    expect(options.credentials).toBe('include')
  })

  it('defaults to /landingPage after login', async () => {
    mockFetch({
      'GET /api/app/auth/me': [401, { error: 'Please log in' }],
      'POST /api/app/auth/login': [200, { user, nextStep: null }],
    })
    renderRoutes(routes, ['/login'])
    await submitPassword()
    expect(await screen.findByTestId('location')).toHaveTextContent('/landingPage')
  })

  it('asks for a code when nextStep is 2fa_verify and verifies it', async () => {
    const fetchMock = mockFetch({
      'GET /api/app/auth/me': [401, { error: 'Please log in' }],
      'POST /api/app/auth/login': [200, { user: null, nextStep: '2fa_verify' }],
      'POST /api/app/auth/2fa/verify': [200, { user }],
    })
    renderRoutes(routes, ['/login'])
    const ui = await submitPassword()
    const codeInput = await screen.findByLabelText('Authentication code')
    expect(screen.queryByRole('img')).not.toBeInTheDocument()
    expect(callsTo(fetchMock, 'POST', '/api/app/auth/2fa/setup')).toHaveLength(0)
    await ui.type(codeInput, '123456')
    await ui.click(screen.getByRole('button', { name: 'Verify' }))
    expect(await screen.findByTestId('location')).toHaveTextContent('/landingPage')
    const [, options] = callsTo(fetchMock, 'POST', '/api/app/auth/2fa/verify')[0]
    expect(JSON.parse(options.body)).toEqual({ code: '123456' })
  })

  it('shows the QR code and secret when nextStep is 2fa_setup', async () => {
    const fetchMock = mockFetch({
      'GET /api/app/auth/me': [401, { error: 'Please log in' }],
      'POST /api/app/auth/login': [200, { user: null, nextStep: '2fa_setup' }],
      'POST /api/app/auth/2fa/setup': [200, { qrCodeDataUrl: 'data:image/png;base64,AAAA', secret: 'JBSWY3DPEHPK3PXP' }],
      'POST /api/app/auth/2fa/verify': [200, { user }],
    })
    renderRoutes(routes, ['/login'])
    const ui = await submitPassword()
    const qr = await screen.findByRole('img', { name: /QR code/i })
    expect(qr).toHaveAttribute('src', 'data:image/png;base64,AAAA')
    expect(screen.getByTestId('totp-secret')).toHaveTextContent('JBSWY3DPEHPK3PXP')
    await ui.type(screen.getByLabelText('Authentication code'), '654321')
    await ui.click(screen.getByRole('button', { name: 'Verify' }))
    expect(await screen.findByTestId('location')).toHaveTextContent('/landingPage')
    expect(callsTo(fetchMock, 'POST', '/api/app/auth/2fa/setup')).toHaveLength(1)
  })

  it('returns to the password step when the pending sign-in expired', async () => {
    mockFetch({
      'GET /api/app/auth/me': [401, { error: 'Please log in' }],
      'POST /api/app/auth/login': [200, { user: null, nextStep: '2fa_verify' }],
      'POST /api/app/auth/2fa/verify': [401, { error: 'Your sign-in expired. Log in again.' }],
    })
    renderRoutes(routes, ['/login'])
    const ui = await submitPassword()
    await ui.type(await screen.findByLabelText('Authentication code'), '123456')
    await ui.click(screen.getByRole('button', { name: 'Verify' }))
    expect(await screen.findByLabelText('Password')).toHaveValue('')
    expect(toast.error).toHaveBeenCalled()
  })

  it('keeps the code step on an invalid code', async () => {
    mockFetch({
      'GET /api/app/auth/me': [401, { error: 'Please log in' }],
      'POST /api/app/auth/login': [200, { user: null, nextStep: '2fa_verify' }],
      'POST /api/app/auth/2fa/verify': [401, { error: 'Invalid code' }],
    })
    renderRoutes(routes, ['/login'])
    const ui = await submitPassword()
    await ui.type(await screen.findByLabelText('Authentication code'), '000000')
    await ui.click(screen.getByRole('button', { name: 'Verify' }))
    await waitFor(() => expect(toast.error).toHaveBeenCalledWith('That code is not valid. Try the current code.'))
    expect(screen.getByLabelText('Authentication code')).toBeInTheDocument()
  })

  it('reports bad credentials', async () => {
    mockFetch({
      'GET /api/app/auth/me': [401, { error: 'Please log in' }],
      'POST /api/app/auth/login': [401, { error: 'Invalid username or password' }],
    })
    renderRoutes(routes, ['/login'])
    await submitPassword()
    await waitFor(() => expect(toast.error).toHaveBeenCalledWith('Login failed: invalid username or password'))
  })
})
