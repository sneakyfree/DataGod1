import axios, { AxiosInstance, InternalAxiosRequestConfig, AxiosResponse } from 'axios';

// API Configuration
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

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

// Response interceptor: auto-refresh on 401
let isRefreshing = false;
let failedQueue: Array<{ resolve: (v: any) => void; reject: (r: any) => void }> = [];

const processQueue = (error: any, token: string | null = null) => {
  failedQueue.forEach((p) => {
    if (token) p.resolve(token);
    else p.reject(error);
  });
  failedQueue = [];
};

api.interceptors.response.use(
  (response: AxiosResponse) => response,
  async (error) => {
    const originalRequest = error.config;

    // Skip refresh for the refresh endpoint itself
    if (error.response?.status === 401 && !originalRequest._retry && !originalRequest.url?.includes('/refresh-token')) {
      if (isRefreshing) {
        // Queue requests while refresh is in progress
        return new Promise((resolve, reject) => {
          failedQueue.push({ resolve, reject });
        }).then((token) => {
          originalRequest.headers.Authorization = `Bearer ${token}`;
          return api(originalRequest);
        });
      }

      originalRequest._retry = true;
      isRefreshing = true;

      try {
        const refreshResponse = await api.post('/refresh-token');
        const newToken = refreshResponse.data.access_token;
        localStorage.setItem('access_token', newToken);
        processQueue(null, newToken);
        originalRequest.headers.Authorization = `Bearer ${newToken}`;
        return api(originalRequest);
      } catch (refreshError) {
        processQueue(refreshError, null);
        localStorage.removeItem('access_token');
        window.location.href = '/login';
        return Promise.reject(refreshError);
      } finally {
        isRefreshing = false;
      }
    }

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
  subscriptionCheckout: '/subscription/checkout',
  subscriptionPortal: '/subscription/portal',
  subscriptionCancel: '/subscription/cancel',

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
  entityNetwork: (id: string) => `/entities/${id}/network`,
  entityConnections: (id: string) => `/entities/${id}/connections`,
  entityRecords: (id: string) => `/entities/${id}/records`,
  entitySearch: '/entities/search/quick',

  // Relationships
  relationships: '/relationships',

  // Saved Searches
  savedSearches: '/saved-searches',
  savedSearch: (id: number) => `/saved-searches/${id}`,
  runSavedSearch: (id: number) => `/saved-searches/${id}/run`,

  // Favorites
  favorites: '/favorites',
  favorite: (id: number) => `/favorites/${id}`,
  checkFavorite: (type: string, itemId: number) => `/favorites/check/${type}/${itemId}`,

  // Activities
  activities: '/activities/recent',
  trackActivity: '/activities/track',
  activityStats: '/activities/stats',

  // Shares
  shares: '/shares',
  share: (id: number) => `/shares/${id}`,
  shareStats: (id: number) => `/shares/${id}/stats`,
  publicShare: (token: string) => `/share/${token}`,

  // Export
  export: '/export',

  // Settings
  settings: '/settings',
  profile: '/users/me',
  changePassword: '/users/me/password',
  notificationSettings: '/users/me/notifications',

  // Health
  health: '/health',

  // Coverage Tracking (Admin)
  coverageSummary: '/admin/coverage/summary',
  coverageByState: '/admin/coverage/by-state',
  coverageGaps: '/admin/coverage/gaps',
  coverageRefresh: (fips: string) => `/admin/coverage/refresh/${fips}`,
  coverageCategories: '/admin/coverage/categories',
  coverageQuickStats: '/admin/coverage/stats/quick',
};

// API Methods
export const apiService = {
  // Generic HTTP methods
  async get<T = any>(url: string, config?: any) {
    return api.get<T>(url, config);
  },

  async post<T = any>(url: string, data?: any, config?: any) {
    return api.post<T>(url, data, config);
  },

  async put<T = any>(url: string, data?: any, config?: any) {
    return api.put<T>(url, data, config);
  },

  async delete<T = any>(url: string, config?: any) {
    return api.delete<T>(url, config);
  },

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

  async changePassword(data: { current_password: string; new_password: string }) {
    return api.put(endpoints.changePassword, data);
  },

  async getNotificationSettings() {
    return api.get(endpoints.notificationSettings);
  },

  async updateNotificationSettings(data: {
    email_updates?: boolean;
    security_alerts?: boolean;
    marketing?: boolean;
    weekly_digest?: boolean;
  }) {
    return api.put(endpoints.notificationSettings, data);
  },

  // Subscription
  async subscribe(subscriptionData: { tier: string }) {
    return api.post(endpoints.subscribe, subscriptionData);
  },

  async getSubscriptionStatus() {
    return api.get(endpoints.subscriptionStatus);
  },

  async createCheckoutSession(tier: string) {
    return api.post(`${endpoints.subscriptionCheckout}?tier=${tier}`);
  },

  async createPortalSession() {
    return api.post(endpoints.subscriptionPortal);
  },

  async cancelSubscription() {
    return api.post(endpoints.subscriptionCancel);
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

  async updateRecord(id: string, data: {
    record_type?: string;
    title?: string;
    description?: string;
    amount?: number;
    date?: string;
    raw_data?: Record<string, unknown>;
  }) {
    return api.put(endpoints.record(id), data);
  },

  async deleteRecord(id: string) {
    return api.delete(endpoints.record(id));
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

  async quickEntitySearch(query: string, limit: number = 10) {
    return api.get('/entities/quick-search', { params: { q: query, limit } });
  },

  // Analytics
  async getAnalyticsTimeSeries(period: 'day' | 'week' | 'month' = 'month', months: number = 12) {
    return api.get('/analytics/time-series', { params: { period, months } });
  },

  async getAnalyticsSummary() {
    return api.get('/analytics/summary');
  },

  async getAnalyticsTrends() {
    return api.get('/analytics/trends');
  },

  // Entity Network
  async getEntityNetwork(id: string, depth: number = 2) {
    return api.get(endpoints.entityNetwork(id), { params: { depth } });
  },

  async getEntityConnections(id: string, params?: {
    relationship_type?: string;
    limit?: number;
    offset?: number;
  }) {
    return api.get(endpoints.entityConnections(id), { params });
  },

  async getEntityRecords(id: string, params?: {
    record_type?: string;
    limit?: number;
    offset?: number;
  }) {
    return api.get(endpoints.entityRecords(id), { params });
  },

  async searchEntitiesQuick(query: string, entityType?: string, limit: number = 10) {
    return api.get(endpoints.entitySearch, {
      params: { q: query, entity_type: entityType, limit }
    });
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

  // Comments (FEAT-094)
  async createComment(data: { record_id: number; content: string; parent_id?: number }) {
    return api.post('/comments', data);
  },

  async getComments(recordId: number, params?: { limit?: number; offset?: number }) {
    return api.get('/comments', { params: { record_id: recordId, ...params } });
  },

  async deleteComment(commentId: number) {
    return api.delete(`/comments/${commentId}`);
  },

  // Saved Searches (FEAT-047) — save & execute
  async saveSearch(data: { name: string; query: string; filters?: Record<string, any> }) {
    return api.post('/saved-searches', data);
  },

  async executeSavedSearch(searchId: number) {
    return api.post(`/saved-searches/${searchId}/execute`);
  },

  // Sharing
  async createShareLink(data: {
    record_id?: number;
    entity_id?: number;
    message?: string;
    expires_in_days?: number;
  }) {
    return api.post(endpoints.shares, data);
  },

  async getShareLinks() {
    return api.get(endpoints.shares);
  },

  async getSharedItem(token: string) {
    return api.get(endpoints.publicShare(token));
  },

  async revokeShareLink(id: number) {
    return api.delete(endpoints.share(id));
  },

  async getShareStats(id: number) {
    return api.get(endpoints.shareStats(id));
  },

  // Legacy method for backwards compatibility
  async shareRecord(data: { recordId: string; email?: string; message?: string }) {
    // Create a share link instead
    return api.post(endpoints.shares, {
      record_id: parseInt(data.recordId),
      message: data.message
    });
  },

  // Saved Searches
  async getSavedSearches() {
    return api.get(endpoints.savedSearches);
  },

  async getSavedSearch(id: number) {
    return api.get(endpoints.savedSearch(id));
  },

  async createSavedSearch(data: {
    name: string;
    description?: string;
    search_params: {
      query?: string;
      filters?: Record<string, any>;
    };
    notify_on_new_results?: boolean;
    notification_frequency?: string;
  }) {
    return api.post(endpoints.savedSearches, data);
  },

  async updateSavedSearch(id: number, data: {
    name?: string;
    description?: string;
    search_params?: {
      query?: string;
      filters?: Record<string, any>;
    };
    notify_on_new_results?: boolean;
    notification_frequency?: string;
  }) {
    return api.put(endpoints.savedSearch(id), data);
  },

  async deleteSavedSearch(id: number) {
    return api.delete(endpoints.savedSearch(id));
  },

  async runSavedSearch(id: number) {
    return api.post(endpoints.runSavedSearch(id));
  },

  // Favorites
  async getFavorites(params?: {
    favorite_type?: 'record' | 'entity';
    limit?: number;
    offset?: number;
  }) {
    return api.get(endpoints.favorites, { params });
  },

  async addFavorite(data: {
    record_id?: number;
    entity_id?: number;
    favorite_type: 'record' | 'entity';
    notes?: string;
    tags?: string[];
  }) {
    return api.post(endpoints.favorites, data);
  },

  async updateFavorite(id: number, data: {
    notes?: string;
    tags?: string[];
  }) {
    return api.put(endpoints.favorite(id), data);
  },

  async removeFavorite(id: number) {
    return api.delete(endpoints.favorite(id));
  },

  async checkFavorite(type: 'record' | 'entity', itemId: number) {
    return api.get(endpoints.checkFavorite(type, itemId));
  },

  // Activities
  async getRecentActivities(params?: {
    activity_type?: string;
    limit?: number;
    offset?: number;
  }) {
    return api.get(endpoints.activities, { params });
  },

  async trackActivity(data: {
    activity_type: string;
    record_id?: number;
    entity_id?: number;
    search_id?: number;
    activity_data?: Record<string, any>;
  }) {
    return api.post(endpoints.trackActivity, data);
  },

  async getActivityStats() {
    return api.get(endpoints.activityStats);
  },

  // Search Records (alias for search with different signature)
  async searchRecords(params: {
    query?: string;
    jurisdictionId?: number;
    recordType?: string;
    limit?: number;
  }) {
    return api.post(endpoints.search, {
      query: params.query || '',
      jurisdiction_ids: params.jurisdictionId ? [params.jurisdictionId] : undefined,
      record_types: params.recordType ? [params.recordType] : undefined,
      page_size: params.limit || 10,
    });
  },

  // Coverage Tracking (Admin)
  async getCoverageSummary() {
    return api.get(endpoints.coverageSummary);
  },

  // Admin: Scraper Monitoring & Data Quality
  async getScraperStatus() {
    return api.get('/admin/scrapers/status');
  },

  async getDataQuality() {
    return api.get('/admin/data-quality');
  },

  async getCoverageByState(params?: {
    tier?: number;
    min_coverage?: number;
  }) {
    return api.get(endpoints.coverageByState, { params });
  },

  async getCoverageGaps(params?: {
    state?: string;
    tier?: number;
    limit?: number;
    min_population?: number;
  }) {
    return api.get(endpoints.coverageGaps, { params });
  },

  async refreshJurisdictionCoverage(fips: string, data?: {
    data_categories?: string[];
    force_refresh?: boolean;
  }) {
    return api.post(endpoints.coverageRefresh(fips), data || {});
  },

  async getDataCategories() {
    return api.get(endpoints.coverageCategories);
  },

  async getQuickCoverageStats() {
    return api.get(endpoints.coverageQuickStats);
  },
};

// Type definitions for coverage responses
export interface CoverageSummary {
  total_jurisdictions: number;
  covered_jurisdictions: number;
  coverage_percentage: number;
  total_counties: number;
  covered_counties: number;
  total_states: number;
  covered_states: number;
  total_territories: number;
  covered_territories: number;
  data_categories: Record<string, {
    covered_count: number;
    total_count: number;
    percentage: number;
  }>;
  tier_breakdown: Record<string, {
    states: string[];
    total_counties: number;
    covered_counties: number;
    percentage: number;
  }>;
  last_updated: string;
}

export interface StateCoverage {
  state_code: string;
  state_name: string;
  fips_code: string;
  tier: number;
  total_counties: number;
  covered_counties: number;
  coverage_percentage: number;
  data_categories: Record<string, number>;
  record_count: number;
  last_scraped: string | null;
}

export interface CoverageGap {
  fips_code: string;
  jurisdiction_name: string;
  state: string;
  county: string | null;
  population: number;
  tier: number;
  missing_categories: string[];
  gap_reason: string | null;
  priority_score: number;
}

export interface DataCategory {
  name: string;
  description: string;
  sources: string[];
}

export default api;
