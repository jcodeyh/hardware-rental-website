import React, { useCallback, useEffect, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext.jsx";
import authService from "../service/authService.js";
import "./Dashboard.css";

const GATEWAY = import.meta.env.VITE_GATEWAY_BASE_URL || "";
const NA = "not available";
const AGENCY_GOVERNMENT = { AUS: "Austin", DAL: "Dallas", TEX: "Texas" };

async function callData(path) {
  try {
    const response = await fetch(GATEWAY + path, { credentials: "include" });
    let body;
    try {
      body = await response.json();
    } catch {
      body = {};
    }
    if (response.status === 401) return { unauthorized: true, body };
    if (!response.ok && body.success === undefined) body.success = false;
    return { body };
  } catch {
    return { body: { success: false, message: "Could not reach the gateway. Try again in a minute." } };
  }
}

const usd = (v) =>
  v === NA || v === null || v === undefined || typeof v !== "number"
    ? "Not available"
    : v.toLocaleString("en-US", { style: "currency", currency: "USD" });

const longDay = (iso) =>
  new Date(`${iso}T00:00:00`).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });

function rangeText(from, to) {
  if (from && to) return `Showing ${longDay(from)} to ${longDay(to)}`;
  if (from) return `Showing ${longDay(from)} onward`;
  if (to) return `Showing through ${longDay(to)}`;
  return "Showing all dates";
}

const compactUsd = (v) =>
  typeof v === "number"
    ? v.toLocaleString("en-US", { style: "currency", currency: "USD", notation: "compact", maximumFractionDigits: 1 })
    : "—";

// Horizontal bar chart, one series. Hover a row for the exact numbers.
function BarChart({ rows, label, value, format, tooltip }) {
  const [hover, setHover] = useState(null);
  const max = Math.max(...rows.map((r) => value(r) || 0), 1);
  return (
    <ol className="dash-bars">
      {rows.map((r, i) => (
        <li
          key={`${label(r)}-${i}`}
          className={hover === i ? "dash-row-hover" : ""}
          onMouseEnter={() => setHover(i)}
          onMouseLeave={() => setHover(null)}
        >
          <span className="dash-bar-label" title={label(r)}>{label(r)}</span>
          <span className="dash-bar-track">
            <span className="dash-bar" style={{ width: `${Math.max((100 * (value(r) || 0)) / max, 1)}%` }} />
            {hover === i && <span className="dash-tooltip">{tooltip(r)}</span>}
          </span>
          <span className="dash-bar-value">{format(value(r))}</span>
        </li>
      ))}
    </ol>
  );
}

// Low–high band (25th–75th percentile) with a dot at the median, on a shared $ axis.
function PriceRangeChart({ rows, priceLabel }) {
  const [hover, setHover] = useState(null);
  const priced = rows.filter((r) => typeof r.median === "number");
  const max = Math.max(...priced.map((r) => (typeof r.high === "number" ? r.high : r.median)), 1);
  const pos = (v) => `${(100 * v) / max}%`;
  const ticks = [0, 0.25, 0.5, 0.75, 1].map((t) => t * max);

  return (
    <div className="dash-range-chart">
      <ol className="dash-bars">
        {rows.map((r, i) => {
          const ok = typeof r.median === "number";
          const low = typeof r.low === "number" ? r.low : r.median;
          const high = typeof r.high === "number" ? r.high : r.median;
          return (
            <li
              key={`${r.category}-${i}`}
              className={hover === i ? "dash-row-hover" : ""}
              onMouseEnter={() => setHover(i)}
              onMouseLeave={() => setHover(null)}
            >
              <span className="dash-bar-label" title={r.category}>{r.category}</span>
              <span className="dash-range-track">
                {ok ? (
                  <>
                    <span className="dash-range-band" style={{ left: pos(low), width: `calc(${pos(high)} - ${pos(low)})` }} />
                    <span className="dash-range-median" style={{ left: pos(r.median) }} />
                    {hover === i && (
                      <span className="dash-tooltip">
                        <strong>{r.category}</strong>
                        <br />
                        Low {usd(r.low)} · Typical {usd(r.median)} · High {usd(r.high)}
                        <br />
                        {r.purchases} purchases
                      </span>
                    )}
                  </>
                ) : (
                  <span className="dash-range-na">Not available (fewer than 3 purchases)</span>
                )}
              </span>
              <span className="dash-bar-value">{ok ? compactUsd(r.median) : "—"}</span>
            </li>
          );
        })}
        <li className="dash-axis-row" aria-hidden="true">
          <span />
          <span className="dash-axis">
            {ticks.map((t, i) => (
              <span key={i} className="dash-axis-tick" style={{ left: pos(t) }}>{compactUsd(t)}</span>
            ))}
          </span>
          <span />
        </li>
      </ol>
      <div className="dash-legend">
        <span><span className="dash-legend-band" /> Typical range (25th–75th percentile)</span>
        <span><span className="dash-legend-dot" /> Typical {priceLabel} (median)</span>
      </div>
    </div>
  );
}

