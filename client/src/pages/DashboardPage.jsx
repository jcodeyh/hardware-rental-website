import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import authService from '../service/authService';
import '../DashboardPage.css';

const GOVERNMENTS = ['Austin', 'Dallas', 'Texas'];
const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

// Shown only in local dev when the data service can't be reached, so the
// charts can be checked visually. Clearly badged as sample data on screen.
const SAMPLE_SUMMARY = {
  topCategories: [
    { category: 'Microcomputers, Handheld, Laptop, and Notebook', purchases: 54, totalAmount: 61234.5 },
    { category: 'Computer Software', purchases: 41, totalAmount: 48210.0 },
    { category: 'Network Equipment', purchases: 33, totalAmount: 39875.25 },
    { category: 'Office Supplies', purchases: 28, totalAmount: 6120.4 },
    { category: 'Telephone Equipment', purchases: 19, totalAmount: 14302.0 },
  ],
  typicalPrices: [
    { category: 'Microcomputers, Handheld, Laptop, and Notebook', low: 780, median: 912, high: 1150, purchases: 54 },
    { category: 'Computer Software', low: 120, median: 340, high: 610, purchases: 41 },
    { category: 'Network Equipment', low: 410, median: 655, high: 980, purchases: 33 },
    { category: 'Telephone Equipment', low: 95, median: 180, high: 260, purchases: 19 },
    { category: 'Servers', low: 'not available', median: 'not available', high: 'not available', purchases: 2 },
  ],
  topVendors: [
    { vendor: 'DELL MARKETING LP', purchases: 162, totalAmount: 245000 },
    { vendor: 'CDW GOVERNMENT LLC', purchases: 118, totalAmount: 187450.75 },
    { vendor: 'SHI GOVERNMENT SOLUTIONS', purchases: 87, totalAmount: 132900 },
    { vendor: 'PRESIDIO NETWORKED SOLUTIONS', purchases: 54, totalAmount: 98340.2 },
    { vendor: 'OFFICE DEPOT', purchases: 61, totalAmount: 21780.6 },
  ],
};

const money = (n) =>
  typeof n === 'number'
    ? n.toLocaleString('en-US', { style: 'currency', currency: 'USD' })
    : '—';

const compactMoney = (n) =>
  n.toLocaleString('en-US', { style: 'currency', currency: 'USD', notation: 'compact', maximumFractionDigits: 1 });

/* ── Horizontal bar chart (one series) ── */
const BarChart = ({ rows, valueKey, format, tooltip, id }) => {
  const [hover, setHover] = useState(null);
  const max = Math.max(...rows.map((r) => r[valueKey]), 1);

  return (
    <div className="bar-chart" id={id} role="list">
      {rows.map((r, i) => {
        const pct = (r[valueKey] / max) * 100;
        return (
          <div
            key={i}
            className={`bar-row ${hover === i ? 'bar-row-hover' : ''}`}
            role="listitem"
            onMouseEnter={() => setHover(i)}
            onMouseLeave={() => setHover(null)}
          >
            <div className="bar-label" title={r.label}>{r.label}</div>
            <div className="bar-track">
              <div className="bar-fill" style={{ width: `${Math.max(pct, 1)}%` }} />
              {hover === i && <div className="chart-tooltip">{tooltip(r)}</div>}
            </div>
            <div className="bar-value">{format(r[valueKey])}</div>
          </div>
        );
      })}
    </div>
  );
};

