import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

// Performance monitoring wrapper
const withPerformanceMonitoring = async (apiCall, operationName) => {
  const startTime = performance.now();
  try {
    const response = await apiCall;
    const endTime = performance.now();
    const duration = endTime - startTime;
    
    // Log performance metrics
    console.log(`[Performance] ${operationName}: ${duration.toFixed(2)}ms`);
    
    // Send metrics to monitoring endpoint
    if (import.meta.env.PROD) {
      axios.post(`${API_BASE_URL}/metrics/performance`, {
        operation: operationName,
        duration: duration,
        timestamp: new Date().toISOString(),
        status: 'success'
      }).catch(err => console.warn('Failed to send performance metrics:', err));
    }
    
    return response;
  } catch (error) {
    const endTime = performance.now();
    const duration = endTime - startTime;
    
    console.error(`[Performance] ${operationName} failed after ${duration.toFixed(2)}ms:`, error);
    
    if (import.meta.env.PROD) {
      axios.post(`${API_BASE_URL}/metrics/performance`, {
        operation: operationName,
        duration: duration,
        timestamp: new Date().toISOString(),
        status: 'error',
        error: error.message
      }).catch(err => console.warn('Failed to send performance metrics:', err));
    }
    
    throw error;
  }
};

// Payment API endpoints
export const paymentAPI = {
  // Get payment history for a member
  getPaymentHistory: async (memberId) => {
    return withPerformanceMonitoring(
      axios.get(`${API_BASE_URL}/api/payments/history/${memberId}`),
      'getPaymentHistory'
    );
  },

  // Process a new payment
  processPayment: async (paymentData) => {
    return withPerformanceMonitoring(
      axios.post(`${API_BASE_URL}/api/payments/process`, paymentData),
      'processPayment'
    );
  },

  // Get payment status
  getPaymentStatus: async (paymentId) => {
    return withPerformanceMonitoring(
      axios.get(`${API_BASE_URL}/api/payments/status/${paymentId}`),
      'getPaymentStatus'
    );
  },

  // Get upcoming renewal reminders
  getRenewalReminders: async (memberId) => {
    return withPerformanceMonitoring(
      axios.get(`${API_BASE_URL}/api/payments/reminders/${memberId}`),
      'getRenewalReminders'
    );
  },

  // Record offline payment
  recordOfflinePayment: async (paymentData) => {
    return withPerformanceMonitoring(
      axios.post(`${API_BASE_URL}/api/payments/offline`, paymentData),
      'recordOfflinePayment'
    );
  },

  // Get payment methods
  getPaymentMethods: async () => {
    return withPerformanceMonitoring(
      axios.get(`${API_BASE_URL}/api/payments/methods`),
      'getPaymentMethods'
    );
  },

  // Refund payment
  refundPayment: async (paymentId, refundData) => {
    return withPerformanceMonitoring(
      axios.post(`${API_BASE_URL}/api/payments/refund/${paymentId}`, refundData),
      'refundPayment'
    );
  },

  // Get payment analytics
  getPaymentAnalytics: async (filters = {}) => {
    return withPerformanceMonitoring(
      axios.get(`${API_BASE_URL}/api/payments/analytics`, { params: filters }),
      'getPaymentAnalytics'
    );
  }
};

// Export default for convenience
export default paymentAPI;