/**
 * API helper - handles all backend communication.
 */
const API = (() => {
  const BASE = '';
  const TOKEN_KEY = 'smm_auth_token';

  function getToken() {
    return localStorage.getItem(TOKEN_KEY) || '';
  }

  function setToken(token) {
    localStorage.setItem(TOKEN_KEY, token);
  }

  function clearToken() {
    localStorage.removeItem(TOKEN_KEY);
  }

  function isLoggedIn() {
    return !!getToken();
  }

  async function request(method, path, body) {
    const opts = { method, headers: {} };
    const token = getToken();
    if (token) {
      opts.headers['Authorization'] = 'Bearer ' + token;
    }
    if (body && !(body instanceof FormData)) {
      opts.headers['Content-Type'] = 'application/json';
      opts.body = JSON.stringify(body);
    } else if (body instanceof FormData) {
      opts.body = body;
    }
    const resp = await fetch(BASE + path, opts);
    const data = await resp.json();
    if (resp.status === 401 && data.detail) {
      clearToken();
      throw new Error(data.detail);
    }
    if (!resp.ok && data.detail) throw new Error(data.detail);
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    return data;
  }

  return {
    // Auth
    login: (username, password) => request('POST', '/api/auth/login', { username, password }),
    logout: () => request('POST', '/api/auth/logout'),
    getMe: () => request('GET', '/api/auth/me'),
    getToken,
    setToken,
    clearToken,
    isLoggedIn,

    // Health
    health: () => request('GET', '/api/health'),

    // Platforms
    listPlatforms: () => request('GET', '/api/accounts/platforms'),

    // Groups
    listGroups: () => request('GET', '/api/groups'),
    createGroup: (data) => request('POST', '/api/groups', data),
    updateGroup: (id, data) => request('PUT', `/api/groups/${id}`, data),
    deleteGroup: (id) => request('DELETE', `/api/groups/${id}`),

    // Accounts
    listAccounts: (params) => {
      const q = new URLSearchParams(params || {}).toString();
      return request('GET', `/api/accounts${q ? '?' + q : ''}`);
    },
    getAccount: (id) => request('GET', `/api/accounts/${id}`),
    createAccount: (data) => request('POST', '/api/accounts', data),
    updateAccount: (id, data) => request('PUT', `/api/accounts/${id}`, data),
    deleteAccount: (id) => request('DELETE', `/api/accounts/${id}`),
    verifyAccount: (id) => request('POST', `/api/accounts/${id}/verify`),
    healthCheckAccount: (id) => request('POST', `/api/accounts/${id}/health-check`),

    // Auth / Credential helpers
    credentialMethods: (platform) => request('GET', `/api/auth/credential-methods/${platform}`),
    credentialFields: (platform, method) => request('GET', `/api/auth/credential-fields/${platform}/${method}`),
    qrRequest: (platform) => request('POST', '/api/auth/qr/request', { platform }),
    qrStatus: (token) => request('GET', `/api/auth/qr/status/${token}`),

    // Content
    listContent: (params) => {
      const q = new URLSearchParams(params || {}).toString();
      return request('GET', `/api/content${q ? '?' + q : ''}`);
    },
    getContent: (id) => request('GET', `/api/content/${id}`),
    createContent: (data) => request('POST', '/api/content', data),
    updateContent: (id, data) => request('PUT', `/api/content/${id}`, data),
    deleteContent: (id) => request('DELETE', `/api/content/${id}`),
    uploadFile: (file) => {
      const fd = new FormData();
      fd.append('file', file);
      return fetch(BASE + '/api/content/upload', { method: 'POST', body: fd }).then(r => r.json());
    },
    publishContent: (contentId, accountId) => {
      const q = accountId ? `?account_id=${accountId}` : '';
      return request('POST', `/api/content/${contentId}/publish${q}`);
    },
    scheduleContent: (contentId, scheduledAt, accountIds) => {
      return request('POST', `/api/content/${contentId}/schedule`, { scheduled_at: scheduledAt, account_ids: accountIds });
    },
    listSchedules: (status) => {
      const q = status ? `?status=${status}` : '';
      return request('GET', `/api/content/schedules/all${q}`);
    },

    // Media Library
    listMedia: (params) => {
      const q = new URLSearchParams(params || {}).toString();
      return request('GET', `/api/content/media${q ? '?' + q : ''}`);
    },
    deleteMedia: (id) => request('DELETE', `/api/content/media/${id}`),

    // AI Content
    aiGenerate: (data) => request('POST', '/api/content/ai/generate', data),
    aiHashtags: (data) => request('POST', '/api/content/ai/hashtags', data),

    // Templates
    listTemplates: (platform) => {
      const q = platform ? `?platform=${platform}` : '';
      return request('GET', `/api/templates${q}`);
    },
    createTemplate: (data) => request('POST', '/api/templates', data),
    updateTemplate: (id, data) => request('PUT', `/api/templates/${id}`, data),
    deleteTemplate: (id) => request('DELETE', `/api/templates/${id}`),

    // Publish
    batchPublish: (data) => request('POST', '/api/publish/batch', data),
    smartSchedule: (data) => request('POST', '/api/publish/smart-schedule', data),
    listPublishQueue: (status) => {
      const q = status ? `?status=${status}` : '';
      return request('GET', `/api/publish/queue${q}`);
    },
    retrySchedule: (id) => request('POST', `/api/publish/queue/${id}/retry`),
    cancelSchedule: (id) => request('DELETE', `/api/publish/queue/${id}`),

    // Dashboard
    getStats: () => request('GET', '/api/dashboard/stats'),
    getRecentActivity: (limit) => request('GET', `/api/dashboard/recent-activity?limit=${limit || 20}`),
    getPlatformSummary: () => request('GET', '/api/dashboard/platform-summary'),
    getNextSchedules: (limit) => request('GET', `/api/dashboard/next-schedules?limit=${limit || 10}`),
    getCalendarSchedules: (year, month) => {
      const y = year || new Date().getFullYear();
      const m = month || (new Date().getMonth() + 1);
      return request('GET', `/api/dashboard/calendar?year=${y}&month=${m}`);
    },

    // Analytics
    getAnalyticsOverview: (days) => request('GET', `/api/analytics/overview${days ? '?days=' + days : ''}`),
    getPlatformAnalytics: (platform) => request('GET', `/api/analytics/platform/${platform}`),
    getAccountAnalytics: (id) => request('GET', `/api/analytics/account/${id}`),
    getTrends: (days) => request('GET', `/api/analytics/trends${days ? '?days=' + days : ''}`),
    getPublishingStats: () => request('GET', '/api/analytics/publishing-stats'),
  };
})();
