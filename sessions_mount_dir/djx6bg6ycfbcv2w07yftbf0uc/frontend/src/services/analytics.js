import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api';

const MAX_RETRIES = 3;
const RETRY_DELAY = 1000;

const sleep = (ms) => new Promise(resolve => setTimeout(resolve, ms));

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
});

apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('authToken');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

const handleApiError = (error) => {
  if (error.response) {
    const { status, data } = error.response;
    switch (status) {
      case 401:
        throw new Error('未授权，请重新登录');
      case 403:
        throw new Error('权限不足');
      case 404:
        throw new Error('请求的资源不存在');
      case 500:
        throw new Error('服务器内部错误');
      default:
        throw new Error(data.message || '请求失败');
    }
  } else if (error.request) {
    throw new Error('网络错误，请检查网络连接');
  } else {
    throw new Error('请求配置错误');
  }
};

const fetchWithRetry = async (url, options = {}, retries = MAX_RETRIES) => {
  try {
    const response = await apiClient({ url, ...options });
    return response.data;
  } catch (error) {
    if (retries > 0 && error.response?.status >= 500) {
      await sleep(RETRY_DELAY);
      return fetchWithRetry(url, options, retries - 1);
    }
    handleApiError(error);
  }
};

export const analyticsService = {
  async getBookingStats(params = {}) {
    return fetchWithRetry('/analytics/bookings', {
      method: 'GET',
      params,
    });
  },

  async getMemberGrowth(params = {}) {
    return fetchWithRetry('/analytics/members', {
      method: 'GET',
      params,
    });
  },

  async getCourseRanking(params = {}) {
    return fetchWithRetry('/analytics/courses', {
      method: 'GET',
      params,
    });
  },

  async getRevenueStats(params = {}) {
    return fetchWithRetry('/analytics/revenue', {
      method: 'GET',
      params,
    });
  },

  async getDashboardSummary() {
    return fetchWithRetry('/analytics/dashboard', {
      method: 'GET',
    });
  },
};

export default analyticsService;
