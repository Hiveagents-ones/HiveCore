import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

/**
 * 会员API客户端
 */
export default {
  /**
   * 获取所有会员列表
   * @returns {Promise} Axios promise
   */
  getAllMembers() {
    return axios.get(`${API_BASE_URL}/api/v1/members`);
  },

  /**
   * 获取单个会员详情
   * @param {number} id 会员ID
   * @returns {Promise} Axios promise
   */
  getMember(id) {
    return axios.get(`${API_BASE_URL}/api/v1/members/${id}`);
  },

  /**
   * 创建新会员
   * @param {Object} memberData 会员数据 {name, contact, level}
   * @returns {Promise} Axios promise
   */
  createMember(memberData) {
    return axios.post(`${API_BASE_URL}/api/v1/members`, memberData);
  },

  /**
   * 更新会员信息
   * @param {number} id 会员ID
   * @param {Object} memberData 更新的会员数据 {name, contact, level}
   * @returns {Promise} Axios promise
   */
  updateMember(id, memberData) {
    return axios.put(`${API_BASE_URL}/api/v1/members/${id}`, memberData);
  },

  /**
   * 删除会员
   * @param {number} id 会员ID
   * @returns {Promise} Axios promise
   */
  deleteMember(id) {
    return axios.delete(`${API_BASE_URL}/api/v1/members/${id}`);
  }
};
