import axios from 'axios';
import { useAuthStore } from '@/stores/auth';

const API_BASE_URL = '/api/v1';
const authStore = useAuthStore();

/**
 * 获取所有支付记录
 * @returns {Promise<Array>} 支付记录列表
 */
export const getPayments = async () => {
  try {
    const response = await axios.get(`${API_BASE_URL}/payments`, {
      headers: { Authorization: `Bearer ${authStore.token}` }
    });
    return response.data;
  } catch (error) {
    console.error('Error fetching payments:', error);
    throw error;
  }
};

/**
 * 创建新的支付记录
 * @param {Object} paymentData 支付数据
 * @param {number} paymentData.member_id 会员ID
 * @param {number} paymentData.amount 支付金额
 * @param {string} paymentData.payment_method 支付方式
 * @returns {Promise<Object>} 新创建的支付记录
 */
export const createPayment = async (paymentData) => {
  try {
    const response = await axios.post(`${API_BASE_URL}/payments`, paymentData, {
      headers: { Authorization: `Bearer ${authStore.token}` }
    });
    return response.data;
  } catch (error) {
    console.error('Error creating payment:', error);
    throw error;
  }
};

/**
 * 获取单个支付记录详情
 * @param {number} paymentId 支付记录ID
 * @returns {Promise<Object>} 支付记录详情
 */
export const getPaymentById = async (paymentId) => {
  try {
    const response = await axios.get(`${API_BASE_URL}/payments/${paymentId}`, {
      headers: { Authorization: `Bearer ${authStore.token}` }
    });
    return response.data;
  } catch (error) {
    console.error(`Error fetching payment with ID ${paymentId}:`, error);
    throw error;
  }
};

/**
 * 更新支付记录
 * @param {number} paymentId 支付记录ID
 * @param {Object} updateData 更新数据
 * @returns {Promise<Object>} 更新后的支付记录
 */
export const updatePayment = async (paymentId, updateData) => {
  try {
    const response = await axios.put(`${API_BASE_URL}/payments/${paymentId}`, updateData, {
      headers: { Authorization: `Bearer ${authStore.token}` }
    });
    return response.data;
  } catch (error) {
    console.error(`Error updating payment with ID ${paymentId}:`, error);
    throw error;
  }
};

/**
 * 删除支付记录
 * @param {number} paymentId 支付记录ID
 * @returns {Promise<void>}
 */
export const deletePayment = async (paymentId) => {
  try {
    await axios.delete(`${API_BASE_URL}/payments/${paymentId}`, {
      headers: { Authorization: `Bearer ${authStore.token}` }
    });
  } catch (error) {
    console.error(`Error deleting payment with ID ${paymentId}:`, error);
    throw error;
  }
};

/**
 * 获取会员的支付记录
 * @param {number} memberId 会员ID
 * @returns {Promise<Array>} 该会员的支付记录列表
 */
export const getPaymentsByMemberId = async (memberId) => {
  try {
    const response = await axios.get(`${API_BASE_URL}/payments?member_id=${memberId}`, {
      headers: { Authorization: `Bearer ${authStore.token}` }
    });
    return response.data;
  } catch (error) {
    console.error(`Error fetching payments for member ${memberId}:`, error);
    throw error;
  }
};
/**
 * 获取支付统计数据
 * @returns {Promise<Object>} 支付统计数据
 */
export const getPaymentStats = async () => {
  try {
    const response = await axios.get(`${API_BASE_URL}/payments/stats`, {
      headers: { Authorization: `Bearer ${authStore.token}` }
    });
    return response.data;
  } catch (error) {
    console.error('Error fetching payment stats:', error);
    throw error;
  }
};