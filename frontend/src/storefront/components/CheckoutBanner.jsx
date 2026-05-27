import "./CheckoutBanner.css";
import { useStore } from "../storeContext";

export default function CheckoutBanner() {
  const { checkoutStatus, dismissCheckout } = useStore();
  if (!checkoutStatus) return null;

  const success = checkoutStatus === "success";
  return (
    <div
      className={`cobanner ${success ? "cobanner--success" : "cobanner--cancel"}`}
      role="status"
    >
      <span className="cobanner__msg">
        {success
          ? "Order confirmed — thanks for the support."
          : "Checkout canceled — your cart is still saved."}
      </span>
      <button
        className="cobanner__close"
        type="button"
        onClick={dismissCheckout}
        aria-label="Dismiss"
      >
        ×
      </button>
    </div>
  );
}