/* ── Range chart: low–high band with median dot, shared $ axis ── */
const PriceRangeChart = ({ rows }) => {
  const [hover, setHover] = useState(null);
  const valid = rows.filter((r) => typeof r.median === 'number');
  const max = Math.max(...valid.map((r) => r.high), 1);
  const pos = (v) => `${(v / max) * 100}%`;
  const ticks = [0, 0.25, 0.5, 0.75, 1].map((t) => t * max);

  return (
    <div className="range-chart" id="typical-prices-chart">
      {rows.map((r, i) => {
        const ok = typeof r.median === 'number';
        return (
          <div
            key={i}
            className={`bar-row ${hover === i ? 'bar-row-hover' : ''}`}
            onMouseEnter={() => setHover(i)}
            onMouseLeave={() => setHover(null)}
          >
            <div className="bar-label" title={r.category}>{r.category}</div>
            <div className="bar-track range-track">
              {ok ? (
                <>
                  <div className="range-band" style={{ left: pos(r.low), width: `calc(${pos(r.high)} - ${pos(r.low)})` }} />
                  <div className="range-median" style={{ left: pos(r.median) }} />
                  {hover === i && (
                    <div className="chart-tooltip" style={{ left: pos(r.median) }}>
                      <strong>{r.category}</strong><br />
                      Low {money(r.low)} · Median {money(r.median)} · High {money(r.high)}<br />
                      {r.purchases} purchases
                    </div>
                  )}
                </>
              ) : (
                <span className="range-na">Not available (fewer than 3 purchases)</span>
              )}
            </div>
            <div className="bar-value">{ok ? money(r.median) : '—'}</div>
          </div>
        );
      })}
      <div className="bar-row axis-row" aria-hidden="true">
        <div className="bar-label" />
        <div className="axis">
          {ticks.map((t, i) => (
            <span key={i} className="axis-tick" style={{ left: pos(t) }}>{compactMoney(t)}</span>
          ))}
        </div>
        <div className="bar-value" />
      </div>
      <div className="chart-legend">
        <span className="legend-item"><span className="legend-band" /> Typical range (25th–75th percentile)</span>
        <span className="legend-item"><span className="legend-dot" /> Median price</span>
      </div>
    </div>
  );
};

/* ── Card shell with chart / table toggle ── */
const ChartCard = ({ id, title, subtitle, wide, children, table }) => {
  const [showTable, setShowTable] = useState(false);
  return (
    <section className={`analytics-card ${wide ? 'analytics-card-wide' : ''}`} id={id}>
      <div className="analytics-card-header">
        <div>
          <h2 className="analytics-card-title">{title}</h2>
          {subtitle && <p className="analytics-card-subtitle">{subtitle}</p>}
        </div>
        {table && (
          <button className="btn btn-outline btn-sm-toggle" onClick={() => setShowTable((s) => !s)}>
            {showTable ? 'Show chart' : 'Show table'}
          </button>
        )}
      </div>
      {showTable ? table : children}
    </section>
  );
};

