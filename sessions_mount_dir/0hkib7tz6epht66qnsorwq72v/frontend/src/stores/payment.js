import { defineStore } from 'pinia';
import { ref } from 'vue';
import {
  getPaymentMethods,
  createPayment,
  getPaymentStatus,
  getPaymentHistory,
  requestRefund,
  verifyPaymentCallback,
  cancelPayment,
} from '@/api/payment';

export const usePaymentStore = defineStore('payment', {
  state: () => ({
    paymentMethods: [],
    selectedPaymentMethod: null,
    currentPayment: null,
    paymentHistory: [],
    paymentHistoryPagination: {
      page: 1,
      limit: 10,
      total: 0,
    },
    loading: false,
    error: null,
  }),

  getters: {
    getPaymentMethodById: (state) => (id) => {
      return state.paymentMethods.find(method => method.id === id);
    },
    
    getPaymentById: (state) => (id) => {
      return state.paymentHistory.find(payment => payment.id === id);
    },

    hasActivePayment: (state) => {
      return state.currentPayment && state.currentPayment.status === 'pending';
    },
  },

  actions: {
    async fetchPaymentMethods() {
      this.loading = true;
      this.error = null;
      try {
        const methods = await getPaymentMethods();
        this.paymentMethods = methods;
      } catch (error) {
        this.error = error.message || '获取支付方式失败';
        throw error;
      } finally {
        this.loading = false;
      }
    },

    async createPaymentOrder(paymentData) {
      this.loading = true;
      this.error = null;
      try {
        const payment = await createPayment(paymentData);
        this.currentPayment = payment;
        return payment;
      } catch (error) {
        this.error = error.message || '创建支付订单失败';
        throw error;
      } finally {
        this.loading = false;
      }
    },

    async checkPaymentStatus(paymentId) {
      this.loading = true;
      this.error = null;
      try {
        const status = await getPaymentStatus(paymentId);
        if (this.currentPayment && this.currentPayment.id === paymentId) {
          this.currentPayment = { ...this.currentPayment, ...status };
        }
        return status;
      } catch (error) {
        this.error = error.message || '查询支付状态失败';
        throw error;
      } finally {
        this.loading = false;
      }
    },

    async fetchPaymentHistory(params = {}) {
      this.loading = true;
      this.error = null;
      try {
        const { page = 1, limit = 10 } = params;
        const response = await getPaymentHistory({ page, limit });
        this.paymentHistory = response.items || [];
        this.paymentHistoryPagination = {
          page: response.page || page,
          limit: response.limit || limit,
          total: response.total || 0,
        };
        return response;
      } catch (error) {
        this.error = error.message || '获取支付历史失败';
        throw error;
      } finally {
        this.loading = false;
      }
    },

    async submitRefundRequest(refundData) {
      this.loading = true;
      this.error = null;
      try {
        const result = await requestRefund(refundData);
        // 更新支付历史中的相关记录
        const paymentIndex = this.paymentHistory.findIndex(
          p => p.id === refundData.payment_id
        );
        if (paymentIndex !== -1) {
          this.paymentHistory[paymentIndex] = {
            ...this.paymentHistory[paymentIndex],
            refund_status: 'pending',
          };
        }
        return result;
      } catch (error) {
        this.error = error.message || '申请退款失败';
        throw error;
      } finally {
        this.loading = false;
      }
    },

    async verifyCallback(callbackData) {
      this.loading = true;
      this.error = null;
      try {
        const result = await verifyPaymentCallback(callbackData);
        if (this.currentPayment && this.currentPayment.id === result.payment_id) {
          this.currentPayment = { ...this.currentPayment, ...result };
        }
        return result;
      } catch (error) {
        this.error = error.message || '验证支付回调失败';
        throw error;
      } finally {
        this.loading = false;
      }
    },

    async cancelPaymentOrder(paymentId) {
      this.loading = true;
      this.error = null;
      try {
        const result = await cancelPayment(paymentId);
        if (this.currentPayment && this.currentPayment.id === paymentId) {
          this.currentPayment = null;
        }
        return result;
      } catch (error) {
        this.error = error.message || '取消支付订单失败';
        throw error;
      } finally {
        this.loading = false;
      }
    },

    clearCurrentPayment() {
      this.currentPayment = null;
    },

    clearError() {
      this.error = null;
    },
  },
});