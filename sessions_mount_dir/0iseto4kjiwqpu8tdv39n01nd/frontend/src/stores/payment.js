import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import axios from 'axios';

export const usePaymentStore = defineStore('payment', () => {
  // State
  const orderInfo = ref(null);
  const paymentStatus = ref('idle'); // idle, processing, success, failed
  const paymentMethod = ref('');
  const transactionHistory = ref([]);
  const loading = ref(false);
  const error = ref(null);

  // Getters
  const isPaymentProcessing = computed(() => paymentStatus.value === 'processing');
  const isPaymentSuccessful = computed(() => paymentStatus.value === 'success');
  const isPaymentFailed = computed(() => paymentStatus.value === 'failed');
  const hasOrderInfo = computed(() => orderInfo.value !== null);

  // Actions
  const setOrderInfo = (info) => {
    orderInfo.value = info;
  };

  const setPaymentMethod = (method) => {
    paymentMethod.value = method;
  };

  const initiatePayment = async (orderId) => {
    try {
      loading.value = true;
      error.value = null;
      paymentStatus.value = 'processing';

      const response = await axios.post('/api/v1/payment/initiate', {
        order_id: orderId,
        payment_method: paymentMethod.value,
      });

      if (response.data.success) {
        // Handle different payment gateway responses
        switch (paymentMethod.value) {
          case 'alipay':
            window.location.href = response.data.payment_url;
            break;
          case 'wechat':
            // WeChat Pay typically requires QR code display
            orderInfo.value = { ...orderInfo.value, qrCode: response.data.qr_code };
            break;
          case 'stripe':
            // Stripe requires client-side confirmation
            const stripe = Stripe(response.data.stripe_public_key);
            const { error: stripeError } = await stripe.confirmCardPayment(response.data.client_secret);
            if (stripeError) {
              throw new Error(stripeError.message);
            }
            paymentStatus.value = 'success';
            break;
          default:
            throw new Error('Unsupported payment method');
        }
      } else {
        throw new Error(response.data.message || 'Payment initiation failed');
      }
    } catch (err) {
      error.value = err.message || 'Payment failed';
      paymentStatus.value = 'failed';
    } finally {
      loading.value = false;
    }
  };

  const verifyPayment = async (paymentId) => {
    try {
      loading.value = true;
      error.value = null;

      const response = await axios.post('/api/v1/payment/verify', {
        payment_id: paymentId,
      });

      if (response.data.success) {
        paymentStatus.value = 'success';
        orderInfo.value = { ...orderInfo.value, ...response.data.order_info };
      } else {
        throw new Error(response.data.message || 'Payment verification failed');
      }
    } catch (err) {
      error.value = err.message || 'Payment verification failed';
      paymentStatus.value = 'failed';
    } finally {
      loading.value = false;
    }
  };

  const fetchTransactionHistory = async () => {
    try {
      loading.value = true;
      error.value = null;

      const response = await axios.get('/api/v1/payment/transactions');
      transactionHistory.value = response.data.transactions || [];
    } catch (err) {
      error.value = err.message || 'Failed to fetch transaction history';
    } finally {
      loading.value = false;
    }
  };

  const resetPaymentState = () => {
    orderInfo.value = null;
    paymentStatus.value = 'idle';
    paymentMethod.value = '';
    error.value = null;
  };

  return {
    // State
    orderInfo,
    paymentStatus,
    paymentMethod,
    transactionHistory,
    loading,
    error,

    // Getters
    isPaymentProcessing,
    isPaymentSuccessful,
    isPaymentFailed,
    hasOrderInfo,

    // Actions
    setOrderInfo,
    setPaymentMethod,
    initiatePayment,
    verifyPayment,
    fetchTransactionHistory,
    resetPaymentState,
  };
});