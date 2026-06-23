// src/api/client.js

/**
 * Cliente API centralizado de WorkaTrack.
 * Maneja:
 *  - Base URL desde .env.local
 *  - Token JWT almacenado en localStorage
 *  - Cabeceras comunes
 *  - Manejo básico de errores
 */

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || '/api';

/**
 * apiFetch:
 * Wrapper de fetch. Inserta token automáticamente.
 *
 * @param {string} endpoint - Ej: "/me/tasks"
 * @param {object} options - Opciones fetch
 */
export async function apiFetch(endpoint, options = {}) {
  const token = localStorage.getItem('workatrack_token');

  const headers = {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...(options.headers || {}),
  };

  const resp = await fetch(`${API_BASE_URL}${endpoint}`, {
    ...options,
    headers,
  });

  let data = null;
  try {
    data = await resp.json();
  } catch (_) {
    data = null;
  }

  if (!resp.ok) {
    const message =
      data?.error || data?.message || `Error ${resp.status}`;
    throw new Error(message);
  }

  return data;
}
