import axios from 'axios';
import { useAuthStore } from '../stores/auth';

// Create axios instance
const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api',
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor to add auth token
api.interceptors.request.use(
  (config) => {
    const authStore = useAuthStore();
    if (authStore.token) {
      config.headers.Authorization = `Bearer ${authStore.token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor to handle common errors
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const authStore = useAuthStore();
    
    // Handle 401 Unauthorized
    if (error.response?.status === 401) {
      authStore.logout();
      // Redirect to login page or handle as needed
      window.location.href = '/login';
    }
    
    return Promise.reject(error);
  }
);

// Course related API calls
export const courseApi = {
  // Get all available courses
  getCourses: async () => {
    const response = await api.get('/courses');
    return response.data;
  },

  // Get course details by ID
  getCourseById: async (courseId) => {
    const response = await api.get(`/courses/${courseId}`);
    return response.data;
  },

  // Book a course
  bookCourse: async (courseId) => {
    const response = await api.post(`/courses/${courseId}/book`);
    return response.data;
  },

  // Cancel a course booking
  cancelBooking: async (courseId) => {
    const response = await api.delete(`/courses/${courseId}/book`);
    return response.data;
  },

  // Get user's booked courses
  getMyBookings: async () => {
    const response = await api.get('/courses/my-bookings');
    return response.data;
  },
};

// Auth related API calls (alternative to auth store)
export const authApi = {
  login: async (credentials) => {
    const response = await api.post('/auth/login', credentials);
    return response.data;
  },

  register: async (userData) => {
    const response = await api.post('/auth/register', userData);
    return response.data;
  },

  getCurrentUser: async () => {
    const response = await api.get('/auth/me');
    return response.data;
  },

  updateProfile: async (profileData) => {
    const response = await api.put('/auth/profile', profileData);
    return response.data;
  },
};

export default api;