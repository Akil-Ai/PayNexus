/**
 * PayNexus API Client Library
 * Connects to the FastAPI backend with token injection, error handling, and complete typed methods.
 */

const BASE_URL = import.meta.env.VITE_API_URL || '';

export function getAuthHeaders(): HeadersInit {
  const token = localStorage.getItem('paynexus_token');
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  return headers;
}

async function request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const url = `${BASE_URL}${endpoint}`;
  const headers = {
    ...getAuthHeaders(),
    ...(options.headers || {}),
  };

  const response = await fetch(url, {
    ...options,
    headers,
  });

  if (response.status === 401) {
    // If not on login page, redirect or clear token
    if (!window.location.pathname.includes('/login')) {
      localStorage.removeItem('paynexus_token');
      localStorage.removeItem('paynexus_user');
      window.location.href = '/login';
    }
  }

  if (!response.ok) {
    let errorDetail = `Request failed: ${response.status} ${response.statusText}`;
    try {
      const errJson = await response.json();
      errorDetail = errJson.detail || errJson.title || errorDetail;
    } catch {
      // not JSON
    }
    throw new Error(errorDetail);
  }

  // Handle empty responses
  const contentType = response.headers.get('content-type');
  if (contentType && contentType.includes('application/json')) {
    return response.json();
  }
  return response.text() as unknown as T;
}

