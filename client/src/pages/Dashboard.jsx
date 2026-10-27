// Government purchase dashboard (requirements 11.2) and the Projects team
// budget context panel (11.3).
// MINIMAL VERSION FOR THE TUESDAY VERTICAL SLICE -- Aneri owns the dashboard
// and Vedanti owns the budget panel; please review and restyle freely.
// Every call goes through the gateway on the same origin (11.1).
import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import "./Dashboard.css";

const GATEWAY = import.meta.env.VITE_GATEWAY_BASE_URL || "";
const NA = "not available";

async function callGateway(path, options = {}) {
  try {
    const response = await fetch(GATEWAY + path, options);
    const body = await response.json();
    return { body, sample: response.headers.get("X-Sample-Data") === "true" };
  } catch {
    return { body: { success: false, message: "Could not reach the gateway. Try again in a minute." } };
  }
}

const usd = (v) =>
  v === NA || v === null || v === undefined
    ? "Not available"
    : v.toLocaleString("en-US", { style: "currency", currency: "USD" });

function CategoryBars({ rows }) {
  const max = Math.max(...rows.map((r) => r.purchases), 1);
  return (
    <ol className="dash-bars">
      {rows.map((r) => (
        <li key={r.category}>
          <span className="dash-bar-label" title={r.category}>{r.category}</span>
          <span className="dash-bar-track">
            <span className="dash-bar" style={{ width: `${(100 * r.purchases) / max}%` }} />
          </span>
          <span className="dash-bar-value">{r.purchases.toLocaleString()}</span>
        </li>
      ))}
    </ol>
  );
}

function BudgetContextPanel() {
  const [item, setItem] = useState("Laptop computer");
  const [quantity, setQuantity] = useState(10);
  const [result, setResult] = useState(null);

  const submit = async (e) => {
    e.preventDefault();
    const { body, sample } = await callGateway("/api/projects/get_budget_context", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ itemDescription: item, quantity: Number(quantity) }),
    });
    setResult({ ...body, sample });
  };

  const governments = result?.unitPrice ? Object.keys(result.unitPrice) : [];
  const cell = (v) => (v && typeof v === "object" ? usd(v.typical) : usd(v));

  return (
    <section className="dash-card">
      <h2>Budget context</h2>
      <form className="dash-budget-form" onSubmit={submit}>
        <input value={item} onChange={(e) => setItem(e.target.value)} placeholder="Item description" aria-label="Item description" />
        <input type="number" min="1" value={quantity} onChange={(e) => setQuantity(e.target.value)} aria-label="Quantity" />
        <button className="btn btn-primary" type="submit">Get context</button>
      </form>
      {result && !result.success && <p className="dash-error">{result.message}</p>}
      {result?.success && (
        <>
          {result.sample && <p className="dash-sample">Sample data from the gateway. The Projects team service is not connected yet.</p>}
          <p>
            <strong>{result.category}</strong>. Estimated cost: {usd(result.estimatedCost?.low)} to{" "}
            {usd(result.estimatedCost?.high)} (typical {usd(result.estimatedCost?.typical)})
          </p>
          <table className="table table-sm">
            <thead><tr><th></th>{governments.map((g) => <th key={g}>{g}</th>)}</tr></thead>
            <tbody>
              <tr><th>Unit price</th>{governments.map((g) => <td key={g}>{cell(result.unitPrice[g])}</td>)}</tr>
              <tr><th>Department spend</th>{governments.map((g) => <td key={g}>{cell(result.departmentSpend?.[g])}</td>)}</tr>
            </tbody>
          </table>
        </>
      )}
      <p className="dash-note">Price context from public purchase records. Not a recommendation.</p>
    </section>
  );
}

export default function Dashboard() {
  const [governments, setGovernments] = useState([]);
  const [selected, setSelected] = useState("");
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    callGateway("/api/data/governments").then(({ body }) => {
      if (!body.success) return setError(body.message);
      setGovernments(body.governments);
      if (body.governments.length) setSelected(body.governments[0].government);
    });
  }, []);

  useEffect(() => {
    if (!selected) return;
    setLoading(true);
    setError("");
    callGateway(`/api/data/governments/${encodeURIComponent(selected)}/summary`).then(({ body }) => {
      setLoading(false);
      if (!body.success) {
        setSummary(null);
        return setError(body.message);
      }
      setSummary(body);
    });
  }, [selected]);

  const empty = summary && summary.topCategories.length === 0;
  const priceLabel = summary?.priceBasis === "payment" ? "payment" : "unit price";

  return (
    <div className="dash">
      <header className="dash-header">
        <h1>Government purchases</h1>
        <Link to="/login">Log in</Link>
      </header>

      <label className="dash-select">
        Government{" "}
        <select value={selected} onChange={(e) => setSelected(e.target.value)} disabled={!governments.length}>
          {governments.map((g) => (
            <option key={g.government} value={g.government}>{g.government}</option>
          ))}
        </select>
      </label>

      {error && <p className="dash-error">{error}</p>}
      {loading && <p>Loading {selected}… (the database may take up to a minute to wake up)</p>}
      {!loading && empty && <p className="dash-empty">{summary.message || `No purchase data for ${selected}.`}</p>}

      {!loading && summary && !empty && (
        <div className="dash-grid">
          <section className="dash-card dash-wide">
            <h2>Top categories by number of purchases</h2>
            <CategoryBars rows={summary.topCategories} />
          </section>

          <section className="dash-card dash-wide">
            <h2>Typical {priceLabel}</h2>
            <table className="table table-sm">
              <thead><tr><th>Category</th><th>Low (25th)</th><th>Typical (median)</th><th>High (75th)</th><th>Purchases</th></tr></thead>
              <tbody>
                {summary.typicalPrices.map((p) => (
                  <tr key={p.category}>
                    <td>{p.category}</td><td>{usd(p.low)}</td><td>{usd(p.median)}</td><td>{usd(p.high)}</td><td>{p.purchases}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>

          <section className="dash-card">
            <h2>Top vendors</h2>
            <ol>
              {summary.topVendors.map((v) => (
                <li key={v.vendor}>{v.vendor} <small>({v.purchases.toLocaleString()} purchases, {usd(v.totalAmount)})</small></li>
              ))}
            </ol>
          </section>

          <BudgetContextPanel />
        </div>
      )}
      {(!summary || empty) && !loading && <BudgetContextPanel />}
    </div>
  );
}
