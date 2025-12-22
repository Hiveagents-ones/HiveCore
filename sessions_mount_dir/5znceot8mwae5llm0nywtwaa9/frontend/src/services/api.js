import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
});

apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('access_token');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

export const membershipAPI = {
  async getMembershipStatus() {
    try {
      const response = await apiClient.get('/api/membership/status');
      return response.data;
    } catch (error) {
      throw new Error(error.response?.data?.detail || 'Failed to fetch membership status');
    }
  },

  async getMembershipPlans() {
    try {
      const response = await apiClient.get('/api/membership/plans');
      return response.data;
    } catch (error) {
      throw new Error(error.response?.data?.detail || 'Failed to fetch membership plans');
    }
  },

  async subscribeToPlan(planId) {
    try {
      const response = await apiClient.post('/api/membership/subscribe', { plan_id: planId });
      return response.data;
    } catch (error) {
      throw new Error(error.response?.data?.detail || 'Failed to subscribe to plan');
    }
  },

  async cancelMembership() {
    try {
      const response = await apiClient.post('/api/membership/cancel');
      return response.data;
    } catch (error) {
      throw new Error(error.response?.data?.detail || 'Failed to cancel membership');
    }
  },

  async getMembershipHistory() {
    try {
      const response = await apiClient.get('/api/membership/history');
      return response.data;
    } catch (error) {
      throw new Error(error.response?.data?.detail || 'Failed to fetch membership history');
    }
  }
};

export const paymentAPI = {
  async createPaymentIntent(planId) {
    try {
      const response = await apiClient.post('/api/payment/create-intent', { plan_id: planId });
      return response.data;
    } catch (error) {
      throw new Error(error.response?.data?.detail || 'Failed to create payment intent');
    }
  },

  async confirmPayment(paymentIntentId) {
    try {
      const response = await apiClient.post('/api/payment/confirm', { payment_intent_id: paymentIntentId });
      return response.data;
    } catch (error) {
      throw new Error(error.response?.data?.detail || 'Failed to confirm payment');
    }
  },

  async getPaymentHistory() {
    try {
      const response = await apiClient.get('/api/payment/history');
      return response.data;
    } catch (error) {
      throw new Error(error.response?.data?.detail || 'Failed to fetch payment history');
    }
  },

  async refundPayment(paymentId) {
    try {
      const response = await apiClient.post('/api/payment/refund', { payment_id: paymentId });
      return response.data;
    } catch (error) {
      throw new Error(error.response?.data?.detail || 'Failed to process refund');
    }
  }
};

export const userAPI = {
  async getUserProfile() {
    try {
      const response = await apiClient.get('/api/user/profile');
      return response.data;
    } catch (error) {
      throw new Error(error.response?.data?.detail || 'Failed to fetch user profile');
    }
  },

  async updateUserProfile(profileData) {
    try {
      const response = await apiClient.put('/api/user/profile', profileData);
      return response.data;
    } catch (error) {
      throw new Error(error.response?.data?.detail || 'Failed to update user profile');
    }
  },

  async changePassword(passwordData) {
    try {
      const response = await apiClient.post('/api/user/change-password', passwordData);
      return response.data;
    } catch (error) {
      throw new Error(error.response?.data?.detail || 'Failed to change password');
    }
  }
};

export default {
  membership: membershipAPI,
  payment: paymentAPI,
  user: userAPI
};