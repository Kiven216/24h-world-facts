function resolveDefaultApiBaseUrl() {
  if (typeof window === 'undefined') {
    return 'http://127.0.0.1:8000/api';
  }

  const { protocol, hostname } = window.location;
  return `${protocol}//${hostname}:8000/api`;
}

function normalizeApiBaseUrl(rawUrl) {
  return (rawUrl || '').replace(/\/+$/, '');
}

const API_BASE_URL = normalizeApiBaseUrl(import.meta.env.VITE_API_BASE_URL || resolveDefaultApiBaseUrl());

export async function fetchHomeData({ debug = false } = {}) {
  const url = new URL(`${API_BASE_URL}/home`);
  if (debug) {
    url.searchParams.set('debug', '1');
  }

  const response = await fetch(url.toString());

  if (!response.ok) {
    throw new Error(`Request failed with status ${response.status}`);
  }

  return response.json();
}

export async function triggerBackendRefresh() {
  const response = await fetch(`${API_BASE_URL}/admin/refresh`, {
    method: 'POST',
  });

  if (!response.ok) {
    throw new Error(`Refresh failed with status ${response.status}`);
  }

  return response.json();
}