// Card with a chart / table toggle so exact values are always reachable.
function ChartCard({ title, subtitle, wide, table, children }) {
  const [showTable, setShowTable] = useState(false);
  return (
    <section className={wide ? "dash-card dash-wide" : "dash-card"}>
      <div className="dash-card-header">
        <div>
          <h2>{title}</h2>
          {subtitle && <p className="dash-card-subtitle">{subtitle}</p>}
        </div>
        <button type="button" className="btn btn-outline dash-toggle" onClick={() => setShowTable((s) => !s)}>
          {showTable ? "Show chart" : "Show table"}
        </button>
      </div>
      {showTable ? table : children}
    </section>
  );
}

const hasPrice = (item) => item.estimatedCost && typeof item.estimatedCost === "object";

function unpricedList(result) {
  if (Array.isArray(result.unpricedItems)) {
    return result.unpricedItems.map((u) => (typeof u === "string" ? u : u?.description || JSON.stringify(u)));
  }
  return (result.items || []).filter((i) => !hasPrice(i)).map((i) => i.description);
}

function confidenceText(c) {
  if (typeof c === "number") return c <= 1 ? `${Math.round(c * 100)}%` : String(c);
  return c || "";
}

function costRange(cost) {
  if (!cost || typeof cost !== "object") return "No price data";
  return `${usd(cost.low)} – ${usd(cost.high)} (typical ${usd(cost.typical)})`;
}

function BudgetVerdict({ result }) {
  if (result.withinBudget === true) return <p className="dash-verdict dash-ok">Within budget</p>;
  if (result.withinBudget === false) return <p className="dash-verdict dash-over">Over budget</p>;
  const n = unpricedList(result).length;
  return (
    <p className="dash-verdict dash-unknown">
      Can't tell — {n} item{n === 1 ? "" : "s"} {n === 1 ? "has" : "have"} no price data
    </p>
  );
}

const emptyRow = () => ({ description: "", quantity: 1 });

