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

export async function fetchHomeData() {
  const response = await fetch(`${API_BASE_URL}/home`);

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
