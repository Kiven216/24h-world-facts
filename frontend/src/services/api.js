function resolveDefaultApiBaseUrl() {
  if (typeof window === 'undefined') {
    return 'http://127.0.0.1:8000';
  }

  const { protocol, hostname } = window.location;
  return `${protocol}//${hostname}:8000`;
}

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || resolveDefaultApiBaseUrl();

export async function fetchHomeData() {
  const response = await fetch(`${API_BASE_URL}/api/home`);

  if (!response.ok) {
    throw new Error(`Request failed with status ${response.status}`);
  }

  return response.json();
}

export async function triggerBackendRefresh() {
  const response = await fetch(`${API_BASE_URL}/api/admin/refresh`, {
    method: 'POST',
  });

  if (!response.ok) {
    throw new Error(`Refresh failed with status ${response.status}`);
  }

  return response.json();
}