export function BudgetContextPanel({ wide, onUnauthorized }) {
  const [budget, setBudget] = useState(20000);
  const [rows, setRows] = useState([{ description: "Laptop computer", quantity: 10 }]);
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const updateRow = (index, field, value) =>
    setRows((prev) => prev.map((r, i) => (i === index ? { ...r, [field]: value } : r)));

  const submit = async (e) => {
    e.preventDefault();
    const budgetValue = Number(budget);
    if (budget === "" || !Number.isFinite(budgetValue) || budgetValue < 0) {
      setError("Enter a budget of 0 or more.");
      return;
    }
    const items = rows.map((r) => ({ description: r.description.trim(), quantity: Number(r.quantity) }));
    if (items.some((i) => !i.description || !Number.isInteger(i.quantity) || i.quantity < 1)) {
      setError("Each item needs a description and a whole-number quantity of 1 or more.");
      return;
    }
    setError("");
    setBusy(true);
    try {
      const body = await authService.getBudgetContext({ budget: budgetValue, items });
      if (body.status === 401) {
        onUnauthorized?.();
        return;
      }
      if (body.error || body.success === false) {
        setResult(null);
        setError(body.error || body.errorMessage || body.message || "Could not get budget context.");
        return;
      }
      setResult(body);
    } catch {
      setResult(null);
      setError("Could not reach the gateway. Try again in a minute.");
    } finally {
      setBusy(false);
    }
  };

  const unpriced = result ? unpricedList(result) : [];

  return (
    <section className={wide ? "dash-card dash-wide" : "dash-card"} aria-labelledby="budget-heading">
      <h2 id="budget-heading">Budget context</h2>
      <form className="dash-budget" onSubmit={submit}>
        <label className="dash-budget-total">
          Budget (USD)
          <input type="number" min="0" step="any" value={budget} onChange={(e) => setBudget(e.target.value)} />
        </label>
        {rows.map((row, index) => (
          <div className="dash-budget-form" key={index}>
            <input
              value={row.description}
              onChange={(e) => updateRow(index, "description", e.target.value)}
              placeholder="Item description"
              aria-label={`Item ${index + 1} description`}
            />
            <input
              type="number"
              min="1"
              value={row.quantity}
              onChange={(e) => updateRow(index, "quantity", e.target.value)}
              aria-label={`Item ${index + 1} quantity`}
            />
            {rows.length > 1 && (
              <button
                type="button"
                className="btn btn-outline-secondary btn-sm"
                onClick={() => setRows((prev) => prev.filter((_, i) => i !== index))}
                aria-label={`Remove item ${index + 1}`}
              >
                ×
              </button>
            )}
          </div>
        ))}
        <div className="dash-budget-actions">
          <button type="button" className="btn btn-outline-secondary btn-sm" onClick={() => setRows((prev) => [...prev, emptyRow()])}>
            Add item
          </button>
          <button className="btn btn-primary btn-sm" type="submit" disabled={busy}>
            {busy ? "Checking…" : "Get context"}
          </button>
        </div>
      </form>
      <p className="dash-note">
        Items are matched to purchase categories from public records. Category names can be long — Austin uses names like
        “Microcomputers, Handheld, Laptop, and Notebook” — so a plain description such as “laptop” works best.
      </p>
      {error && <p className="dash-error" role="alert">{error}</p>}
      {result && (
        <div className="dash-budget-result">
          <BudgetVerdict result={result} />
          <table className="table table-sm">
            <thead>
              <tr><th>Item</th><th>Qty</th><th>Matched category</th><th>Estimated cost</th></tr>
            </thead>
            <tbody>
              {(result.items || []).map((item, i) => (
                <tr key={`${item.description}-${i}`}>
                  <td>{item.description}</td>
                  <td>{item.quantity}</td>
                  <td>
                    {item.matchedCategory || "No match"}
                    {item.confidence !== undefined && item.confidence !== null && (
                      <small className="dash-muted"> ({confidenceText(item.confidence)} match)</small>
                    )}
                  </td>
                  <td>{costRange(item.estimatedCost)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <p>
            <strong>Total estimate:</strong> {costRange(result.totalEstimate)}
            {typeof result.budget === "number" && <> against a budget of {usd(result.budget)}</>}
          </p>
          {unpriced.length > 0 && (
            <p className="dash-sample">No price data for: {unpriced.join(", ")}</p>
          )}
        </div>
      )}
      <p className="dash-note">Price context from public purchase records. Not a recommendation.</p>
    </section>
  );
}

export default function Dashboard() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [governments, setGovernments] = useState([]);
  const [selected, setSelected] = useState("");
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [draftFrom, setDraftFrom] = useState("");
  const [draftTo, setDraftTo] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [attempt, setAttempt] = useState(0);
  const [myCategories, setMyCategories] = useState([]);
  const [chips, setChips] = useState([]);
  const [mode, setMode] = useState("all");
  const [hardwareReady, setHardwareReady] = useState(false);

  const toLogin = useCallback(
    () => navigate("/login", { replace: true, state: { from: location } }),
    [navigate, location]
  );

  const orgId = user?.orgId;

  useEffect(() => {
    let ignore = false;
    callData("/api/data/governments").then(({ body, unauthorized }) => {
      if (ignore) return;
      if (unauthorized) return toLogin();
      if (!body.success) return setError(body.message || "Could not load governments.");
      const list = body.governments || [];
      setGovernments(list);
      const preferred = AGENCY_GOVERNMENT[orgId];
      const initial = list.find((g) => g.government === preferred) || list[0];
      if (initial) setSelected(initial.government);
    });
    return () => {
      ignore = true;
    };
  }, [orgId, toLogin]);

  useEffect(() => {
    let ignore = false;
    authService
      .getMyHardware()
      .then((body) => {
        if (ignore) return;
        if (body.status === 401) return toLogin();
        const categories = body.error ? [] : (body.categories || []).filter(Boolean);
        setMyCategories(categories);
        setChips(categories);
        setMode(categories.length ? "mine" : "all");
      })
      .catch(() => {
        if (ignore) return;
        setMyCategories([]);
        setChips([]);
        setMode("all");
      })
      .finally(() => {
        if (!ignore) setHardwareReady(true);
      });
    return () => {
      ignore = true;
    };
  }, [toLogin]);

  const matchQuery = mode === "mine" && chips.length ? chips.join(",") : "";

  useEffect(() => {
    if (!selected || !hardwareReady) return;
    let ignore = false;
    const params = new URLSearchParams();
    if (dateFrom) params.set("from", dateFrom);
    if (dateTo) params.set("to", dateTo);
    if (matchQuery) params.set("match", matchQuery);
    const query = params.toString();
    setLoading(true);
    setError("");
    callData(`/api/data/governments/${encodeURIComponent(selected)}/summary${query ? `?${query}` : ""}`).then(
      ({ body, unauthorized }) => {
        if (ignore) return;
        if (unauthorized) return toLogin();
        setLoading(false);
        if (!body.success) {
          setSummary(null);
          return setError(body.message || "Could not load the summary.");
        }
        setSummary(body);
      }
    );
    return () => {
      ignore = true;
    };
  }, [selected, dateFrom, dateTo, attempt, matchQuery, hardwareReady, toLogin]);

  const applyDates = (e) => {
    e.preventDefault();
    setDateFrom(draftFrom);
    setDateTo(draftTo);
    setAttempt((n) => n + 1);
  };

  const selectGovernment = (government) => {
    setSelected(government);
    setDraftFrom(dateFrom);
    setDraftTo(dateTo);
  };

  const clearDates = () => {
    setDraftFrom("");
    setDraftTo("");
    setDateFrom("");
    setDateTo("");
  };

  const chooseMine = () => {
    setChips(myCategories);
    setMode("mine");
  };

  const removeChip = (category) => {
    const next = chips.filter((c) => c !== category);
    setChips(next);
    if (!next.length) setMode("all");
  };

  const handleLogout = async () => {
    try {
      await authService.logout();
    } catch (err) {
      console.error("Logout error:", err);
    } finally {
      logout();
      navigate("/login");
    }
  };

  const bounds = governments.find((g) => g.government === selected);
  const empty = summary && (summary.topCategories || []).length === 0;
  const showSummary = !loading && summary && !empty;
  const priceLabel = summary?.priceBasis === "payment" ? "payment" : "unit price";

  return (
    <div className="app-container dash" id="dashboard-page-container">
      <nav className="navbar" id="dashboard-navbar">
        <div className="dash-nav-left">
          <Link className="btn btn-secondary" to="/landingPage">← Projects</Link>
          <span className="navbar-brand">HaaS Portal</span>
        </div>
        <div className="navbar-right">
          <span className="navbar-username">
            Welcome, <strong>{user?.username || "User"}</strong>
          </span>
          <button className="btn btn-danger" onClick={handleLogout}>Logout</button>
        </div>
      </nav>

      <main className="main-content">
      <h1 className="page-title">Government purchases</h1>
      <p className="page-subtitle">See what governments buy, what they typically pay, and who they buy from.</p>

      <div className="dash-toolbar">
      <form className="dash-filters" onSubmit={applyDates}>
        <label className="dash-select">
          Government{" "}
          <select value={selected} onChange={(e) => selectGovernment(e.target.value)} disabled={!governments.length}>
            {governments.map((g) => (
              <option key={g.government} value={g.government}>{g.government}</option>
            ))}
          </select>
        </label>
        <label>
          From{" "}
          <input type="date" value={draftFrom} min={bounds?.from} max={bounds?.to} onChange={(e) => setDraftFrom(e.target.value)} />
        </label>
        <label>
          To{" "}
          <input type="date" value={draftTo} min={bounds?.from} max={bounds?.to} onChange={(e) => setDraftTo(e.target.value)} />
        </label>
        <button className="btn btn-primary btn-sm" type="submit" disabled={!selected}>Apply</button>
        <button className="btn btn-outline-secondary btn-sm" type="button" onClick={clearDates} disabled={!draftFrom && !draftTo && !dateFrom && !dateTo}>Clear</button>
      </form>

      <div className="dash-scope">
        <div className="btn-group btn-group-sm" role="group" aria-label="Purchases to show">
          <button
            type="button"
            className={`btn ${mode === "all" ? "btn-primary" : "btn-outline-primary"}`}
            aria-pressed={mode === "all"}
            onClick={() => setMode("all")}
          >
            All purchases
          </button>
          <button
            type="button"
            className={`btn ${mode === "mine" ? "btn-primary" : "btn-outline-primary"}`}
            aria-pressed={mode === "mine"}
            onClick={chooseMine}
            disabled={!myCategories.length}
          >
            Hardware I've used
          </button>
        </div>
        {hardwareReady && !myCategories.length && (
          <span className="dash-note">Check out hardware to filter by the types you use.</span>
        )}
        {mode === "mine" && chips.length > 0 && (
          <ul className="dash-chips" aria-label="Hardware types in the filter">
            {chips.map((c) => (
              <li key={c} className="dash-chip">
                {c}
                <button type="button" onClick={() => removeChip(c)} aria-label={`Remove ${c}`}>×</button>
              </li>
            ))}
          </ul>
        )}
      </div>
      </div>

      {!loading && summary && <p className="dash-range">{rangeText(summary.from, summary.to)}</p>}
      {error && <p className="dash-error">{error}</p>}
      {loading && (
        <div className="dash-message">
          <div className="dash-spinner" />
          <p>Loading {selected}… (the database may take up to a minute to wake up)</p>
        </div>
      )}
      {!loading && empty && <p className="dash-empty">{summary.message || `No purchase data for ${selected}.`}</p>}

      <div className="dash-grid">
        {showSummary && (
          <>
            <ChartCard
              title="Top categories by number of purchases"
              subtitle="How often each kind of item was bought"
              table={
                <table className="table table-sm dash-table">
                  <thead><tr><th>Category</th><th className="num">Purchases</th></tr></thead>
                  <tbody>
                    {summary.topCategories.map((c) => (
                      <tr key={c.category}><td>{c.category}</td><td className="num">{c.purchases.toLocaleString()}</td></tr>
                    ))}
                  </tbody>
                </table>
              }
            >
              <BarChart
                rows={summary.topCategories}
                label={(c) => c.category}
                value={(c) => c.purchases}
                format={(v) => v.toLocaleString()}
                tooltip={(c) => (
                  <>
                    <strong>{c.category}</strong>
                    <br />
                    {c.purchases.toLocaleString()} purchases
                    {typeof c.totalAmount === "number" && <> · {usd(c.totalAmount)}</>}
                  </>
                )}
              />
            </ChartCard>

            <ChartCard
              title="Top vendors"
              subtitle="Total amount spent with each vendor"
              table={
                <table className="table table-sm dash-table">
                  <thead><tr><th>Vendor</th><th className="num">Purchases</th><th className="num">Total</th></tr></thead>
                  <tbody>
                    {(summary.topVendors || []).map((v) => (
                      <tr key={v.vendor}><td>{v.vendor}</td><td className="num">{v.purchases.toLocaleString()}</td><td className="num">{usd(v.totalAmount)}</td></tr>
                    ))}
                  </tbody>
                </table>
              }
            >
              <BarChart
                rows={summary.topVendors || []}
                label={(v) => v.vendor}
                value={(v) => v.totalAmount}
                format={compactUsd}
                tooltip={(v) => (
                  <>
                    <strong>{v.vendor}</strong>
                    <br />
                    {usd(v.totalAmount)} · {v.purchases.toLocaleString()} purchases
                  </>
                )}
              />
            </ChartCard>

            <ChartCard
              wide
              title={`Typical ${priceLabel}`}
              subtitle={`Range of ${priceLabel}s per category. Hover a row for exact values.`}
              table={
                <table className="table table-sm dash-table">
                  <thead><tr><th>Category</th><th className="num">Low (25th)</th><th className="num">Typical (median)</th><th className="num">High (75th)</th><th className="num">Purchases</th></tr></thead>
                  <tbody>
                    {(summary.typicalPrices || []).map((p) => (
                      <tr key={p.category}>
                        <td>{p.category}</td><td className="num">{usd(p.low)}</td><td className="num">{usd(p.median)}</td><td className="num">{usd(p.high)}</td><td className="num">{p.purchases}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              }
            >
              <PriceRangeChart rows={summary.typicalPrices || []} priceLabel={priceLabel} />
            </ChartCard>
          </>
        )}

        <BudgetContextPanel wide onUnauthorized={toLogin} />
      </div>
      </main>
    </div>
  );
}
