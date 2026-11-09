import { describe, it, expect } from 'vitest'
import { screen } from '@testing-library/react'
import { Route, useLocation } from 'react-router-dom'
import ProtectedRoute from './ProtectedRoute.jsx'
import { mockFetch, renderRoutes } from '../test/utils.jsx'

function LoginProbe() {
  const location = useLocation()
  return <div>login page from {location.state?.from?.pathname}</div>
}

const routes = [
  <Route key="secret" path="/secret" element={<ProtectedRoute><div>secret content</div></ProtectedRoute>} />,
  <Route key="login" path="/login" element={<LoginProbe />} />,
]

describe('ProtectedRoute', () => {
  it('redirects to /login and remembers the intended path when /auth/me is 401', async () => {
    mockFetch({ 'GET /api/app/auth/me': [401, { error: 'Please log in' }] })
    renderRoutes(routes, ['/secret'])
    expect(screen.getByText('Loading…')).toBeInTheDocument()
    expect(await screen.findByText('login page from /secret')).toBeInTheDocument()
    expect(screen.queryByText('secret content')).not.toBeInTheDocument()
  })

  it('renders children when /auth/me is 200', async () => {
    const fetchMock = mockFetch({
      'GET /api/app/auth/me': [200, { user: { userId: 'u1', username: 'alice', orgId: 'AUS' } }],
    })
    renderRoutes(routes, ['/secret'])
    expect(await screen.findByText('secret content')).toBeInTheDocument()
    expect(fetchMock.mock.calls[0][1].credentials).toBe('include')
  })
})
