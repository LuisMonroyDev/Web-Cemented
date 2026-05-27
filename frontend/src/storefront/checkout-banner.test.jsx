import { StrictMode } from "react";
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

// The provider hydrates auth/cart on mount; stub the API so tests stay offline.
vi.mock("../lib/api", () => ({
  fetchMe: vi.fn().mockRejectedValue(new Error("not authenticated")),
  fetchCart: vi.fn().mockResolvedValue({ items: [], total: "0.00" }),
  login: vi.fn(),
  register: vi.fn(),
  logout: vi.fn(),
  addToCart: vi.fn(),
  updateCartItem: vi.fn(),
  removeCartItem: vi.fn(),
  checkout: vi.fn(),
  fetchProducts: vi.fn(),
  fetchGallery: vi.fn(),
  fetchSiteSettings: vi.fn(),
  fetchHealth: vi.fn(),
  ADMIN_URL: "http://localhost:8000/admin/",
}));

import { StoreProvider } from "./StoreProvider";
import CheckoutBanner from "./components/CheckoutBanner";

function renderStore() {
  return render(
    <StrictMode>
      <StoreProvider>
        <CheckoutBanner />
      </StoreProvider>
    </StrictMode>,
  );
}

afterEach(() => {
  cleanup();
  window.history.replaceState({}, "", "/");
});

describe("checkout confirmation banner", () => {
  // Regression: returning from Stripe must show the banner even though the
  // effect strips the URL param (and StrictMode double-invokes effects in dev).
  it("appears after returning with ?checkout=success", async () => {
    window.history.replaceState({}, "", "/?checkout=success");
    renderStore();
    expect(await screen.findByText(/order confirmed/i)).toBeTruthy();
  });

  it("strips the ?checkout param from the URL", async () => {
    window.history.replaceState({}, "", "/?checkout=success");
    renderStore();
    await screen.findByText(/order confirmed/i);
    expect(window.location.search).toBe("");
  });

  it("shows nothing without a checkout param", () => {
    window.history.replaceState({}, "", "/");
    renderStore();
    expect(screen.queryByText(/order confirmed/i)).toBeNull();
    expect(screen.queryByText(/checkout canceled/i)).toBeNull();
  });
});