export const api = {
  // ── Auth ──
  login: async (formData: URLSearchParams | FormData) => {
    const url = `${BASE_URL}/api/v1/auth/login`;
    const res = await fetch(url, {
      method: 'POST',
      body: formData,
    });
    if (!res.ok) {
      let msg = 'Login failed';
      try {
        const j = await res.json();
        msg = j.detail || msg;
      } catch {}
      throw new Error(msg);
    }
    return res.json();
  },

  getMe: () => request<any>('/api/v1/auth/me'),

  // ── Dashboard & Analytics ──
  getDashboardMetrics: () => request<any>('/api/v1/analytics/dashboard'),

  // ── Payments ──
  listPayments: (params?: {
    state?: string;
    rail?: string;
    currency?: string;
    customer_id?: string;
    search?: string;
    page?: number;
    page_size?: number;
    limit?: number;
  }) => {
    const query = new URLSearchParams();
    if (params?.state) query.append('state', params.state);
    if (params?.rail) query.append('rail', params.rail);
    if (params?.currency) query.append('currency', params.currency);
    if (params?.customer_id) query.append('customer_id', params.customer_id);
    if (params?.search) query.append('search', params.search);
    if (params?.page) query.append('page', String(params.page));
    if (params?.limit) query.append('page_size', String(params.limit));
    else if (params?.page_size) query.append('page_size', String(params.page_size));

    const qs = query.toString();
    return request<any>(`/api/v1/payments${qs ? `?${qs}` : ''}`);
  },

  getPaymentById: (id: string) => request<any>(`/api/v1/payments/${id}`),

  createPayment: (payload: any, idempotencyKey?: string) => {
    const key = idempotencyKey || `pnx_ui_${Date.now()}_${Math.random().toString(36).substring(2, 9)}`;
    return request<any>('/api/v1/payments', {
      method: 'POST',
      headers: {
        'Idempotency-Key': key,
      },
      body: JSON.stringify(payload),
    });
  },

  cancelPayment: (id: string, reason?: string) =>
    request<any>(`/api/v1/payments/${id}/cancel`, {
      method: 'POST',
      body: JSON.stringify({ reason: reason || 'User cancelled' }),
    }),

  refundPayment: (id: string, amount_minor?: number, reason?: string) =>
    request<any>(`/api/v1/payments/${id}/refund`, {
      method: 'POST',
      body: JSON.stringify({ amount_minor, reason: reason || 'User requested refund' }),
    }),

  // ── Rails & Orchestration ──
  listRails: () => request<any[]>('/api/v1/rails/'),

  recommendRail: (params: { amount_minor: number; currency?: string; urgency?: string; destination_country?: string }) =>
    request<any>('/api/v1/rails/recommend', {
      method: 'POST',
      body: JSON.stringify({
        amount_minor: params.amount_minor,
        currency: params.currency || 'INR',
        urgency: params.urgency || 'NORMAL',
        destination_country: params.destination_country || 'IN',
      }),
    }),

  configureRailChaos: (railCode: string, chaosConfig: { latency_ms: number; error_rate: number; drop_response_rate: number; is_down: boolean }) =>
    request<any>(`/api/v1/rails/${railCode}/chaos`, {
      method: 'POST',
      body: JSON.stringify(chaosConfig),
    }),

  resetCircuitBreaker: (railCode: string) =>
    request<any>(`/api/v1/rails/${railCode}/circuit-breaker/reset`, {
      method: 'POST',
    }),

  // ── Compliance, Screening, & Approvals ──
  getScreeningQueue: (resultFilter?: string) => {
    const qs = resultFilter ? `?result_filter=${resultFilter}` : '';
    return request<any[]>(`/api/v1/compliance/screening-queue${qs}`);
  },

  listWatchlists: () => request<any[]>('/api/v1/compliance/watchlists'),

  listFraudRules: () => request<any[]>('/api/v1/compliance/fraud-rules'),

  toggleFraudRule: (ruleId: string) =>
    request<any>(`/api/v1/compliance/fraud-rules/${ruleId}/toggle`, {
      method: 'POST',
    }),

  processApproval: (approvalId: string, action: 'APPROVE' | 'REJECT', notes?: string) =>
    request<any>(`/api/v1/compliance/approvals/${approvalId}`, {
      method: 'POST',
      body: JSON.stringify({ action, notes }),
    }),

  // ── Reconciliation ──
  listReconRuns: (limit = 50) => request<any[]>(`/api/v1/reconciliation/runs?limit=${limit}`),

  getReconRun: (runId: string) => request<any>(`/api/v1/reconciliation/runs/${runId}`),

  getRunExceptions: (runId: string) => request<any[]>(`/api/v1/reconciliation/runs/${runId}/exceptions`),

  uploadAndRunStatement: async (formData: FormData) => {
    const token = localStorage.getItem('paynexus_token');
    const headers: Record<string, string> = {};
    if (token) headers['Authorization'] = `Bearer ${token}`;

    const res = await fetch(`${BASE_URL}/api/v1/reconciliation/upload-and-run`, {
      method: 'POST',
      headers,
      body: formData,
    });
    if (!res.ok) {
      let msg = 'Statement upload failed';
      try {
        const j = await res.json();
        msg = j.detail || msg;
      } catch {}
      throw new Error(msg);
    }
    return res.json();
  },

  resolveException: (exceptionId: string, resolutionAction: string, notes?: string) =>
    request<any>(`/api/v1/reconciliation/exceptions/${exceptionId}/resolve`, {
      method: 'POST',
      body: JSON.stringify({ resolution_action: resolutionAction, notes }),
    }),

  // ── Exceptions & DLQ ──
  listExceptions: (statusFilter?: string) => {
    const qs = statusFilter ? `?status_filter=${statusFilter}` : '';
    return request<any[]>(`/api/v1/exceptions/${qs}`);
  },

  assignException: (caseId: string, assignedTo: string) =>
    request<any>(`/api/v1/exceptions/${caseId}/assign`, {
      method: 'POST',
      body: JSON.stringify({ assigned_to: assignedTo }),
    }),

  listDlq: () => request<any[]>('/api/v1/exceptions/dlq'),

  replayDlq: (eventIds: string[]) =>
    request<any>('/api/v1/exceptions/dlq/replay', {
      method: 'POST',
      body: JSON.stringify({ event_ids: eventIds }),
    }),

  // ── Cryptographic Audit Trail ──
  listAuditLogs: (params?: { entity_type?: string; entity_id?: string; actor_id?: string; limit?: number }) => {
    const query = new URLSearchParams();
    if (params?.entity_type) query.append('entity_type', params.entity_type);
    if (params?.entity_id) query.append('entity_id', params.entity_id);
    if (params?.actor_id) query.append('actor_id', params.actor_id);
    if (params?.limit) query.append('limit', String(params.limit));
    const qs = query.toString();
    return request<any[]>(`/api/v1/audit/${qs ? `?${qs}` : ''}`);
  },

  verifyAuditIntegrity: () =>
    request<any>('/api/v1/audit/verify', {
      method: 'POST',
    }),

  tamperDemo: (rowSequence?: number, corruptedAction?: string) =>
    request<any>('/api/v1/audit/tamper-demo', {
      method: 'POST',
      body: JSON.stringify({
        row_sequence: rowSequence,
        corrupted_action: corruptedAction || 'TAMPERED_ACTION_MALICIOUS_OVERRIDE',
      }),
    }),

  // ── ISO 20022 Translator Playground ──
  translateMessage: (content: string, formatType = 'AUTO') =>
    request<any>('/api/v1/messages/translate', {
      method: 'POST',
      body: JSON.stringify({ content, format_type: formatType }),
    }),

  serializeMessage: (canonicalMessage: any, targetFormat = 'PAIN_001') =>
    request<any>('/api/v1/messages/serialize', {
      method: 'POST',
      body: JSON.stringify({ canonical_message: canonicalMessage, target_format: targetFormat }),
    }),

  // ── Admin & Lookups ──
  getSettings: () => request<any[]>('/api/v1/admin/settings'),

  updateSetting: (key: string, value: any, description?: string) =>
    request<any>('/api/v1/admin/settings', {
      method: 'PUT',
      body: JSON.stringify({ key, value, description }),
    }),

  listUsers: () => request<any[]>('/api/v1/admin/users'),

  listApiClients: () => request<any[]>('/api/v1/admin/api-clients'),

  createApiClient: (payload: { name: string; description?: string; rate_limit_per_minute?: number }) =>
    request<any>('/api/v1/admin/api-clients', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  listWebhooks: () => request<any[]>('/api/v1/admin/webhooks/deliveries'),

  getCustomers: (limit = 100) => request<any[]>(`/api/v1/admin/customers?limit=${limit}`),

  getBeneficiaries: (customerId?: string) => {
    const qs = customerId ? `?customer_id=${customerId}` : '';
    return request<any[]>(`/api/v1/admin/beneficiaries${qs}`);
  },

  // ── Novelty Feature: Payment Investigation Assistant ──
  investigateTransaction: (query: string) =>
    request<any>('/api/v1/analytics/investigate', {
      method: 'POST',
      body: JSON.stringify({ query }),
    }),

  // ── Performance & Working Measures System ──
  getPerformanceSummary: (window = '1h') =>
    request<any>(`/api/v1/performance/summary?window=${window}`),

  getPerformanceTargets: () =>
    request<any>('/api/v1/performance/targets'),

  updatePerformanceTargets: (targets: any) =>
    request<any>('/api/v1/performance/targets', {
      method: 'PUT',
      body: JSON.stringify(targets),
    }),

  runWorkingMeasuresSuite: () =>
    request<any>('/api/v1/performance/run-working-measures-suite', {
      method: 'POST',
      body: JSON.stringify({}),
    }),
};
