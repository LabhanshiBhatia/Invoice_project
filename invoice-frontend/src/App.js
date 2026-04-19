import { useState, useEffect, useCallback } from "react";
import "./App.css";

const API = "http://127.0.0.1:5000/api";

const fmt = (n) =>
  new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 2 }).format(n);

const fmtDate = (iso) => {
  const d = new Date(iso);
  return d.toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" });
};

const STATUS_META = {
  paid:    { label: "Paid",    color: "green"  },
  unpaid:  { label: "Unpaid",  color: "amber"  },
  overdue: { label: "Overdue", color: "red"    },
};

// ─── COMPONENTS ───────────────────────────────────────────────────────────────

function StatCard({ label, value, sub, accent }) {
  return (
    <div className={`stat-card stat-card--${accent}`}>
      <span className="stat-label">{label}</span>
      <span className="stat-value">{value}</span>
      {sub && <span className="stat-sub">{sub}</span>}
    </div>
  );
}

function StatusBadge({ status }) {
  const m = STATUS_META[status] || { label: status, color: "gray" };
  return <span className={`badge badge--${m.color}`}>{m.label}</span>;
}

function Toast({ msg, type, onClose }) {
  useEffect(() => {
    const t = setTimeout(onClose, 3500);
    return () => clearTimeout(t);
  }, [onClose]);
  return (
    <div className={`toast toast--${type}`}>
      <span>{msg}</span>
      <button className="toast-close" onClick={onClose}>✕</button>
    </div>
  );
}

function InvoiceRow({ inv, onDelete, onStatusChange, onDownload }) {
  const [menuOpen, setMenuOpen] = useState(false);

  return (
    <tr className="inv-row">
      <td className="td-id">#{String(inv.id).padStart(4, "0")}</td>
      <td>
        <div className="customer-cell">
          <div className="avatar">{inv.customer[0].toUpperCase()}</div>
          <span>{inv.customer}</span>
        </div>
      </td>
      <td className="td-product">{inv.product}</td>
      <td className="td-num">{inv.qty}</td>
      <td className="td-num">{fmt(inv.price)}</td>
      <td className="td-num">{fmt(inv.subtotal)}</td>
      <td className="td-num td-tax">{fmt(inv.tax_amt)}</td>
      <td className="td-num td-total">{fmt(inv.grand_total)}</td>
      <td>
        <div className="status-wrap" style={{ position: "relative" }}>
          <button
            className={`badge badge--${STATUS_META[inv.status]?.color || "gray"} badge-btn`}
            onClick={() => setMenuOpen(p => !p)}
            title="Change status"
          >
            {STATUS_META[inv.status]?.label || inv.status}
            <span className="badge-caret">▾</span>
          </button>
          {menuOpen && (
            <div className="status-menu">
              {Object.entries(STATUS_META).map(([key, val]) => (
                <button
                  key={key}
                  className={`status-option ${inv.status === key ? "active" : ""}`}
                  onClick={() => { onStatusChange(inv.id, key); setMenuOpen(false); }}
                >
                  <span className={`dot dot--${val.color}`} />
                  {val.label}
                </button>
              ))}
            </div>
          )}
        </div>
      </td>
      <td className="td-date">{fmtDate(inv.created_at)}</td>
      <td className="td-actions">
        <button className="action-btn action-btn--dl" onClick={() => onDownload(inv.id)} title="Download PDF">
          <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
            <path d="M8 2v8M5 7l3 3 3-3M3 12h10" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
        </button>
        <button className="action-btn action-btn--del" onClick={() => onDelete(inv.id)} title="Delete">
          <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
            <path d="M3 4h10M6 4V3h4v1M5 4l.5 9h5l.5-9" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
        </button>
      </td>
    </tr>
  );
}

