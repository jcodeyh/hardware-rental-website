import { render } from '@testing-library/react'
import { MemoryRouter, Routes, Route, useLocation } from 'react-router-dom'
import { vi } from 'vitest'
import { AuthProvider } from '../context/AuthContext.jsx'

export function jsonResponse(status, body) {
  return {
    ok: status >= 200 && status < 300,
    status,
    headers: { get: () => null },
    json: async () => {
      if (body === undefined) throw new Error('no body')
      return body
    },
  }
}

export function mockFetch(routes) {
  const fn = vi.fn(async (input, options = {}) => {
    const url = typeof input === 'string' ? input : input.url
    const method = (options.method || 'GET').toUpperCase()
    const path = url.split('?')[0]
    const handler = routes[`${method} ${path}`]
    if (!handler) return jsonResponse(404, { error: `no mock for ${method} ${url}` })
    const result = typeof handler === 'function' ? handler(url, options) : handler
    return jsonResponse(result[0], result[1])
  })
  vi.stubGlobal('fetch', fn)
  return fn
}

export function callsTo(fetchMock, method, path) {
  return fetchMock.mock.calls.filter(([url, options = {}]) =>
    (options.method || 'GET').toUpperCase() === method && url.split('?')[0] === path)
}

export function LocationProbe() {
  const location = useLocation()
  return <div data-testid="location">{location.pathname}</div>
}

export function renderRoutes(routes, initialEntries) {
  return render(
    <AuthProvider>
      <MemoryRouter initialEntries={initialEntries} future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
        <Routes>
          {routes}
          <Route path="*" element={<LocationProbe />} />
        </Routes>
      </MemoryRouter>
    </AuthProvider>
  )
}
