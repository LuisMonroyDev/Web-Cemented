import { useState } from "react";
import { QRCodeSVG } from "qrcode.react";
import "./AccountDrawer.css";
import { useStore } from "../storeContext";
import { fetchOrders, cancelOrder } from "../../lib/api";

// Placeholder — swap for the band's real contact address.
const CONTACT_EMAIL = "contact@cemented.band";

// The happy-path fulfilment lifecycle, in order. Canceled is handled apart.
const STEPS = [
  { key: "paid", label: "Paid" },
  { key: "fulfilling", label: "Fulfilling" },
  { key: "shipped", label: "Shipped" },
  { key: "delivered", label: "Delivered" },
];

// Preset cancellation reasons. "Other" forces the customer to type a note.
const CANCEL_REASONS = [
  "Changed my mind",
  "Ordered by mistake",
  "Item won't arrive in time",
  "Found it cheaper elsewhere",
  "Other",
];

export default function AccountDrawer() {
  const { accountOpen, closeAccount, user, signOut } = useStore();
  const [view, setView] = useState("menu"); // "menu" | "orders" | "detail"
  const [orders, setOrders] = useState([]);
  const [selected, setSelected] = useState(null); // the order being viewed
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  // Cancel form state.
  const [showCancelForm, setShowCancelForm] = useState(false);
  const [reason, setReason] = useState("");
  const [notes, setNotes] = useState("");
  const [canceling, setCanceling] = useState(false);
  const [cancelError, setCancelError] = useState("");

  if (!accountOpen || !user) return null;

  const resetCancelForm = () => {
    setShowCancelForm(false);
    setReason("");
    setNotes("");
    setCancelError("");
  };

  const close = () => {
    setView("menu");
    setSelected(null);
    resetCancelForm();
    closeAccount();
  };

  // Orders load on demand (event handler — no setState-in-effect).
  const showOrders = async () => {
    setView("orders");
    setLoading(true);
    setError("");
    try {
      setOrders(await fetchOrders());
    } catch {
      setError("Couldn't load your orders.");
    } finally {
      setLoading(false);
    }
  };

  const openDetail = (order) => {
    setSelected(order);
    resetCancelForm();
    setView("detail");
  };

  // Back steps one level: detail → orders → menu.
  const goBack = () => {
    if (view === "detail") {
      setSelected(null);
      resetCancelForm();
      setView("orders");
    } else {
      setView("menu");
    }
  };

  const submitCancel = async () => {
    if (!selected) return;
    if (!reason) {
      setCancelError("Please choose a reason.");
      return;
    }
    if (reason === "Other" && !notes.trim()) {
      setCancelError("Please add a note so we know why.");
      return;
    }
    const fullReason = notes.trim() ? `${reason}: ${notes.trim()}` : reason;
    setCanceling(true);
    setCancelError("");
    try {
      const updated = await cancelOrder(selected.id, fullReason);
      setSelected(updated);
      // Keep the list in sync so it reflects the new status when we go back.
      setOrders((prev) => prev.map((o) => (o.id === updated.id ? updated : o)));
      resetCancelForm();
    } catch (err) {
      setCancelError(err.message || "Couldn't cancel this order.");
    } finally {
      setCanceling(false);
    }
  };

  const currentStep = selected
    ? STEPS.findIndex((s) => s.key === selected.status)
    : -1;

  return (
    <div className="acct" role="dialog" aria-modal="true">
      <div className="acct__scrim" onClick={close} />
      <aside className="acct__panel">
        <header className="acct__head">
          {view !== "menu" ? (
            <button className="acct__back" type="button" onClick={goBack}>
              ← Back
            </button>
          ) : (
            <span className="acct__hello">Hi, {user.username}</span>
          )}
          <button className="acct__close" type="button" onClick={close} aria-label="Close">
            ×
          </button>
        </header>

        {view === "menu" && (
          <nav className="acct__menu">
            <button className="acct__item" type="button" onClick={showOrders}>
              Orders
            </button>
            <a className="acct__item" href={`mailto:${CONTACT_EMAIL}`}>
              Contact
            </a>
            <button className="acct__item" type="button" onClick={signOut}>
              Log out
            </button>
          </nav>
        )}

        {view === "orders" && (
          <div className="acct__orders">
            {loading && <p className="acct__muted">Loading…</p>}
            {error && <p className="acct__error">{error}</p>}
            {!loading && !error && orders.length === 0 && (
              <p className="acct__muted">No orders yet.</p>
            )}
            {!loading &&
              !error &&
              orders.map((order) => (
                <button
                  className="order order--row"
                  type="button"
                  key={order.id}
                  onClick={() => openDetail(order)}
                >
                  <div className="order__top">
                    <span className="order__id">Order #{order.id}</span>
                    <span className="order__date">
                      {new Date(order.created_at).toLocaleDateString()}
                    </span>
                  </div>
                  <div className="order__rowmeta">
                    <span className={`order__status order__status--${order.status}`}>
                      {order.status_display}
                    </span>
                    <span className="order__rowtotal">${order.total}</span>
                  </div>
                </button>
              ))}
          </div>
        )}

        {view === "detail" && selected && (
          <div className="acct__orders">
            {/* Lifecycle progress — or a canceled notice. */}
            {selected.status === "canceled" ? (
              <div className="order__canceled">
                <span className="order__status order__status--canceled">Canceled</span>
                <p className="acct__muted">This order was canceled and refunded.</p>
              </div>
            ) : (
              <ol className="stepper">
                {STEPS.map((step, i) => (
                  <li
                    key={step.key}
                    className={
                      "stepper__step" +
                      (i < currentStep ? " stepper__step--done" : "") +
                      (i === currentStep ? " stepper__step--active" : "")
                    }
                  >
                    <span className="stepper__dot" />
                    <span className="stepper__label">{step.label}</span>
                  </li>
                ))}
              </ol>
            )}

            <article className="order">
              <div className="order__top">
                <span className="order__id">Order #{selected.id}</span>
                <span className="order__date">
                  {new Date(selected.created_at).toLocaleDateString()}
                </span>
              </div>
              <ul className="order__items">
                {selected.items.map((item) => (
                  <li key={item.id}>
                    <span>
                      {item.quantity}× {item.name}
                      {item.size_label ? ` (${item.size_label})` : ""}
                    </span>
                    <span>${item.line_total}</span>
                  </li>
                ))}
              </ul>
              {Number(selected.shipping_cost) > 0 && (
                <div className="order__subline">
                  <span>Shipping</span>
                  <span>${selected.shipping_cost}</span>
                </div>
              )}
              <div className="order__total">
                <span>Total</span>
                <span>${selected.total}</span>
              </div>
            </article>

            {selected.shipping && (
              <div className="order__block">
                <h4 className="order__blocktitle">Shipping to</h4>
                <address className="order__address">
                  {selected.shipping.lines.map((line, i) => (
                    <span key={i}>{line}</span>
                  ))}
                </address>
              </div>
            )}

            {selected.tracking_number && (
              <div className="order__block">
                <h4 className="order__blocktitle">Tracking number</h4>
                <p className="order__tracking">{selected.tracking_number}</p>
                {selected.tracking_url && (
                  <div className="order__track">
                    <a
                      className="order__tracklink"
                      href={selected.tracking_url}
                      target="_blank"
                      rel="noopener noreferrer"
                    >
                      Track with USPS
                    </a>
                    <div className="order__qr">
                      <QRCodeSVG
                        value={selected.tracking_url}
                        size={132}
                        bgColor="#ffffff"
                        fgColor="#0a0a0a"
                        level="M"
                        marginSize={2}
                      />
                      <span className="order__qrhint">Scan to track on your phone</span>
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Cancel + reason capture. */}
            {selected.can_cancel && !showCancelForm && (
              <button
                className="order__cancel"
                type="button"
                onClick={() => setShowCancelForm(true)}
              >
                Cancel order
              </button>
            )}

            {selected.can_cancel && showCancelForm && (
              <div className="order__cancelform">
                <label className="order__field">
                  <span className="order__blocktitle">Reason for canceling</span>
                  <select
                    className="order__select"
                    value={reason}
                    onChange={(e) => setReason(e.target.value)}
                  >
                    <option value="">Select a reason…</option>
                    {CANCEL_REASONS.map((r) => (
                      <option key={r} value={r}>
                        {r}
                      </option>
                    ))}
                  </select>
                </label>
                <textarea
                  className="order__notes"
                  rows={2}
                  placeholder={
                    reason === "Other" ? "Tell us more (required)" : "Add a note (optional)"
                  }
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                />
                {cancelError && <p className="acct__error">{cancelError}</p>}
                <div className="order__cancelactions">
                  <button
                    className="order__cancel"
                    type="button"
                    onClick={submitCancel}
                    disabled={canceling}
                  >
                    {canceling ? "Canceling…" : "Confirm cancellation"}
                  </button>
                  <button
                    className="order__keep"
                    type="button"
                    onClick={resetCancelForm}
                    disabled={canceling}
                  >
                    Keep order
                  </button>
                </div>
              </div>
            )}
          </div>
        )}
      </aside>
    </div>
  );
}