function CreateModal({ onClose, onCreated }) {
  const empty = { name: "", product: "", price: "", qty: "", tax: "" };
  const [form, setForm] = useState(empty);
  const [loading, setLoading] = useState(false);
  const [errors, setErrors] = useState([]);

  const price = parseFloat(form.price) || 0;
  const qty   = parseInt(form.qty)    || 0;
  const tax   = parseFloat(form.tax)  || 0;
  const sub   = price * qty;
  const taxA  = sub * tax / 100;
  const total = sub + taxA;

  const handle = (e) => setForm({ ...form, [e.target.name]: e.target.value });

  const submit = async () => {
    setLoading(true);
    setErrors([]);
    try {
      const res = await fetch(`${API}/invoices`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(form),
      });
      const body = await res.json();
      if (!res.ok) {
        setErrors(body.errors || [body.error || "Unknown error"]);
      } else {
        onCreated(body);
        onClose();
      }
    } catch {
      setErrors(["Network error — is the server running?"]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="modal-backdrop" onClick={(e) => e.target === e.currentTarget && onClose()}>
      <div className="modal">
        <div className="modal-header">
          <h2>New Invoice</h2>
          <button className="modal-close" onClick={onClose}>✕</button>
        </div>

        {errors.length > 0 && (
          <div className="form-errors">
            {errors.map((e, i) => <p key={i}>{e}</p>)}
          </div>
        )}

        <div className="form-grid">
          <label className="form-label">
            Customer Name
            <input name="name" className="form-input" value={form.name} onChange={handle} placeholder="e.g. Acme Corp" />
          </label>
          <label className="form-label">
            Product / Service
            <input name="product" className="form-input" value={form.product} onChange={handle} placeholder="e.g. Web Design" />
          </label>
          <label className="form-label">
            Unit Price (₹)
            <input name="price" className="form-input" type="number" min="0" value={form.price} onChange={handle} placeholder="0.00" />
          </label>
          <label className="form-label">
            Quantity
            <input name="qty" className="form-input" type="number" min="1" value={form.qty} onChange={handle} placeholder="1" />
          </label>
          <label className="form-label" style={{ gridColumn: "1 / -1" }}>
            Tax Rate (%)
            <input name="tax" className="form-input" type="number" min="0" max="100" value={form.tax} onChange={handle} placeholder="18" />
          </label>
        </div>

        {(sub > 0) && (
          <div className="preview-block">
            <div className="preview-row"><span>Subtotal</span><span>{fmt(sub)}</span></div>
            <div className="preview-row"><span>Tax ({tax}%)</span><span>{fmt(taxA)}</span></div>
            <div className="preview-row preview-row--total"><span>Grand Total</span><span>{fmt(total)}</span></div>
          </div>
        )}

        <div className="modal-footer">
          <button className="btn btn--ghost" onClick={onClose}>Cancel</button>
          <button className="btn btn--primary" onClick={submit} disabled={loading}>
            {loading ? "Creating…" : "Create Invoice"}
          </button>
        </div>
      </div>
    </div>
  );
}

// ─── APP ──────────────────────────────────────────────────────────────────────

export default function App() {
  const [invoices, setInvoices]   = useState([]);
  const [stats, setStats]         = useState(null);
  const [loading, setLoading]     = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [toast, setToast]         = useState(null);
  const [search, setSearch]       = useState("");
  const [filter, setFilter]       = useState("all");

  const notify = (msg, type = "success") => setToast({ msg, type });

  const fetchAll = useCallback(async () => {
    setLoading(true);
    try {
      const [invRes, statsRes] = await Promise.all([
        fetch(`${API}/invoices`),
        fetch(`${API}/stats`),
      ]);
      setInvoices(await invRes.json());
      setStats(await statsRes.json());
    } catch {
      notify("Failed to load data", "error");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchAll(); }, [fetchAll]);

  const handleDelete = async (id) => {
    if (!window.confirm(`Delete invoice #${String(id).padStart(4, "0")}?`)) return;
    const res = await fetch(`${API}/invoices/${id}`, { method: "DELETE" });
    if (res.ok) {
      setInvoices(p => p.filter(i => i.id !== id));
      notify("Invoice deleted");
      fetchAll();
    } else {
      notify("Delete failed", "error");
    }
  };

  const handleStatusChange = async (id, status) => {
    const res = await fetch(`${API}/invoices/${id}/status`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ status }),
    });
    if (res.ok) {
      setInvoices(p => p.map(i => i.id === id ? { ...i, status } : i));
      notify(`Marked as ${status}`);
      fetchAll();
    } else {
      notify("Status update failed", "error");
    }
  };

  const handleDownload = (id) => {
    window.open(`${API}/invoices/${id}/pdf`, "_blank");
  };

  const handleCreated = (inv) => {
    setInvoices(p => [inv, ...p]);
    notify(`Invoice #${String(inv.id).padStart(4, "0")} created`);
    fetchAll();
  };

  const visible = invoices.filter(i => {
    const matchFilter = filter === "all" || i.status === filter;
    const q = search.toLowerCase();
    const matchSearch = !q || i.customer.toLowerCase().includes(q) || i.product.toLowerCase().includes(q);
    return matchFilter && matchSearch;
  });

  return (
    <div className="app">
      {/* ─ Sidebar ─ */}
      <aside className="sidebar">
        <div className="sidebar-logo">
          <svg width="22" height="22" viewBox="0 0 22 22" fill="none">
            <rect width="22" height="22" rx="6" fill="currentColor"/>
            <path d="M6 11h10M11 6v10" stroke="white" strokeWidth="2" strokeLinecap="round"/>
          </svg>
          <span>Invoicr</span>
        </div>

        <nav className="sidebar-nav">
          {[
            { key: "all",     label: "All Invoices", count: stats?.total },
            { key: "paid",    label: "Paid",          count: stats?.paid_count },
            { key: "unpaid",  label: "Unpaid",        count: stats?.unpaid_count },
            { key: "overdue", label: "Overdue",       count: stats?.overdue_count },
          ].map(item => (
            <button
              key={item.key}
              className={`nav-item ${filter === item.key ? "nav-item--active" : ""}`}
              onClick={() => setFilter(item.key)}
            >
              <span>{item.label}</span>
              {item.count != null && <span className="nav-count">{item.count}</span>}
            </button>
          ))}
        </nav>

        <div className="sidebar-footer">
          <p>Invoice System v2</p>
        </div>
      </aside>

      {/* ─ Main ─ */}
      <main className="main">
        {/* Header */}
        <header className="page-header">
          <div>
            <h1 className="page-title">
              {filter === "all" ? "All Invoices" : STATUS_META[filter]?.label + " Invoices"}
            </h1>
            <p className="page-sub">{visible.length} invoice{visible.length !== 1 ? "s" : ""}</p>
          </div>
          <div className="header-actions">
            <div className="search-wrap">
              <svg className="search-icon" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
                <circle cx="7" cy="7" r="4.5"/><path d="M10.5 10.5l3 3" strokeLinecap="round"/>
              </svg>
              <input
                className="search-input"
                placeholder="Search customer or product…"
                value={search}
                onChange={e => setSearch(e.target.value)}
              />
            </div>
            <button className="btn btn--primary" onClick={() => setShowModal(true)}>
              <span>+ New Invoice</span>
            </button>
          </div>
        </header>

        {/* Stats */}
        {stats && (
          <div className="stats-row">
            <StatCard label="Total Revenue" value={fmt(stats.revenue)} sub={`${stats.total} invoices`} accent="default" />
            <StatCard label="Collected"     value={fmt(stats.paid)}    sub={`${stats.paid_count} paid`}    accent="green"   />
            <StatCard label="Pending"       value={fmt(stats.unpaid)}  sub={`${stats.unpaid_count} unpaid`}  accent="amber"   />
            <StatCard label="Overdue"       value={fmt(stats.overdue)} sub={`${stats.overdue_count} overdue`} accent="red"     />
          </div>
        )}

        {/* Table */}
        <div className="table-wrap">
          {loading ? (
            <div className="empty-state">
              <div className="spinner" />
              <p>Loading invoices…</p>
            </div>
          ) : visible.length === 0 ? (
            <div className="empty-state">
              <svg width="40" height="40" viewBox="0 0 40 40" fill="none">
                <rect x="8" y="6" width="24" height="30" rx="3" stroke="currentColor" strokeWidth="1.5"/>
                <path d="M14 14h12M14 20h8M14 26h5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
              </svg>
              <p>{search || filter !== "all" ? "No matching invoices" : "No invoices yet"}</p>
              {!search && filter === "all" && (
                <button className="btn btn--primary" onClick={() => setShowModal(true)}>Create your first invoice</button>
              )}
            </div>
          ) : (
            <table className="inv-table">
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Customer</th>
                  <th>Product</th>
                  <th className="td-num">Qty</th>
                  <th className="td-num">Price</th>
                  <th className="td-num">Subtotal</th>
                  <th className="td-num td-tax">Tax</th>
                  <th className="td-num td-total">Total</th>
                  <th>Status</th>
                  <th>Date</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {visible.map(inv => (
                  <InvoiceRow
                    key={inv.id}
                    inv={inv}
                    onDelete={handleDelete}
                    onStatusChange={handleStatusChange}
                    onDownload={handleDownload}
                  />
                ))}
              </tbody>
            </table>
          )}
        </div>
      </main>

      {showModal && (
        <CreateModal onClose={() => setShowModal(false)} onCreated={handleCreated} />
      )}

      {toast && (
        <Toast msg={toast.msg} type={toast.type} onClose={() => setToast(null)} />
      )}
    </div>
  );
}
