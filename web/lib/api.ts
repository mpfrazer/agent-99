import type {
  AgentConfig,
  AgentSummary,
  RunDetail,
  RunSummary,
  StartRunRequest,
  StartRunResponse,
} from './types';

const BASE = '/api';

async function request<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    credentials: 'include',
    headers: { 'Content-Type': 'application/json', ...options.headers },
    ...options,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail ?? res.statusText);
  }
  return res.json() as Promise<T>;
}

// ---------------------------------------------------------------------------
// Auth
// ---------------------------------------------------------------------------

export const auth = {
  login: (password: string) =>
    request<{ authenticated: boolean }>('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ password }),
    }),

  logout: () =>
    request<{ authenticated: boolean }>('/auth/logout', { method: 'POST' }),

  me: () =>
    request<{ authenticated: boolean }>('/auth/me'),

  changePassword: (password: string) =>
    request<{ ok: boolean }>('/auth/password', {
      method: 'POST',
      body: JSON.stringify({ password }),
    }),
};

// ---------------------------------------------------------------------------
// Tools
// ---------------------------------------------------------------------------

export const tools = {
  list: () => request<{ name: string; description: string }[]>('/tools'),
};

// ---------------------------------------------------------------------------
// Agents
// ---------------------------------------------------------------------------

export const agents = {
  list: () => request<AgentSummary[]>('/agents'),

  get: (name: string) => request<AgentConfig>(`/agents/${name}`),

  create: (payload: AgentConfig) =>
    request<{ name: string }>('/agents', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  update: (name: string, payload: AgentConfig) =>
    request<{ name: string }>(`/agents/${name}`, {
      method: 'PUT',
      body: JSON.stringify(payload),
    }),

  delete: (name: string) =>
    request<{ deleted: string }>(`/agents/${name}`, { method: 'DELETE' }),
};

// ---------------------------------------------------------------------------
// Runs
// ---------------------------------------------------------------------------

export const runs = {
  start: (body: StartRunRequest) =>
    request<StartRunResponse>('/runs', {
      method: 'POST',
      body: JSON.stringify(body),
    }),

  list: (status?: string) =>
    request<RunSummary[]>(`/runs${status ? `?status=${status}` : ''}`),

  get: (id: string) => request<RunDetail>(`/runs/${id}`),

  cancel: (id: string) =>
    request<{ cancelled: string }>(`/runs/${id}`, { method: 'DELETE' }),
};
