import { describe, it, expect } from 'vitest'
import { screen, waitFor, render } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route } from 'react-router-dom'
import Dashboard, { BudgetContextPanel } from './Dashboard.jsx'
import ProtectedRoute from '../components/ProtectedRoute.jsx'
import { mockFetch, renderRoutes, callsTo } from '../test/utils.jsx'

const governments = {
  success: true,
  governments: [
    { government: 'Austin', records: 10, from: '2020-01-01', to: '2024-12-31' },
    { government: 'Dallas', records: 10, from: '2020-01-01', to: '2024-12-31' },
    { government: 'Texas', records: 10, from: '2020-01-01', to: '2024-12-31' },
  ],
}

const summary = {
  success: true,
  from: '2020-01-01',
  to: '2024-12-31',
  priceBasis: 'unit',
  topCategories: [{ category: 'Laptops', purchases: 5 }],
  typicalPrices: [{ category: 'Laptops', low: 800, median: 1000, high: 1200, purchases: 5 }],
  topVendors: [{ vendor: 'Acme', purchases: 5, totalAmount: 5000 }],
}

const future = { v7_startTransition: true, v7_relativeSplatPath: true }

const routes = [<Route key="dash" path="/dashboard" element={<ProtectedRoute><Dashboard /></ProtectedRoute>} />]

function summaryCalls(fetchMock) {
  return fetchMock.mock.calls
    .map(([url]) => url)
    .filter((url) => url.includes('/summary'))
    .map((url) => new URL(url, 'http://localhost'))
}

function setup({ orgId = 'DAL', myHardware = [200, { categories: ['Laptop', 'Monitor'], items: [] }], me } = {}) {
  return mockFetch({
    'GET /api/app/auth/me': me || [200, { user: { userId: 'u1', username: 'alice', orgId } }],
    'GET /api/data/governments': [200, governments],
    'GET /api/app/dashboard/my-hardware': myHardware,
    'GET /api/data/governments/Austin/summary': [200, summary],
    'GET /api/data/governments/Dallas/summary': [200, summary],
    'GET /api/data/governments/Texas/summary': [200, summary],
  })
}

describe('Dashboard', () => {
  it('defaults the government to the user agency and filters by the hardware they used', async () => {
    const fetchMock = setup({ orgId: 'DAL' })
    renderRoutes(routes, ['/dashboard'])
    expect(await screen.findByText('Top vendors')).toBeInTheDocument()
    expect(screen.getByLabelText(/Government/)).toHaveValue('Dallas')
    const calls = summaryCalls(fetchMock)
    expect(calls).toHaveLength(1)
    expect(calls[0].pathname).toBe('/api/data/governments/Dallas/summary')
    expect(calls[0].searchParams.get('match')).toBe('Laptop,Monitor')
    expect(screen.getByRole('button', { name: "Hardware I've used" })).toHaveAttribute('aria-pressed', 'true')
    for (const [url, options] of fetchMock.mock.calls) {
      if (url.startsWith('/api/')) expect(options?.credentials).toBe('include')
    }
  })

  it('drops match= when toggled to All purchases and narrows it when a chip is removed', async () => {
    const fetchMock = setup({ orgId: 'TEX' })
    const ui = userEvent.setup()
    renderRoutes(routes, ['/dashboard'])
    await screen.findByText('Top vendors')
    expect(screen.getByLabelText(/Government/)).toHaveValue('Texas')

    await ui.click(screen.getByRole('button', { name: 'Remove Monitor' }))
    await waitFor(() => expect(summaryCalls(fetchMock).at(-1).searchParams.get('match')).toBe('Laptop'))

    await ui.click(screen.getByRole('button', { name: 'All purchases' }))
    await waitFor(() => expect(summaryCalls(fetchMock).at(-1).searchParams.has('match')).toBe(false))
    expect(screen.queryByRole('button', { name: 'Remove Laptop' })).not.toBeInTheDocument()

    await ui.click(screen.getByRole('button', { name: "Hardware I've used" }))
    await waitFor(() => expect(summaryCalls(fetchMock).at(-1).searchParams.get('match')).toBe('Laptop,Monitor'))
  })

  it('falls back to All purchases with a note when the user has no checkouts', async () => {
    const fetchMock = setup({ orgId: 'AUS', myHardware: [200, { categories: [], items: [] }] })
    renderRoutes(routes, ['/dashboard'])
    await screen.findByText('Top vendors')
    expect(screen.getByText('Check out hardware to filter by the types you use.')).toBeInTheDocument()
    expect(screen.getByLabelText(/Government/)).toHaveValue('Austin')
    expect(summaryCalls(fetchMock)[0].searchParams.has('match')).toBe(false)
  })

  it('silently uses All purchases when my-hardware fails', async () => {
    const fetchMock = setup({ orgId: 'XYZ', myHardware: [503, { error: 'down' }] })
    renderRoutes(routes, ['/dashboard'])
    await screen.findByText('Top vendors')
    expect(screen.getByLabelText(/Government/)).toHaveValue('Austin')
    expect(summaryCalls(fetchMock)[0].searchParams.has('match')).toBe(false)
  })

  it('sends the user to /login when the data service returns 401', async () => {
    mockFetch({
      'GET /api/app/auth/me': [200, { user: { userId: 'u1', username: 'alice', orgId: 'AUS' } }],
      'GET /api/data/governments': [401, { success: false, message: 'Please log in' }],
      'GET /api/app/dashboard/my-hardware': [200, { categories: [], items: [] }],
    })
    renderRoutes(routes, ['/dashboard'])
    expect(await screen.findByTestId('location')).toHaveTextContent('/login')
  })
})

