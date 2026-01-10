import axios, { AxiosInstance, InternalAxiosRequestConfig, AxiosResponse } from 'axios';

// API Configuration
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v2';

// Create axios instance
const api: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor for auth
api.interceptors.request.use(
  (config: InternalAxiosRequestConfig): InternalAxiosRequestConfig => {
    const token = localStorage.getItem('access_token');
    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor for error handling
api.interceptors.response.use(
  (response: AxiosResponse) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('access_token');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

// API Endpoints
export const endpoints = {
  // Authentication
  login: '/token',
  register: '/auth/register',
  refresh: '/refresh-token',
  forgotPassword: '/auth/forgot-password',
  resetPassword: '/auth/reset-password',
  currentUser: '/users/me',

  // Subscription
  subscribe: '/subscription/subscribe',
  subscriptionStatus: '/subscription/status',

  // Dashboard
  dashboard: '/stats',

  // Records
  records: '/records',
  record: (id: string) => `/records/${id}`,

  // Search
  search: '/search',

  // Jurisdictions
  jurisdictions: '/jurisdictions',

  // Data Sources
  dataSources: '/data-sources',

  // Entities
  entities: '/entities',
  entity: (id: string) => `/entities/${id}`,

  // Relationships
  relationships: '/relationships',

  // Export
  export: '/export',

  // Settings
  settings: '/settings',
  profile: '/users/me',

  // Health
  health: '/health',
};

// API Methods
export const apiService = {
  // Authentication
  async login(credentials: { email: string; password: string }) {
    // OAuth2 expects form data with username field
    const formData = new URLSearchParams();
    formData.append('username', credentials.email);
    formData.append('password', credentials.password);
    formData.append('grant_type', 'password');

    return api.post(endpoints.login, formData, {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    });
  },

  async register(userData: { username?: string; email: string; password: string; full_name?: string }) {
    return api.post(endpoints.register, {
      username: userData.username || userData.email.split('@')[0],
      email: userData.email,
      password: userData.password,
      full_name: userData.full_name || '',
    });
  },

  async forgotPassword(email: string) {
    return api.post(endpoints.forgotPassword, { email });
  },

  async resetPassword(token: string, newPassword: string) {
    return api.post(endpoints.resetPassword, { token, new_password: newPassword });
  },

  async refreshToken() {
    return api.post(endpoints.refresh);
  },

  async getCurrentUser() {
    return api.get(endpoints.currentUser);
  },

  async updateProfile(data: Record<string, any>) {
    return api.put(endpoints.profile, data);
  },

  // Subscription
  async subscribe(subscriptionData: { tier: string }) {
    return api.post(endpoints.subscribe, subscriptionData);
  },

  async getSubscriptionStatus() {
    return api.get(endpoints.subscriptionStatus);
  },

  // Dashboard
  async getDashboardStats() {
    return api.get(endpoints.dashboard);
  },

  // Records
  async getRecords(params?: {
    page?: number;
    limit?: number;
    search?: string;
    jurisdiction_id?: number;
    record_type?: string;
    date_from?: string;
    date_to?: string;
    amount_min?: number;
    amount_max?: number;
    sort_by?: string;
    sort_order?: 'asc' | 'desc';
  }) {
    return api.get(endpoints.records, { params });
  },

  async getRecord(id: string) {
    return api.get(endpoints.record(id));
  },

  // Search
  async search(query: string, filters?: {
    jurisdiction_ids?: number[];
    record_types?: string[];
    date_from?: string;
    date_to?: string;
    amount_min?: number;
    amount_max?: number;
    page?: number;
    page_size?: number;
    sort_by?: string;
    sort_order?: 'asc' | 'desc';
  }) {
    return api.post(endpoints.search, { query, ...filters });
  },

  // Jurisdictions
  async getJurisdictions(params?: {
    state?: string;
    limit?: number;
    offset?: number;
  }) {
    return api.get(endpoints.jurisdictions, { params });
  },

  // Data Sources
  async getDataSources(params?: {
    jurisdiction_id?: number;
    status?: string;
  }) {
    return api.get(endpoints.dataSources, { params });
  },

  // Entities
  async getEntities(params?: {
    entity_type?: string;
    name?: string;
    limit?: number;
    offset?: number;
  }) {
    return api.get(endpoints.entities, { params });
  },

  async getEntity(id: string) {
    return api.get(endpoints.entity(id));
  },

  // Export
  async exportData(format: 'csv' | 'json' | 'excel', query?: string, filters?: Record<string, any>) {
    return api.post(endpoints.export, { format, query, ...filters }, {
      responseType: format === 'json' ? 'json' : 'blob',
    });
  },

  // Health
  async getHealth() {
    return api.get(endpoints.health);
  },

  // Sharing (stub - needs backend implementation)
  async shareRecord(data: { recordId: string; email: string; message: string }) {
    // TODO: Implement when backend endpoint is ready
    return Promise.resolve({ data: { success: true } });
  },
};

export default api;
