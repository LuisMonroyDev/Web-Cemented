// All HTTP calls to the Django backend live in this one file.
// Auth is session-cookie based, so every request sends credentials, and
// state-changing requests include the CSRF token Django expects.
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

// The Django admin lives on the backend host (band/staff only).
export const ADMIN_URL = `${API_BASE_URL}/admin/`;

function getCookie(name) {
  const match = document.cookie.match(new RegExp("(?:^|; )" + name + "=([^;]*)"));
  return match ? decodeURIComponent(match[1]) : null;
}

// Make sure the csrftoken cookie exists before a write request.
async function ensureCsrf() {
  if (!getCookie("csrftoken")) {
    await fetch(`${API_BASE_URL}/api/auth/csrf/`, { credentials: "include" });
  }
}

async function request(path, { method = "GET", body } = {}) {
  const headers = {};
  const opts = { method, credentials: "include", headers };
  if (body !== undefined) {
    headers["Content-Type"] = "application/json";
    opts.body = JSON.stringify(body);
  }
  if (method !== "GET" && method !== "HEAD") {
    await ensureCsrf();
    headers["X-CSRFToken"] = getCookie("csrftoken") ?? "";
  }

  const response = await fetch(`${API_BASE_URL}${path}`, opts);
  if (!response.ok) {
    let detail;
    try {
      detail = (await response.json()).detail;
    } catch {
      // response had no JSON body
    }
    const error = new Error(detail || `Request failed (${response.status})`);
    error.status = response.status;
    throw error;
  }
  return response.status === 204 ? null : response.json();
}

// --- public storefront data ---
export const fetchHealth = () => request("/api/health/");
export const fetchProducts = () => request("/api/products/");
export const fetchGallery = () => request("/api/gallery/");
export const fetchSiteSettings = () => request("/api/settings/");

// --- auth (customers) ---
export const register = (data) => request("/api/auth/register/", { method: "POST", body: data });
export const login = (username, password) =>
  request("/api/auth/login/", { method: "POST", body: { username, password } });
export const logout = () => request("/api/auth/logout/", { method: "POST" });
export const fetchMe = () => request("/api/auth/me/");

// --- cart ---
export const fetchCart = () => request("/api/cart/");
export const addToCart = (productId, quantity = 1) =>
  request("/api/cart/items/", { method: "POST", body: { product_id: productId, quantity } });
export const updateCartItem = (itemId, quantity) =>
  request(`/api/cart/items/${itemId}/`, { method: "PATCH", body: { quantity } });
export const removeCartItem = (itemId) =>
  request(`/api/cart/items/${itemId}/`, { method: "DELETE" });

// --- checkout ---
export const checkout = () => request("/api/checkout/", { method: "POST" });
