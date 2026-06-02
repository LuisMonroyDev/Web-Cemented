import { useCallback, useEffect, useState } from "react";

import * as api from "../lib/api";
import { StoreContext } from "./storeContext";

const EMPTY_CART = { items: [], total: "0.00" };

// Read the ?checkout result from the URL. Used as useState's lazy initializer
// so the banner is decided at render time, not inside an effect (which also
// keeps it immune to StrictMode's dev double-invoke).
function readCheckoutParam() {
  if (typeof window === "undefined") return null;
  const value = new URLSearchParams(window.location.search).get("checkout");
  return value === "success" || value === "cancel" ? value : null;
}

export function StoreProvider({ children }) {
  const [user, setUser] = useState(null);
  const [cart, setCart] = useState(EMPTY_CART);
  const [ready, setReady] = useState(false);
  const [authOpen, setAuthOpen] = useState(false);
  const [cartOpen, setCartOpen] = useState(false);
  const [accountOpen, setAccountOpen] = useState(false);
  const [checkoutStatus, setCheckoutStatus] = useState(readCheckoutParam); // from the URL

  const loadCart = useCallback(async () => {
    try {
      setCart(await api.fetchCart());
    } catch {
      setCart(EMPTY_CART);
    }
  }, []);

  // Hydrate auth + cart on load (401 just means "not logged in").
  useEffect(() => {
    let active = true;

    // checkoutStatus is initialised from the URL at render time; here we only
    // strip the ?checkout param so a refresh won't re-show the banner.
    const params = new URLSearchParams(window.location.search);
    if (params.has("checkout")) {
      params.delete("checkout");
      const query = params.toString();
      window.history.replaceState(
        {},
        "",
        window.location.pathname + (query ? `?${query}` : "") + window.location.hash,
      );
    }

    (async () => {
      try {
        const me = await api.fetchMe();
        if (!active) return;
        setUser(me);
        await loadCart(); // after a paid order the webhook has emptied this
      } catch {
        if (active) setUser(null);
      } finally {
        if (active) setReady(true);
      }
    })();
    return () => {
      active = false;
    };
  }, [loadCart]);

  const signIn = useCallback(
    async (username, password) => {
      setUser(await api.login(username, password));
      await loadCart();
      setAuthOpen(false);
    },
    [loadCart],
  );

  const signUp = useCallback(
    async (payload) => {
      setUser(await api.register(payload));
      await loadCart();
      setAuthOpen(false);
    },
    [loadCart],
  );

  const signOut = useCallback(async () => {
    try {
      await api.logout();
    } catch {
      // logging out locally is enough even if the request fails
    }
    setUser(null);
    setCart(EMPTY_CART);
    setCartOpen(false);
    setAccountOpen(false);
  }, []);

  const addToCart = useCallback(
    async (productId, quantity = 1, sizeId = null) => {
      if (!user) {
        setAuthOpen(true); // must be signed in to have a cart
        return;
      }
      try {
        setCart(await api.addToCart(productId, quantity, sizeId));
        setCartOpen(true);
      } catch {
        // e.g. a placeholder product that isn't in the DB — ignore
      }
    },
    [user],
  );

  const updateItem = useCallback(async (itemId, quantity) => {
    try {
      setCart(await api.updateCartItem(itemId, quantity));
    } catch {
      // ignore transient errors
    }
  }, []);

  const removeItem = useCallback(async (itemId) => {
    try {
      setCart(await api.removeCartItem(itemId));
    } catch {
      // ignore transient errors
    }
  }, []);

  // Change a line's size. Throws on failure (e.g. the new size is sold out) so
  // the cart UI can show why the swap didn't take.
  const changeItemSize = useCallback(async (itemId, sizeId) => {
    setCart(await api.changeCartItemSize(itemId, sizeId));
  }, []);

  // Throws on failure (e.g. Stripe not configured) so the cart UI can show it.
  const startCheckout = useCallback(async () => {
    const data = await api.checkout();
    if (data?.checkout_url) {
      window.location.href = data.checkout_url;
    }
  }, []);

  const dismissCheckout = useCallback(() => setCheckoutStatus(null), []);

  const count = cart.items.reduce((sum, item) => sum + item.quantity, 0);

  const value = {
    user,
    cart,
    count,
    ready,
    authOpen,
    cartOpen,
    checkoutStatus,
    dismissCheckout,
    openAuth: () => setAuthOpen(true),
    closeAuth: () => setAuthOpen(false),
    openCart: () => setCartOpen(true),
    closeCart: () => setCartOpen(false),
    accountOpen,
    openAccount: () => setAccountOpen(true),
    closeAccount: () => setAccountOpen(false),
    signIn,
    signUp,
    signOut,
    addToCart,
    updateItem,
    removeItem,
    changeItemSize,
    startCheckout,
  };

  return <StoreContext.Provider value={value}>{children}</StoreContext.Provider>;
}
