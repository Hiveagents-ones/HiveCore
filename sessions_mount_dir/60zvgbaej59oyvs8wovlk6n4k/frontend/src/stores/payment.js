import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import { ElMessage } from 'element-plus';
import api from '../api';

// Payment gateway adapters
import { stripeAdapter } from '../adapters/stripe';
import { adyenAdapter } from '../adapters/adyen';

// Membership related imports
import { useMembershipStore } from './membership';

export const usePaymentStore = defineStore('payment', () => {
  // State
  const paymentHistory = ref([]);
  const currentPayment = ref(null);
  const loading = ref(false);
  const error = ref(null);
  const renewalReminder = ref(null);

  const paymentGateway = ref('stripe'); // Default payment gateway

  // Getters
  const hasPendingPayment = computed(() => {
    return currentPayment.value && currentPayment.value.status === 'pending';
  });

  const lastPayment = computed(() => {
    return paymentHistory.value.length > 0 ? paymentHistory.value[0] : null;
  });

  const isRenewalDue = computed(() => {
    if (!renewalReminder.value) return false;
    const daysUntilExpiry = renewalReminder.value.daysUntilExpiry;
    return daysUntilExpiry <= 30 && daysUntilExpiry > 0;
  });

  const getPaymentAdapter = computed(() => {
    return paymentGateway.value === 'stripe' ? stripeAdapter : adyenAdapter;
  });

  // Actions
  const fetchPaymentHistory = async () => {
    loading.value = true;
    error.value = null;
    try {
      const response = await api.get('/payments/history');
      paymentHistory.value = response.data;
    } catch (err) {
      error.value = err.message;
      ElMessage.error('Failed to fetch payment history');
    } finally {
      loading.value = false;
    }
  };

  const initiatePayment = async (paymentData) => {
    loading.value = true;
    error.value = null;
    try {
      const adapter = getPaymentAdapter.value;
      const gatewayResponse = await adapter.createPayment(paymentData);
      
      const response = await api.post('/payments/initiate', {
        ...paymentData,
        gatewayPaymentId: gatewayResponse.id,
        gateway: paymentGateway.value
      });
      
      currentPayment.value = response.data;
      ElMessage.success('Payment initiated successfully');
      return response.data;
    } catch (err) {
      error.value = err.message;
      ElMessage.error('Failed to initiate payment');
      throw err;
    } finally {
      loading.value = false;
    }
  };

  const confirmPayment = async (paymentId) => {
    loading.value = true;
    error.value = null;
    try {
      const response = await api.post(`/payments/confirm/${paymentId}`);
      currentPayment.value = response.data;
      await fetchPaymentHistory();
      ElMessage.success('Payment confirmed successfully');
      return response.data;
    } catch (err) {
      error.value = err.message;
      ElMessage.error('Failed to confirm payment');
      throw err;
    } finally {
      loading.value = false;
    }
  };

  const cancelPayment = async (paymentId) => {
    loading.value = true;
    error.value = null;
    try {
      const response = await api.post(`/payments/cancel/${paymentId}`);
      currentPayment.value = response.data;
      ElMessage.success('Payment cancelled successfully');
      return response.data;
    } catch (err) {
      error.value = err.message;
      ElMessage.error('Failed to cancel payment');
      throw err;
    } finally {
      loading.value = false;
    }
  };

  const fetchRenewalReminder = async () => {
    loading.value = true;
    error.value = null;
    try {
      const response = await api.get('/memberships/renewal-reminder');
      renewalReminder.value = response.data;
      
      // If renewal is due, show notification
      if (response.data && response.data.daysUntilExpiry <= 30) {
        const membershipStore = useMembershipStore();
        ElMessage.warning(`Your membership will expire in ${response.data.daysUntilExpiry} days. Please renew to continue enjoying benefits.`);
        await membershipStore.checkMembershipStatus();
      }
    } catch (err) {
      error.value = err.message;
      ElMessage.error('Failed to fetch renewal reminder');
    } finally {
      loading.value = false;
    }
  };

  const clearCurrentPayment = () => {
    currentPayment.value = null;
  };

  const clearError = () => {
    error.value = null;
  };

  const setPaymentGateway = (gateway) => {
    paymentGateway.value = gateway;
  };


  return {
    // State
    paymentHistory,
    currentPayment,
    loading,
    error,
    renewalReminder,
    paymentGateway,
    
    // Getters
    hasPendingPayment,
    lastPayment,
    isRenewalDue,
    getPaymentAdapter,
    
    // Actions
    fetchPaymentHistory,
    initiatePayment,
    confirmPayment,
    cancelPayment,
    fetchRenewalReminder,
    renewMembership,
    clearCurrentPayment,
    clearError,
    setPaymentGateway
  };
});

# ========== AUTO-APPENDED CODE (编辑失败自动追加) ==========
# [AUTO-APPENDED] Failed to insert:

  const renewMembership = async () => {
    loading.value = true;
    error.value = null;
    try {
      const membershipStore = useMembershipStore();
      const currentPlan = membershipStore.currentMembership;
      
      if (!currentPlan) {
        throw new Error('No active membership found');
      }

      const paymentData = {
        amount: currentPlan.price,
        currency: currentPlan.currency,
        description: `Membership renewal - ${currentPlan.name}`,
        metadata: {
          type: 'membership_renewal',
          planId: currentPlan.id
        }
      };

      const response = await initiatePayment(paymentData);
      return response;
    } catch (err) {
      error.value = err.message;
      ElMessage.error('Failed to renew membership');
      throw err;
    } finally {
      loading.value = false;
    }
  };