import axios from 'axios';
import { retryRequest } from '@/utils/retry';
import { showErrorNotification } from '@/utils/notification';
import { logApiError } from '@/utils/logger';

const API_BASE_URL = '/api/v1';

/**
 * 会员API客户端
 */
export default {
  /**
   * 获取所有会员列表
   * @returns {Promise} Axios promise
   */
  getMembers() {
    return retryRequest(
      () => axios.get(`${API_BASE_URL}/members`),
      {
        maxRetries: 3,
        retryDelay: 1000,
        retryCondition: (error) => !error.response || error.response.status >= 500
      }
    )
      .catch(error => {
        logApiError('GET /members', error);
        showErrorNotification('获取会员列表失败', error);
        throw error;
      });
  },

  /**
   * 获取单个会员信息
   * @param {number} memberId 会员ID
   * @returns {Promise} Axios promise
   */
  getMember(memberId) {
    return retryRequest(
      () => axios.get(`${API_BASE_URL}/members/${memberId}`),
      {
        maxRetries: 3,
        retryDelay: 1000,
        retryCondition: (error) => !error.response || error.response.status >= 500
      }
    )
      .catch(error => {
        logApiError(`GET /members/${memberId}`, error);
        showErrorNotification('获取会员信息失败', error);
        throw error;
      });
  },

  /**
   * 创建新会员
   * @param {Object} memberData 会员数据
   * @returns {Promise} Axios promise
   */
  createMember(memberData) {
    return retryRequest(
      () => axios.post(`${API_BASE_URL}/members`, memberData),
      {
        maxRetries: 2,
        retryDelay: 1500,
        retryCondition: (error) => !error.response || error.response.status >= 500
      }
    )
      .catch(error => {
        logApiError('POST /members', error);
        showErrorNotification('创建会员失败', error);
        throw error;
      });
  },

  /**
   * 更新会员信息
   * @param {number} memberId 会员ID
   * @param {Object} memberData 更新的会员数据
   * @returns {Promise} Axios promise
   */
  updateMember(memberId, memberData) {
    return retryRequest(
      () => axios.put(`${API_BASE_URL}/members/${memberId}`, memberData),
      {
        maxRetries: 2,
        retryDelay: 1500,
        retryCondition: (error) => !error.response || error.response.status >= 500
      }
    )
      .catch(error => {
        logApiError(`PUT /members/${memberId}`, error);
        showErrorNotification('更新会员信息失败', error);
        throw error;
      });
  },

  /**
   * 删除会员
   * @param {number} memberId 会员ID
   * @returns {Promise} Axios promise
   */
  deleteMember(memberId) {
    return retryRequest(
      () => axios.delete(`${API_BASE_URL}/members/${memberId}`),
      {
        maxRetries: 2,
        retryDelay: 1500,
        retryCondition: (error) => !error.response || error.response.status >= 500
      }
    )
      .catch(error => {
        logApiError(`DELETE /members/${memberId}`, error);
        showErrorNotification('删除会员失败', error);
        throw error;
      });
  }
};