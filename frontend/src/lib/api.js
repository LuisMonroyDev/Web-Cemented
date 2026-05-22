// All HTTP calls to the Django backend live in this one file
// (see docs/plan/03-conventions.md). The base URL comes from VITE_API_BASE_URL;
// it falls back to the local Django dev server so the app runs without a .env.
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export async function fetchHealth() {
  const response = await fetch(`${API_BASE_URL}/api/health/`);
  if (!response.ok) {
    throw new Error(`API responded with ${response.status}`);
  }
  return response.json();
}
