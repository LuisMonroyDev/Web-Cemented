import { useState } from "react";
import "./AccountDrawer.css";
import { useStore } from "../storeContext";
import { fetchOrders } from "../../lib/api";

// Placeholder — swap for the band's real contact address.
const CONTACT_EMAIL = "contact@cemented.band";

export default function AccountDrawer() {
  const { accountOpen, closeAccount, user, signOut } = useStore();
  const [view, setView] = useState("menu"); // "menu" | "orders"
  const [orders, setOrders] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  if (!accountOpen || !user) return null;

  const close = () => {
    setView("menu");
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

  return (
    <div className="acct" role="dialog" aria-modal="true">
      <div className="acct__scrim" onClick={close} />
      <aside className="acct__panel">
        <header className="acct__head">
          {view === "orders" ? (
            <button className="acct__back" type="button" onClick={() => setView("menu")}>
              ← Back
            </button>
          ) : (
            <span className="acct__hello">Hi, {user.username}</span>
          )}
          <button className="acct__close" type="button" onClick={close} aria-label="Close">
            ×
          </button>
        </header>

        {view === "menu" ? (
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
        ) : (
          <div className="acct__orders">
            {loading && <p className="acct__muted">Loading…</p>}
            {error && <p className="acct__error">{error}</p>}
            {!loading && !error && orders.length === 0 && (
              <p className="acct__muted">No orders yet.</p>
            )}
            {!loading &&
              !error &&
              orders.map((order) => (
                <article className="order" key={order.id}>
                  <div className="order__top">
                    <span className="order__id">Order #{order.id}</span>
                    <span className="order__date">
                      {new Date(order.created_at).toLocaleDateString()}
                    </span>
                  </div>
                  <ul className="order__items">
                    {order.items.map((item) => (
                      <li key={item.id}>
                        <span>
                          {item.quantity}× {item.name}
                        </span>
                        <span>${item.line_total}</span>
                      </li>
                    ))}
                  </ul>
                  <div className="order__total">
                    <span>Total</span>
                    <span>${order.total}</span>
                  </div>
                </article>
              ))}
          </div>
        )}
      </aside>
    </div>
  );
}
