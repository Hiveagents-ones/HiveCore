import { defineStore } from 'pinia';
import { paymentAPI } from '../api/payment';

export const usePaymentStore = defineStore('payment', {
  state: () => ({
    paymentHistory: [],
    paymentDetails: null,
    paymentStats: null,
    paymentMethods: [],
    loading: false,
    error: null,
  }),

  getters: {
    getPaymentHistory: (state) => state.paymentHistory,
    getPaymentDetails: (state) => state.paymentDetails,
    getPaymentStats: (state) => state.paymentStats,
    getPaymentMethods: (state) => state.paymentMethods,
    isLoading: (state) => state.loading,
    getError: (state) => state.error,
  },

  actions: {
    async fetchPaymentHistory(memberId, params = {}) {
      this.loading = true;
      this.error = null;
      try {
        const response = await paymentAPI.getPaymentHistory(memberId, params);
        this.paymentHistory = response.data || [];
      } catch (error) {
        this.error = error.message || 'Failed to fetch payment history';
        console.error('Store Error:', this.error);
      } finally {
        this.loading = false;
      }
    },

    async recordPayment(paymentData) {
      this.loading = true;
      this.error = null;
      try {
        const response = await paymentAPI.recordPayment(paymentData);
        return response;
      } catch (error) {
        this.error = error.message || 'Failed to record payment';
        console.error('Store Error:', this.error);
        throw error;
      } finally {
        this.loading = false;
      }
    },

    async fetchPaymentDetails(paymentId) {
      this.loading = true;
      this.error = null;
      try {
        const response = await paymentAPI.getPaymentDetails(paymentId);
        this.paymentDetails = response.data;
      } catch (error) {
        this.error = error.message || 'Failed to fetch payment details';
        console.error('Store Error:', this.error);
      } finally {
        this.loading = false;
      }
    },

    async updatePaymentStatus(paymentId, status) {
      this.loading = true;
      this.error = null;
      try {
        const response = await paymentAPI.updatePaymentStatus(paymentId, status);
        return response;
      } catch (error) {
        this.error = error.message || 'Failed to update payment status';
        console.error('Store Error:', this.error);
        throw error;
      } finally {
        this.loading = false;
      }
    },

    async fetchPaymentStats(params = {}) {
      this.loading = true;
      this.error = null;
      try {
        const response = await paymentAPI.getPaymentStats(params);
        this.paymentStats = response.data;
      } catch (error) {
        this.error = error.message || 'Failed to fetch payment statistics';
        console.error('Store Error:', this.error);
      } finally {
        this.loading = false;
      }
    },

    async exportPayments(params = {}) {
      this.loading = true;
      this.error = null;
      try {
        const response = await paymentAPI.exportPayments(params);
        return response;
      } catch (error) {
        this.error = error.message || 'Failed to export payments';
        console.error('Store Error:', this.error);
        throw error;
      } finally {
        this.loading = false;
      }
    },

    async fetchPaymentMethods() {
      this.loading = true;
      this.error = null;
      try {
        const response = await paymentAPI.getPaymentMethods();
        this.paymentMethods = response.data || [];
      } catch (error) {
        this.error = error.message || 'Failed to fetch payment methods';
        console.error('Store Error:', this.error);
      } finally {
        this.loading = false;
      }
    },

    async processRefund(paymentId, refundData) {
      this.loading = true;
      this.error = null;
      try {
        const response = await paymentAPI.processRefund(paymentId, refundData);
        return response;
      } catch (error) {
        this.error = error.message || 'Failed to process refund';
        console.error('Store Error:', this.error);
        throw error;
      } finally {
        this.loading = false;
      }
    },

    clearError() {
      this.error = null;
    },
  },
});
