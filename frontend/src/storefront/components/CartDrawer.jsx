import { useState } from "react";
import "./CartDrawer.css";
import { useStore } from "../storeContext";

export default function CartDrawer() {
  const { cartOpen, closeCart, cart, user, updateItem, removeItem, startCheckout, openAuth } =
    useStore();
  const [error, setError] = useState("");

  if (!cartOpen) return null;

  const onCheckout = async () => {
    setError("");
    try {
      await startCheckout();
    } catch (err) {
      setError(err.message || "Could not start checkout.");
    }
  };

  const isEmpty = cart.items.length === 0;

  return (
    <div className="cart" role="dialog" aria-modal="true">
      <div className="cart__scrim" onClick={closeCart} />
      <aside className="cart__panel">
        <header className="cart__head">
          <h2>Cart</h2>
          <button className="cart__close" type="button" onClick={closeCart} aria-label="Close">
            ×
          </button>
        </header>

        {!user ? (
          <div className="cart__empty">
            <p>Sign in to start a cart.</p>
            <button
              className="cart__cta"
              type="button"
              onClick={() => {
                closeCart();
                openAuth();
              }}
            >
              Sign in
            </button>
          </div>
        ) : isEmpty ? (
          <div className="cart__empty">
            <p>Your cart is empty.</p>
          </div>
        ) : (
          <>
            <ul className="cart__items">
              {cart.items.map((item) => (
                <li className="cart__item" key={item.id}>
                  <div
                    className="cart__thumb"
                    style={
                      item.product.image
                        ? { backgroundImage: `url(${item.product.image})` }
                        : undefined
                    }
                  />
                  <div className="cart__info">
                    <p className="cart__name">{item.product.name}</p>
                    <p className="cart__price">${item.product.price}</p>
                    <div className="cart__qty">
                      <button type="button" onClick={() => updateItem(item.id, item.quantity - 1)} aria-label="Decrease">
                        −
                      </button>
                      <span>{item.quantity}</span>
                      <button type="button" onClick={() => updateItem(item.id, item.quantity + 1)} aria-label="Increase">
                        +
                      </button>
                      <button className="cart__remove" type="button" onClick={() => removeItem(item.id)}>
                        Remove
                      </button>
                    </div>
                  </div>
                  <p className="cart__line">${item.line_total}</p>
                </li>
              ))}
            </ul>

            <footer className="cart__foot">
              {error && <p className="cart__error">{error}</p>}
              <div className="cart__total">
                <span>Total</span>
                <span>${cart.total}</span>
              </div>
              <button className="cart__checkout" type="button" onClick={onCheckout}>
                Checkout
              </button>
            </footer>
          </>
        )}
      </aside>
    </div>
  );
}
