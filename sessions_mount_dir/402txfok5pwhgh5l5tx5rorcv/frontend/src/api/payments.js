import axios from 'axios';

// 支付方式枚举
export const PaymentMethod = {
  ALIPAY: 'alipay',
  WECHAT: 'wechat'
};


const API_BASE_URL = '/api/v1';

/**
 * 支付API调用封装
 * 提供支付相关接口的调用方法
 */
export const paymentsApi = {
  /**
   * 创建支付订单
   * @param {Object} paymentData - 支付数据
   * @param {number} paymentData.member_id - 会员ID
   * @param {number} paymentData.amount - 支付金额
   * @param {string} paymentData.type - 支付类型 (membership|private_course|course_booking)
   * @param {number} [paymentData.course_id] - 课程ID（当type为private_course或course_booking时需要）
   * @returns {Promise<Object>} 支付订单信息
   */
  async createPayment(paymentData) {
    try {
      const response = await axios.post(`${API_BASE_URL}/payments`, paymentData);
      return response.data;
    } catch (error) {
      console.error('创建支付订单失败:', error);
      throw error;
    }
  },

  /**
   * 创建支付订单并获取支付链接
   * @param {Object} paymentData - 支付数据
   * @param {number} paymentData.member_id - 会员ID
   * @param {number} paymentData.amount - 支付金额
   * @param {string} paymentData.type - 支付类型 (membership|private_course|course_booking)
   * @param {number} [paymentData.course_id] - 课程ID（当type为private_course或course_booking时需要）
   * @param {string} paymentData.method - 支付方式 (alipay|wechat)
   * @returns {Promise<Object>} 包含支付链接的订单信息
   */
  async createPaymentWithUrl(paymentData) {
    try {
      const response = await axios.post(`${API_BASE_URL}/payments/create`, paymentData);
      return response.data;
    } catch (error) {
      console.error('创建支付订单失败:', error);
      throw error;
    }
  },

  /**
   * 验证支付结果
   * @param {number} paymentId - 支付ID
   * @returns {Promise<Object>} 验证结果
   */
  async verifyPayment(paymentId) {
    try {
      const response = await axios.post(`${API_BASE_URL}/payments/${paymentId}/verify`);
      return response.data;
    } catch (error) {
      console.error('验证支付结果失败:', error);
      throw error;
    }
  },

  /**
   * 获取支付历史记录
   * @param {Object} params - 查询参数
   * @param {number} [params.member_id] - 会员ID（可选）
   * @param {string} [params.status] - 支付状态过滤（可选）
   * @param {number} [params.page=1] - 页码
   * @param {number} [params.size=10] - 每页数量
   * @returns {Promise<Object>} 支付历史列表
   */
  async getPaymentHistory(params = {}) {
    try {
      const response = await axios.get(`${API_BASE_URL}/payments`, {
        params: {
          page: params.page || 1,
          size: params.size || 10,
          ...params
        }
      });
      return response.data;
    } catch (error) {
      console.error('获取支付历史失败:', error);
      throw error;
    }
  },

  /**
   * 获取单个支付详情
   * @param {number} paymentId - 支付ID
   * @returns {Promise<Object>} 支付详情
   */
  async getPaymentDetail(paymentId) {
    try {
      const response = await axios.get(`${API_BASE_URL}/payments/${paymentId}`);
      return response.data;
    } catch (error) {
      console.error('获取支付详情失败:', error);
      throw error;
    }
  },

  /**
   * 取消支付
   * @param {number} paymentId - 支付ID
   * @returns {Promise<Object>} 取消结果
   */
  async cancelPayment(paymentId) {
    try {
      const response = await axios.put(`${API_BASE_URL}/payments/${paymentId}/cancel`);
      return response.data;
    } catch (error) {
      console.error('取消支付失败:', error);
      throw error;
    }
  },

  /**
   * 获取支付状态
   * @param {number} paymentId - 支付ID
   * @returns {Promise<Object>} 支付状态
   */
  async getPaymentStatus(paymentId) {
    try {
      const response = await axios.get(`${API_BASE_URL}/payments/${paymentId}/status`);
      return response.data;
    } catch (error) {
      console.error('获取支付状态失败:', error);
      throw error;
    }
  }
};

/**
 * 支付类型枚举
 */
export const PaymentType = {
  MEMBERSHIP: 'membership',
  PRIVATE_COURSE: 'private_course',
  COURSE_BOOKING: 'course_booking'
};

/**
 * 支付状态枚举
 */
export const PaymentStatus = {
  PENDING: 'pending',
  SUCCESS: 'success',
  FAILED: 'failed',
  CANCELLED: 'cancelled'
};

export default paymentsApi;