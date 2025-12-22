import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import axios from 'axios';

export const useAuthStore = defineStore('auth', () => {
  // State
  const user = ref(null);
  const token = ref(localStorage.getItem('token') || null);
  const isLoading = ref(false);
  const error = ref(null);

  // Getters
  const isAuthenticated = computed(() => !!token.value);
  const currentUser = computed(() => user.value);

  // Actions
  const login = async (credentials) => {
    isLoading.value = true;
    error.value = null;
    try {
      const response = await axios.post('/api/auth/login', credentials);
      const { access_token, user: userData } = response.data;
      
      token.value = access_token;
      user.value = userData;
      localStorage.setItem('token', access_token);
      
      // Set default auth header
      axios.defaults.headers.common['Authorization'] = `Bearer ${access_token}`;
      
      return { success: true };
    } catch (err) {
      error.value = err.response?.data?.detail || 'Login failed';
      return { success: false, error: error.value };
    } finally {
      isLoading.value = false;
    }
  };

  const logout = () => {
    user.value = null;
    token.value = null;
    localStorage.removeItem('token');
    delete axios.defaults.headers.common['Authorization'];
  };

  const register = async (userData) => {
    isLoading.value = true;
    error.value = null;
    try {
      const response = await axios.post('/api/auth/register', userData);
      const { access_token, user: newUser } = response.data;
      
      token.value = access_token;
      user.value = newUser;
      localStorage.setItem('token', access_token);
      
      // Set default auth header
      axios.defaults.headers.common['Authorization'] = `Bearer ${access_token}`;
      
      return { success: true };
    } catch (err) {
      error.value = err.response?.data?.detail || 'Registration failed';
      return { success: false, error: error.value };
    } finally {
      isLoading.value = false;
    }
  };

  const fetchUser = async () => {
    if (!token.value) return;
    
    isLoading.value = true;
    error.value = null;
    try {
      const response = await axios.get('/api/auth/me');
      user.value = response.data;
      return { success: true };
    } catch (err) {
      error.value = err.response?.data?.detail || 'Failed to fetch user';
      // If token is invalid, logout
      if (err.response?.status === 401) {
        logout();
      }
      return { success: false, error: error.value };
    } finally {
      isLoading.value = false;
    }
  };

  const updateProfile = async (profileData) => {
    isLoading.value = true;
    error.value = null;
    try {
      const response = await axios.put('/api/auth/profile', profileData);
      user.value = response.data;
      return { success: true };
    } catch (err) {
      error.value = err.response?.data?.detail || 'Failed to update profile';
      return { success: false, error: error.value };
    } finally {
      isLoading.value = false;
    }
  };

  // Initialize auth state
  const initAuth = () => {
    if (token.value) {
      axios.defaults.headers.common['Authorization'] = `Bearer ${token.value}`;
      fetchUser();
    }
  };

  return {
    // State
    user,
    token,
    isLoading,
    error,
    
    // Getters
    isAuthenticated,
    currentUser,
    
    // Actions
    login,
    logout,
    register,
    fetchUser,
    updateProfile,
    initAuth
  };
});