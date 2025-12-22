import axios from 'axios';

const API_BASE_URL = '/api/v1';

/**
 * 获取所有支付记录
 * @returns {Promise<Array>} 支付记录列表
 */
export const getPayments = async () => {
  try {
    const response = await axios.get(`${API_BASE_URL}/payments`);
    return response.data;
  } catch (error) {
    console.error('Error fetching payments:', error);
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
    const response = await axios.get(`${API_BASE_URL}/payments/${paymentId}`);
    return response.data;
  } catch (error) {
    console.error(`Error fetching payment with ID ${paymentId}:`, error);
    throw error;
  }
};

/**
 * 创建新的支付记录
 * @param {Object} paymentData 支付数据
 * @param {number} paymentData.member_id 会员ID
 * @param {number} paymentData.amount 支付金额
 * @param {string} paymentData.payment_type 支付类型
 * @returns {Promise<Object>} 新创建的支付记录
 */
export const createPayment = async (paymentData) => {
  try {
    const response = await axios.post(`${API_BASE_URL}/payments`, paymentData);
    return response.data;
  } catch (error) {
    console.error('Error creating payment:', error);
    throw error;
  }
};

/**
 * 获取会员的支付记录
 * @param {number} memberId 会员ID
 * @returns {Promise<Array>} 该会员的支付记录列表
 */
export const getPaymentsByMemberId = async (memberId) => {

/**
 * 更新支付记录
 * @param {number} paymentId 支付记录ID
 * @param {Object} updateData 更新数据
 * @returns {Promise<Object>} 更新后的支付记录
 */
export const updatePayment = async (paymentId, updateData) => {

/**
 * 删除支付记录
 * @param {number} paymentId 支付记录ID
 * @returns {Promise<Object>} 删除操作结果
 */
export const deletePayment = async (paymentId) => {
  try {
    const response = await axios.delete(`${API_BASE_URL}/payments/${paymentId}`);
    return response.data;
  } catch (error) {
    console.error(`Error deleting payment with ID ${paymentId}:`, error);
    throw error;
  }
};
  try {
    const response = await axios.put(`${API_BASE_URL}/payments/${paymentId}`, updateData);
    return response.data;
  } catch (error) {
    console.error(`Error updating payment with ID ${paymentId}:`, error);
    throw error;
  }
};
  try {
    const response = await axios.get(`${API_BASE_URL}/payments`, {
      params: { member_id: memberId }
    });
    return response.data;
  } catch (error) {
    console.error(`Error fetching payments for member ${memberId}:`, error);
    throw error;
  }
};
  try {
    const response = await axios.get(`${API_BASE_URL}/payments`, {
      params: { member_id: memberId }
    });
    return response.data;
  } catch (error) {
    console.error(`Error fetching payments for member ${memberId}:`, error);
    throw error;
  }
};

export default {
  getPayments,
  getPaymentById,
  createPayment,
  getPaymentsByMemberId,
  updatePayment,
  deletePayment
};