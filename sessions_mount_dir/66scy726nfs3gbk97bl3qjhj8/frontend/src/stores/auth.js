import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import axios from 'axios';
import router from '../router';

export const useAuthStore = defineStore('auth', () => {
  const token = ref(localStorage.getItem('token') || null);
  const user = ref(JSON.parse(localStorage.getItem('user') || 'null'));
  const isLoading = ref(false);
  const error = ref(null);

  const isAuthenticated = computed(() => !!token.value);

  const login = async (credentials) => {
    isLoading.value = true;
    error.value = null;
    try {
      const response = await axios.post('/api/auth/login', credentials);
      const { access_token, user: userData } = response.data;
      
      token.value = access_token;
      user.value = userData;
      
      localStorage.setItem('token', access_token);
      localStorage.setItem('user', JSON.stringify(userData));
      
      axios.defaults.headers.common['Authorization'] = `Bearer ${access_token}`;
      
      router.push('/dashboard');
    } catch (err) {
      error.value = err.response?.data?.detail || '登录失败';
      throw err;
    } finally {
      isLoading.value = false;
    }
  };

  const logout = () => {
    token.value = null;
    user.value = null;
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    delete axios.defaults.headers.common['Authorization'];
    router.push('/login');
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
      localStorage.setItem('user', JSON.stringify(newUser));
      
      axios.defaults.headers.common['Authorization'] = `Bearer ${access_token}`;
      
      router.push('/dashboard');
    } catch (err) {
      error.value = err.response?.data?.detail || '注册失败';
      throw err;
    } finally {
      isLoading.value = false;
    }
  };

  const refreshToken = async () => {
    if (!token.value) return;
    
    try {
      const response = await axios.post('/api/auth/refresh', {
        token: token.value
      });
      const { access_token } = response.data;
      
      token.value = access_token;
      localStorage.setItem('token', access_token);
      axios.defaults.headers.common['Authorization'] = `Bearer ${access_token}`;
    } catch (err) {
      logout();
    }
  };

  const initializeAuth = () => {
    if (token.value) {
      axios.defaults.headers.common['Authorization'] = `Bearer ${token.value}`;
    }
  };

  return {
    token,
    user,
    isLoading,
    error,
    isAuthenticated,
    login,
    logout,
    register,
    refreshToken,
    initializeAuth
  };
});