/**
 * ShipIQ API service — pure fetch, no axios dependency.
 *
 * All functions accept an optional sessionId (default: "default")
 * so the UI can support multi-session workflows in the future.
 */

const BASE = (import.meta.env.VITE_API_URL || '/api').replace(/\/$/, '');

async function request(path, options = {}) {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: `HTTP ${res.status}` }));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }
  return res.status === 204 ? null : res.json();
}

export const api = {
  health: () => request('/health'),

  submitInput: (cargos, tanks, sessionId = 'default') =>
    request(sessionId === 'default' ? '/input' : `/input/${sessionId}`, {
      method: 'POST',
      body: JSON.stringify({ cargos, tanks }),
    }),

  optimize: (sessionId = 'default') =>
    request(sessionId === 'default' ? '/optimize' : `/optimize/${sessionId}`, {
      method: 'POST',
    }),

  getResults: (sessionId = 'default') =>
    request(sessionId === 'default' ? '/results' : `/results/${sessionId}`),

  clearSession: (sessionId) => request(`/session/${sessionId}`, { method: 'DELETE' }),
};

export default api;
