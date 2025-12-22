import axios from 'axios';
import { useAuthStore } from '@/stores/auth';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api/v1';

/**
 * 支付API客户端
 */
const paymentApi = {
  /**
   * 获取支付记录
   * @param {Object} params - 查询参数
   * @param {string} [params.memberId] - 会员ID
   * @param {string} [params.type] - 支付类型
   * @param {string} [params.startDate] - 开始日期
   * @param {string} [params.endDate] - 结束日期
   * @returns {Promise<Array>} 支付记录列表
   */
  async getPayments(params = {}) {
    try {
      const response = await axios.get(`${API_BASE_URL}/payments`, {
        params,
        headers: {
          Authorization: `Bearer ${useAuthStore().token}`
        }
      });
      return response.data;
    } catch (error) {
      console.error('获取支付记录失败:', error);
      throw error;
    }
  },

  /**
   * 创建支付记录
   * @param {Object} paymentData - 支付数据
   * @param {string} paymentData.memberId - 会员ID
   * @param {string} paymentData.type - 支付类型 (membership/course)
   * @param {number} paymentData.amount - 支付金额
   * @param {string} paymentData.paymentMethod - 支付方式
   * @param {string} [paymentData.description] - 支付描述
   * @param {string} [paymentData.referenceId] - 关联ID (会员卡ID或课程ID)
   * @returns {Promise<Object>} 创建的支付记录
   */
  async createPayment(paymentData) {
    try {
      const response = await axios.post(`${API_BASE_URL}/payments`, paymentData, {
        headers: {
          Authorization: `Bearer ${useAuthStore().token}`
        }
      });
      return response.data;
    } catch (error) {
      console.error('创建支付记录失败:', error);
      throw error;
    }
  },

  /**
   * 获取支付详情
   * @param {string} paymentId - 支付记录ID
   * @returns {Promise<Object>} 支付详情
   */
  async getPaymentDetail(paymentId) {
    try {
      const response = await axios.get(`${API_BASE_URL}/payments/${paymentId}`, {
        headers: {
          Authorization: `Bearer ${useAuthStore().token}`
        }
      });
      return response.data;
    } catch (error) {
      console.error('获取支付详情失败:', error);
      throw error;
    }
  },

  /**
   * 更新支付记录
   * @param {string} paymentId - 支付记录ID
   * @param {Object} updates - 更新数据
   * @returns {Promise<Object>} 更新后的支付记录
   */
  async updatePayment(paymentId, updates) {
    try {
      const response = await axios.put(`${API_BASE_URL}/payments/${paymentId}`, updates, {
        headers: {
          Authorization: `Bearer ${useAuthStore().token}`
        }
      });
      return response.data;
    } catch (error) {
      console.error('更新支付记录失败:', error);
      throw error;
    }
  },
,

  /**
   * 获取会员支付记录
   * @param {string} memberId - 会员ID
   * @returns {Promise<Array>} 会员支付记录列表
   */
  async getMemberPayments(memberId) {
,
,

  /**
   * 获取支付统计数据
   * @param {Object} params - 查询参数
   * @param {string} [params.type] - 支付类型
   * @param {string} [params.startDate] - 开始日期
   * @param {string} [params.endDate] - 结束日期
   * @returns {Promise<Object>} 支付统计数据
   */
  async getPaymentStats(params = {}) {
    try {
      const response = await axios.get(`${API_BASE_URL}/payments/stats`, {
        params,
        headers: {
          Authorization: `Bearer ${useAuthStore().token}`
        }
      });
      return response.data;
    } catch (error) {
      console.error('获取支付统计数据失败:', error);
      throw error;
    }
  },

  /**
   * 导出支付记录
   * @param {Object} params - 查询参数
   * @param {string} [params.memberId] - 会员ID
   * @param {string} [params.type] - 支付类型
   * @param {string} [params.startDate] - 开始日期
   * @param {string} [params.endDate] - 结束日期
   * @returns {Promise<Blob>} 导出的文件数据
   */
  async exportPayments(params = {}) {
    try {
      const response = await axios.get(`${API_BASE_URL}/members/${memberId}/payments`, {
        headers: {
          Authorization: `Bearer ${useAuthStore().token}`
        }
      });
      return response.data;
    } catch (error) {
      console.error('获取会员支付记录失败:', error);
      throw error;
    }
  }
    try {
      const response = await axios.get(`${API_BASE_URL}/payments/export`, {
        params,
        responseType: 'blob',
        headers: {
          Authorization: `Bearer ${useAuthStore().token}`
        }
      });
      return response.data;
    } catch (error) {
      console.error('导出支付记录失败:', error);
      throw error;
    }
  }

};

export default paymentApi;