// All HTTP calls to the Django backend live in this one file
// (see docs/plan/03-conventions.md). The base URL comes from VITE_API_BASE_URL;
// it falls back to the local Django dev server so the app runs without a .env.
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

// The Django admin lives on the backend host. Band/staff log in here.
export const ADMIN_URL = `${API_BASE_URL}/admin/`;

async function getJSON(path) {
  const response = await fetch(`${API_BASE_URL}${path}`);
  if (!response.ok) {
    throw new Error(`API responded with ${response.status}`);
  }
  return response.json();
}

export function fetchHealth() {
  return getJSON("/api/health/");
}

export function fetchProducts() {
  return getJSON("/api/products/");
}

export function fetchGallery() {
  return getJSON("/api/gallery/");
}

export function fetchSiteSettings() {
  return getJSON("/api/settings/");
}
