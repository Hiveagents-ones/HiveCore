import axios from 'axios';

const API_BASE_URL = process.env.VUE_APP_API_URL || 'http://localhost:8000/api/v1';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add authorization header to all requests
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Handle token refresh or logout on 401/403 errors
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401 || error.response?.status === 403) {
      localStorage.removeItem('access_token');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

export const authAPI = {
  // Authentication
  login: async (username, password) => {
    const formData = new FormData();
    formData.append('username', username);
    formData.append('password', password);
    
    const response = await api.post('/auth/login', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    
    localStorage.setItem('access_token', response.data.access_token);
    return response.data;
  },

  logout: () => {
    localStorage.removeItem('access_token');
    window.location.href = '/login';
  },

  // Role management
  getRoles: async () => {
    const response = await api.get('/auth/roles');
    return response.data;
  },

  createRole: async (roleData) => {
    const response = await api.post('/auth/roles', roleData);
    return response.data;
  },

  updateRole: async (roleId, roleData) => {
    const response = await api.put(`/auth/roles/${roleId}`, roleData);
    return response.data;
  },

  deleteRole: async (roleId) => {
    const response = await api.delete(`/auth/roles/${roleId}`);
    return response.data;
  },

  // Permission management
  getPermissions: async () => {
    const response = await api.get('/auth/permissions');
    return response.data;
  },

  createPermission: async (permissionData) => {
    const response = await api.post('/auth/permissions', permissionData);
    return response.data;
  },

  updatePermission: async (permissionId, permissionData) => {
    const response = await api.put(`/auth/permissions/${permissionId}`, permissionData);
    return response.data;
  },

  deletePermission: async (permissionId) => {
    const response = await api.delete(`/auth/permissions/${permissionId}`);
    return response.data;
  },

  // User management
  getCurrentUser: async () => {
    const response = await api.get('/auth/me');
    return response.data;
  },
};

export default api;