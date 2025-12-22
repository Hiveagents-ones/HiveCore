import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import { useRouter } from 'vue-router';
import axios from 'axios';

export const useAuthStore = defineStore('auth', () => {
  const router = useRouter();
  const token = ref(localStorage.getItem('token') || null);
  const user = ref(JSON.parse(localStorage.getItem('user') || 'null'));
  const permissions = ref(JSON.parse(localStorage.getItem('permissions') || '[]'));

  const isAuthenticated = computed(() => !!token.value);
  const userRole = computed(() => user.value?.role || null);
  const hasPermission = computed(() => (permission) => permissions.value.includes(permission));

  const login = async (credentials) => {
    try {
      const response = await axios.post('/api/auth/login', credentials);
      const { token: newToken, user: userData, permissions: userPermissions } = response.data;
      
      token.value = newToken;
      user.value = userData;
      permissions.value = userPermissions;
      
      localStorage.setItem('token', newToken);
      localStorage.setItem('user', JSON.stringify(userData));
      localStorage.setItem('permissions', JSON.stringify(userPermissions));
      
      axios.defaults.headers.common['Authorization'] = `Bearer ${newToken}`;
      
      return { success: true };
    } catch (error) {
      console.error('Login failed:', error);
      return { success: false, error: error.response?.data?.message || 'Login failed' };
    }
  };

  const logout = () => {
    token.value = null;
    user.value = null;
    permissions.value = [];
    
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    localStorage.removeItem('permissions');
    
    delete axios.defaults.headers.common['Authorization'];
    
    router.push('/login');
  };

  const refreshToken = async () => {
    try {
      const response = await axios.post('/api/auth/refresh');
      const { token: newToken } = response.data;
      
      token.value = newToken;
      localStorage.setItem('token', newToken);
      axios.defaults.headers.common['Authorization'] = `Bearer ${newToken}`;
      
      return true;
    } catch (error) {
      console.error('Token refresh failed:', error);
      logout();
      return false;
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
    permissions,
    isAuthenticated,
    userRole,
    hasPermission,
    login,
    logout,
    refreshToken,
    initializeAuth
  };
});