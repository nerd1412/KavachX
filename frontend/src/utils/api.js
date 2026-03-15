import axios from 'axios'

const PROD_URL = "https://kavachx-gaas.onrender.com/api/v1"
export const BASE = import.meta.env.VITE_API_URL || PROD_URL
console.log(`[KavachX] API Base: ${BASE}`);

export const api = axios.create({
  baseURL: BASE,
  timeout: 12000,
})

api.interceptors.request.use(cfg => {
  const token = localStorage.getItem('kavachx_token')
  if (token) cfg.headers.Authorization = `Bearer ${token}`
  return cfg
})

api.interceptors.response.use(
  r => r,
  err => {
    // Only force-logout on 401 (token invalid), not 403 (forbidden) or network errors
    if (err.response?.status === 401) {
      localStorage.removeItem('kavachx_token')
      localStorage.removeItem('kavachx_user')
      window.location.href = '/login'
    }
    return Promise.reject(err)
  }
)

export const dashboardAPI = {
  getStats: () => api.get('/dashboard/stats'),
  getRiskTrend: (h = 24) => api.get(`/dashboard/risk-trend?hours=${h}`),
  getEnforcementBreakdown: () => api.get('/dashboard/enforcement-breakdown'),
  getComplianceSummary: () => api.get('/dashboard/compliance-summary'),
  getDebugLogs: (params) => api.get('/dashboard/debug-logs', { params }),
}

export const modelsAPI = {
  list: () => api.get('/models/'),
  get: id => api.get(`/models/${id}`),
  create: d => api.post('/models/', d),
  updateStatus: (id, status) => api.patch(`/models/${id}/status`, { status }),
}

export const policiesAPI = {
  list: () => api.get('/policies/'),
  create: d => api.post('/policies/', d),
  update: (id, d) => api.put(`/policies/${id}`, d),
  delete: id => api.delete(`/policies/${id}`),
  toggle: (id, enabled) => api.patch(`/policies/${id}/toggle`, { enabled }),
}

export const auditAPI = {
  getLogs: params => api.get('/audit/logs', { params }),
  getEvents: params => api.get('/audit/events', { params }),
}

export const governanceAPI = {
  evaluate: d => api.post('/governance/evaluate', d),
  simulate: d => api.post('/governance/simulate', d),  // no auth, auto-model, persists to DB
  getInferences: params => api.get('/governance/inferences', { params }),
  getInference: id => api.get(`/governance/inferences/${id}`),
}

export const settingsAPI = {
  getThresholds: () => api.get('/settings/thresholds'),
  updateThresholds: d => api.put('/settings/thresholds', d),
}