const DashboardPage = () => {
  const navigate = useNavigate();
  const { logout } = useAuth();
  const rawUser = localStorage.getItem('username');
  const username = rawUser && rawUser !== 'undefined' ? rawUser : 'User';

  const [selectedGov, setSelectedGov] = useState('');
  const [data, setData] = useState(null);
  const [isSample, setIsSample] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleLogout = async () => {
    try {
      await authService.logout();
    } catch (err) {
      console.error('Logout error:', err);
    } finally {
      localStorage.removeItem('username');
      logout();
      navigate('/login');
    }
  };

  const fetchSummary = async (gov) => {
    setLoading(true);
    setError(null);
    setData(null);
    setIsSample(false);
    try {
      const res = await fetch(`${API_BASE}/api/data/governments/${gov}/summary`, { credentials: 'include' });
      const json = await res.json();
      if (!json.success) {
        setError(json.message || `Could not load data for ${gov}.`);
      } else {
        setData(json);
      }
    } catch (err) {
      if (import.meta.env.DEV) {
        console.warn('Data service unreachable, showing sample data:', err);
        setData(SAMPLE_SUMMARY);
        setIsSample(true);
      } else {
        setError('The data service is not reachable right now. Please try again later.');
      }
    } finally {
      setLoading(false);
    }
  };

  const handleGovChange = (gov) => {
    setSelectedGov(gov);
    fetchSummary(gov);
  };

  const hasData =
    data &&
    (data.topCategories?.length || data.typicalPrices?.length || data.topVendors?.length);

  return (
    <div className="app-container" id="dashboard-page-container">
      {/* ── Navbar (same layout as the other pages) ── */}
      <nav className="navbar" id="dashboard-navbar">
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <button className="btn btn-secondary" onClick={() => navigate('/landingPage')}>← Back</button>
          <span className="navbar-brand" id="dashboard-navbar-logo">HaaS Portal</span>
        </div>
        <div className="navbar-right">
          <span className="navbar-username" id="dashboard-navbar-user">
            Welcome, <strong>{username}</strong>
          </span>
          <button className="btn btn-danger" id="dashboard-btn-logout" onClick={handleLogout}>
            Logout
          </button>
        </div>
      </nav>

      <main className="main-content" id="dashboard-main-content">
        <h1 className="page-title" id="dashboard-page-title">Government Procurement Analytics</h1>
        <p className="page-subtitle" id="dashboard-page-subtitle">
          Explore what governments buy, what they pay, and who they buy from.
        </p>

        {/* ── Government selector ── */}
        <div className="gov-selector-row" id="gov-selector-row" role="tablist">
          {GOVERNMENTS.map((gov) => (
            <button
              key={gov}
              id={`gov-btn-${gov.toLowerCase()}`}
              role="tab"
              aria-selected={selectedGov === gov}
              className={`btn ${selectedGov === gov ? 'btn-primary' : 'btn-secondary'} gov-btn`}
              onClick={() => handleGovChange(gov)}
            >
              {gov}
            </button>
          ))}
          {isSample && <span className="sample-badge">Sample data — data service not connected</span>}
        </div>

        {!selectedGov && (
          <div className="dashboard-message" id="dashboard-empty-state">
            <h2>Select a government to begin</h2>
            <p>Choose Austin, Dallas, or Texas above to view their procurement analytics.</p>
          </div>
        )}

        {selectedGov && loading && (
          <div className="dashboard-message" id="dashboard-loading-state">
            <div className="spinner" />
            <p>Loading data for <strong>{selectedGov}</strong>…</p>
          </div>
        )}

        {selectedGov && !loading && error && (
          <div className="modal-error" id="dashboard-error-state">{error}</div>
        )}

        {selectedGov && !loading && !error && data && !hasData && (
          <div className="dashboard-message" id="dashboard-no-data">
            <h2>No purchase data</h2>
            <p>{data.message || `There is no purchase data for ${selectedGov} yet.`}</p>
          </div>
        )}

        {selectedGov && !loading && !error && hasData && (
          <div className="analytics-grid" id="analytics-grid">
            <ChartCard
              id="section-top-categories"
              title="Most Common Goods & Services"
              subtitle="Number of purchases per category"
              table={
                <table className="data-table">
                  <thead><tr><th>Category</th><th className="num">Purchases</th><th className="num">Total</th></tr></thead>
                  <tbody>
                    {data.topCategories.map((c, i) => (
                      <tr key={i}><td>{c.category}</td><td className="num">{c.purchases.toLocaleString()}</td><td className="num">{money(c.totalAmount)}</td></tr>
                    ))}
                  </tbody>
                </table>
              }
            >
              <BarChart
                id="top-categories-chart"
                rows={data.topCategories.map((c) => ({ ...c, label: c.category }))}
                valueKey="purchases"
                format={(v) => v.toLocaleString()}
                tooltip={(r) => (
                  <><strong>{r.category}</strong><br />{r.purchases.toLocaleString()} purchases · {money(r.totalAmount)}</>
                )}
              />
            </ChartCard>

            <ChartCard
              id="section-top-vendors"
              title="Top Vendors"
              subtitle="Total amount spent per vendor"
              table={
                <table className="data-table">
                  <thead><tr><th>#</th><th>Vendor</th><th className="num">Purchases</th><th className="num">Total</th></tr></thead>
                  <tbody>
                    {data.topVendors.map((v, i) => (
                      <tr key={i}><td>{i + 1}</td><td>{v.vendor}</td><td className="num">{v.purchases.toLocaleString()}</td><td className="num">{money(v.totalAmount)}</td></tr>
                    ))}
                  </tbody>
                </table>
              }
            >
              <BarChart
                id="top-vendors-chart"
                rows={data.topVendors.map((v) => ({ ...v, label: v.vendor }))}
                valueKey="totalAmount"
                format={compactMoney}
                tooltip={(r) => (
                  <><strong>{r.vendor}</strong><br />{money(r.totalAmount)} · {r.purchases.toLocaleString()} purchases</>
                )}
              />
            </ChartCard>

            <ChartCard
              id="section-typical-prices"
              title="Typical Price per Item"
              subtitle={selectedGov === 'Dallas' ? 'Typical payment per category (Dallas has no unit prices)' : 'Unit price range per category'}
              wide
              table={
                <table className="data-table">
                  <thead><tr><th>Category</th><th className="num">Low</th><th className="num">Median</th><th className="num">High</th><th className="num">Purchases</th></tr></thead>
                  <tbody>
                    {data.typicalPrices.map((p, i) => (
                      <tr key={i}>
                        <td>{p.category}</td>
                        <td className="num">{money(p.low)}</td>
                        <td className="num"><strong>{money(p.median)}</strong></td>
                        <td className="num">{money(p.high)}</td>
                        <td className="num">{p.purchases ?? '—'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              }
            >
              <PriceRangeChart rows={data.typicalPrices} />
            </ChartCard>
          </div>
        )}
      </main>
    </div>
  );
};

export default DashboardPage;
