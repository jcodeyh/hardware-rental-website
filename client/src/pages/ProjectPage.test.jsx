import { describe, it, expect, vi } from 'vitest'
import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { Route } from 'react-router-dom'
import ProjectPage from './ProjectPage.jsx'
import ProtectedRoute from '../components/ProtectedRoute.jsx'
import { mockFetch, renderRoutes, callsTo } from '../test/utils.jsx'

vi.mock('react-toastify', () => ({
  toast: { success: vi.fn(), error: vi.fn(), warning: vi.fn() },
}))

const projectInfo = {
  projectId: 'p1',
  projectName: 'Vision Lab',
  projectDesc: 'Cameras and laptops',
  creatorId: 'u1',
  orgId: 'AUS',
  budget: 10000,
  joined_users: ['u1'],
  hardwareList: [
    { hardwareId: 'hw-1', name: 'Laptop', allocation: 10, reserved: 8, out: 3, remaining: 5 },
    { hardwareId: 'hw-2', name: 'Monitor', allocation: 4, reserved: 4, out: 0, remaining: 4 },
  ],
}

const routes = [<Route key="p" path="/project/:projectId" element={<ProtectedRoute><ProjectPage /></ProtectedRoute>} />]

function setup(extra = {}) {
  return mockFetch({
    'GET /api/app/auth/me': [200, { user: { userId: 'u1', username: 'alice', orgId: 'AUS' } }],
    'GET /api/app/projects/p1': [200, { projectInfo }],
    ...extra,
  })
}

describe('ProjectPage', () => {
  it('renders name, planned, reserved, out and remaining per hardware item', async () => {
    setup()
    renderRoutes(routes, ['/project/p1'])
    expect(await screen.findByText('Vision Lab')).toBeInTheDocument()
    const laptop = within(document.getElementById('hw-row-hw-1'))
    expect(laptop.getByText('Laptop')).toBeInTheDocument()
    const cell = (row, label) => row.querySelector(`[data-label="${label}"]`).textContent
    const laptopRow = document.getElementById('hw-row-hw-1')
    expect(cell(laptopRow, 'planned')).toBe('10')
    expect(cell(laptopRow, 'reserved')).toBe('8')
    expect(cell(laptopRow, 'out')).toBe('3')
    expect(cell(laptopRow, 'remaining')).toBe('5')
    expect(document.getElementById('btn-checkin-hw-2')).toBeDisabled()
    expect(document.getElementById('btn-checkout-hw-2')).toBeEnabled()
    expect(screen.getByText('alice')).toBeInTheDocument()
  })

  it('caps check-out at remaining and check-in at out', async () => {
    const fetchMock = setup({ 'POST /api/app/hardware/check-out': [200, { success: true }] })
    const ui = userEvent.setup()
    renderRoutes(routes, ['/project/p1'])
    await screen.findByText('Vision Lab')

    await ui.click(document.getElementById('btn-checkin-hw-1'))
    await ui.type(screen.getByLabelText('Quantity'), '4')
    await ui.click(screen.getByRole('button', { name: 'Submit' }))
    expect(screen.getByText('Only 3 units are checked out.')).toBeInTheDocument()
    await ui.click(screen.getByRole('button', { name: 'Cancel' }))

    await ui.click(document.getElementById('btn-checkout-hw-1'))
    await ui.type(screen.getByLabelText('Quantity'), '6')
    await ui.click(screen.getByRole('button', { name: 'Submit' }))
    expect(screen.getByText('Only 5 units remaining.')).toBeInTheDocument()
    expect(callsTo(fetchMock, 'POST', '/api/app/hardware/check-out')).toHaveLength(0)

    await ui.clear(screen.getByLabelText('Quantity'))
    await ui.type(screen.getByLabelText('Quantity'), '5')
    await ui.click(screen.getByRole('button', { name: 'Submit' }))
    const row = document.getElementById('hw-row-hw-1')
    await waitFor(() => expect(row.querySelector('[data-label="remaining"]').textContent).toBe('0'))
    expect(row.querySelector('[data-label="out"]').textContent).toBe('8')
    const body = JSON.parse(callsTo(fetchMock, 'POST', '/api/app/hardware/check-out')[0][1].body)
    expect(body).toMatchObject({ projectId: 'p1', hardwareId: 'hw-1', quantity: 5 })
    expect(document.getElementById('btn-checkout-hw-1')).toBeDisabled()
  })
})
