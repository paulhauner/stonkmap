import type { DashboardData } from './types';

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? '/api';

async function parseResponse(response: Response) {
  if (!response.ok) {
    let message = `Request failed with status ${response.status}`;
    try {
      const payload = await response.json();
      if (typeof payload?.detail === 'string' && payload.detail) {
        message = payload.detail;
      }
    } catch {
      // Ignore non-JSON error payloads and fall back to the HTTP status message.
    }
    throw new Error(message);
  }
  return response.json();
}

export async function fetchDashboard(): Promise<DashboardData> {
  return parseResponse(await fetch(`${API_BASE}/dashboard`));
}

export async function refreshIndexes(): Promise<void> {
  await parseResponse(
    await fetch(`${API_BASE}/indexes/refresh`, {
      method: 'POST',
    }),
  );
}

export async function refreshPrices(): Promise<void> {
  await parseResponse(
    await fetch(`${API_BASE}/prices/refresh`, {
      method: 'POST',
    }),
  );
}

export async function refreshMarketData(): Promise<void> {
  await refreshIndexes();
  await refreshPrices();
}
