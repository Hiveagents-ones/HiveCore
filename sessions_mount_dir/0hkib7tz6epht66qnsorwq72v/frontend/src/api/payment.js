import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';

/**
 * 获取支付方式列表
 * @returns {Promise<Array>} 支付方式列表
 */
export const getPaymentMethods = async () => {
  try {
    const response = await axios.get(`${API_BASE_URL}/payments/methods`);
    return response.data;
  } catch (error) {
    console.error('获取支付方式失败:', error);
    throw error;
  }
};

/**
 * 创建支付订单
 * @param {Object} paymentData - 支付数据
 * @param {string} paymentData.membership_plan_id - 会籍计划ID
 * @param {string} paymentData.payment_method - 支付方式 (alipay/wechat/stripe)
 * @param {number} paymentData.amount - 支付金额
 * @param {string} paymentData.currency - 货币类型
 * @returns {Promise<Object>} 支付订单信息
 */
export const createPayment = async (paymentData) => {
  try {
    const response = await axios.post(`${API_BASE_URL}/payments/create`, paymentData);
    return response.data;
  } catch (error) {
    console.error('创建支付订单失败:', error);
    throw error;
  }
};

/**
 * 查询支付状态
 * @param {string} paymentId - 支付ID
 * @returns {Promise<Object>} 支付状态信息
 */
export const getPaymentStatus = async (paymentId) => {
  try {
    const response = await axios.get(`${API_BASE_URL}/payments/${paymentId}/status`);
    return response.data;
  } catch (error) {
    console.error('查询支付状态失败:', error);
    throw error;
  }
};

/**
 * 获取用户支付历史
 * @param {Object} params - 查询参数
 * @param {number} params.page - 页码
 * @param {number} params.limit - 每页数量
 * @returns {Promise<Object>} 支付历史列表
 */
export const getPaymentHistory = async (params = {}) => {
  try {
    const response = await axios.get(`${API_BASE_URL}/payments/history`, { params });
    return response.data;
  } catch (error) {
    console.error('获取支付历史失败:', error);
    throw error;
  }
};

/**
 * 申请退款
 * @param {Object} refundData - 退款数据
 * @param {string} refundData.payment_id - 支付ID
 * @param {number} refundData.amount - 退款金额
 * @param {string} refundData.reason - 退款原因
 * @returns {Promise<Object>} 退款申请结果
 */
export const requestRefund = async (refundData) => {
  try {
    const response = await axios.post(`${API_BASE_URL}/payments/refund`, refundData);
    return response.data;
  } catch (error) {
    console.error('申请退款失败:', error);
    throw error;
  }
};

/**
 * 验证支付回调
 * @param {Object} callbackData - 回调数据
 * @returns {Promise<Object>} 验证结果
 */
export const verifyPaymentCallback = async (callbackData) => {
  try {
    const response = await axios.post(`${API_BASE_URL}/payments/verify`, callbackData);
    return response.data;
  } catch (error) {
    console.error('验证支付回调失败:', error);
    throw error;
  }
};

/**
 * 取消支付订单
 * @param {string} paymentId - 支付ID
 * @returns {Promise<Object>} 取消结果
 */
export const cancelPayment = async (paymentId) => {
  try {
    const response = await axios.post(`${API_BASE_URL}/payments/${paymentId}/cancel`);
    return response.data;
  } catch (error) {
    console.error('取消支付订单失败:', error);
    throw error;
  }
};

/**
 * 获取支付详情
 * @param {string} paymentId - 支付ID
 * @returns {Promise<Object>} 支付详情
 */
export const getPaymentDetails = async (paymentId) => {
  try {
    const response = await axios.get(`${API_BASE_URL}/payments/${paymentId}`);
    return response.data;
  } catch (error) {
    console.error('获取支付详情失败:', error);
    throw error;
  }
};

/**
 * 获取会员计划列表
 * @returns {Promise<Array>} 会员计划列表
 */
export const getMembershipPlans = async () => {
  try {
    const response = await axios.get(`${API_BASE_URL}/membership/plans`);
    return response.data;
  } catch (error) {
    console.error('获取会员计划失败:', error);
    throw error;
  }
};

/**
 * 购买会员计划
 * @param {Object} planData - 购买数据
 * @param {string} planData.plan_id - 计划ID
 * @param {string} planData.payment_method - 支付方式
 * @returns {Promise<Object>} 购买结果
 */
export const purchaseMembership = async (planData) => {
  try {
    const response = await axios.post(`${API_BASE_URL}/membership/purchase`, planData);
    return response.data;
  } catch (error) {
    console.error('购买会员计划失败:', error);
    throw error;
  }
};

/**
 * 获取当前会员信息
 * @returns {Promise<Object>} 会员信息
 */
export const getCurrentMembership = async () => {
  try {
    const response = await axios.get(`${API_BASE_URL}/membership/current`);
    return response.data;
  } catch (error) {
    console.error('获取会员信息失败:', error);
    throw error;
  }
};

/**
 * 升级会员计划
 * @param {Object} upgradeData - 升级数据
 * @param {string} upgradeData.target_plan_id - 目标计划ID
 * @param {string} upgradeData.payment_method - 支付方式
 * @returns {Promise<Object>} 升级结果
 */
export const upgradeMembership = async (upgradeData) => {
  try {
    const response = await axios.post(`${API_BASE_URL}/membership/upgrade`, upgradeData);
    return response.data;
  } catch (error) {
    console.error('升级会员计划失败:', error);
    throw error;
  }
};

/**
 * 续费会员
 * @param {Object} renewalData - 续费数据
 * @param {string} renewalData.payment_method - 支付方式
 * @returns {Promise<Object>} 续费结果
 */
export const renewMembership = async (renewalData) => {
  try {
    const response = await axios.post(`${API_BASE_URL}/membership/renew`, renewalData);
    return response.data;
  } catch (error) {
    console.error('续费会员失败:', error);
    throw error;
  }
};

// 默认导出所有方法
export default {
  // 支付相关
  getPaymentMethods,
  createPayment,
  getPaymentStatus,
  getPaymentHistory,
  requestRefund,
  verifyPaymentCallback,
  cancelPayment,
  getPaymentDetails,
  // 会员相关
  getMembershipPlans,
  purchaseMembership,
  getCurrentMembership,
  upgradeMembership,
  renewMembership
};