describe('BudgetContextPanel', () => {
  it('posts budget and items and shows "Can\'t tell" when withinBudget is null', async () => {
    const fetchMock = mockFetch({
      'POST /api/app/budget-context': [200, {
        success: true,
        orgId: 'AUS',
        budget: 5000,
        items: [
          {
            description: 'laptop', quantity: 2,
            matchedCategory: 'Microcomputers, Handheld, Laptop, and Notebook', confidence: 0.92,
            unitPrice: { median: 1000, low: 800, high: 1200, purchases: 40 },
            estimatedCost: { low: 1600, typical: 2000, high: 2400 },
          },
          {
            description: 'quantum widget', quantity: 1,
            matchedCategory: null, confidence: 0,
            unitPrice: 'not available', estimatedCost: 'not available',
          },
        ],
        totalEstimate: { low: 1600, typical: 2000, high: 2400 },
        unpricedItems: ['quantum widget'],
        withinBudget: null,
      }],
    })
    const ui = userEvent.setup()
    render(<MemoryRouter future={future}><BudgetContextPanel /></MemoryRouter>)

    const budget = screen.getByLabelText('Budget (USD)')
    await ui.clear(budget)
    await ui.type(budget, '5000')
    const first = screen.getByLabelText('Item 1 description')
    await ui.clear(first)
    await ui.type(first, 'laptop')
    const qty = screen.getByLabelText('Item 1 quantity')
    await ui.clear(qty)
    await ui.type(qty, '2')
    await ui.click(screen.getByRole('button', { name: 'Add item' }))
    await ui.type(screen.getByLabelText('Item 2 description'), 'quantum widget')
    await ui.click(screen.getByRole('button', { name: 'Get context' }))

    expect(await screen.findByText("Can't tell — 1 item has no price data")).toBeInTheDocument()
    const [, options] = callsTo(fetchMock, 'POST', '/api/app/budget-context')[0]
    expect(options.credentials).toBe('include')
    expect(JSON.parse(options.body)).toEqual({
      budget: 5000,
      items: [{ description: 'laptop', quantity: 2 }, { description: 'quantum widget', quantity: 1 }],
    })
    expect(screen.getByText('Microcomputers, Handheld, Laptop, and Notebook')).toBeInTheDocument()
    expect(screen.getByText('No price data for: quantum widget')).toBeInTheDocument()
    expect(screen.getAllByText('$1,600.00 – $2,400.00 (typical $2,000.00)').length).toBeGreaterThan(0)
  })

  it('shows Within budget and Over budget verdicts', async () => {
    let within = true
    mockFetch({
      'POST /api/app/budget-context': () => [200, {
        success: true, budget: 20000, items: [], totalEstimate: { low: 1, typical: 2, high: 3 }, withinBudget: within,
      }],
    })
    const ui = userEvent.setup()
    render(<MemoryRouter future={future}><BudgetContextPanel /></MemoryRouter>)
    await ui.click(screen.getByRole('button', { name: 'Get context' }))
    expect(await screen.findByText('Within budget')).toBeInTheDocument()
    within = false
    await ui.click(screen.getByRole('button', { name: 'Get context' }))
    expect(await screen.findByText('Over budget')).toBeInTheDocument()
  })

  it('shows the upstream error message', async () => {
    mockFetch({ 'POST /api/app/budget-context': [502, { error: 'Projects service unavailable' }] })
    const ui = userEvent.setup()
    render(<MemoryRouter future={future}><BudgetContextPanel /></MemoryRouter>)
    await ui.click(screen.getByRole('button', { name: 'Get context' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Projects service unavailable')
  })
})
