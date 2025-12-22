import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

const memberApi = {
  /**
   * 获取会员列表
   * @param {Object} params - 查询参数
   * @param {number} params.page - 页码
   * @param {number} params.size - 每页数量
   * @param {string} [params.search] - 搜索关键词
   * @param {string} [params.status] - 会员状态筛选
   * @returns {Promise} 会员列表数据
   */
  getMembers(params = {}) {
    return axios.get(`${API_BASE_URL}/api/v1/members`, { params });
  },

  /**
   * 根据ID获取会员详情
   * @param {number} id - 会员ID
   * @returns {Promise} 会员详情数据
   */
  getMemberById(id) {
    return axios.get(`${API_BASE_URL}/api/v1/members/${id}`);
  },

  /**
   * 创建新会员
   * @param {Object} memberData - 会员数据
   * @param {string} memberData.name - 姓名
   * @param {string} memberData.phone - 联系方式
   * @param {string} [memberData.email] - 邮箱
   * @param {string} memberData.card_number - 会员卡号
   * @param {string} memberData.level - 会员等级
   * @param {string} memberData.status - 会员状态
   * @returns {Promise} 创建的会员数据
   */
  createMember(memberData) {
    return axios.post(`${API_BASE_URL}/api/v1/members`, memberData);
  },

  /**
   * 更新会员信息
   * @param {number} id - 会员ID
   * @param {Object} memberData - 更新的会员数据
   * @returns {Promise} 更新后的会员数据
   */
  updateMember(id, memberData) {
    return axios.put(`${API_BASE_URL}/api/v1/members/${id}`, memberData);
  },

  /**
   * 删除会员
   * @param {number} id - 会员ID
   * @returns {Promise} 删除结果
   */
  deleteMember(id) {
    return axios.delete(`${API_BASE_URL}/api/v1/members/${id}`);
  },

  /**
   * 更新会员状态
   * @param {number} id - 会员ID
   * @param {string} status - 新状态
   * @returns {Promise} 更新结果
   */
  updateMemberStatus(id, status) {
    return axios.patch(`${API_BASE_URL}/api/v1/members/${id}/status`, { status });
  },

  /**
   * 根据会员卡号查询会员
   * @param {string} cardNumber - 会员卡号
   * @returns {Promise} 会员数据
   */
  getMemberByCardNumber(cardNumber) {
    return axios.get(`${API_BASE_URL}/api/v1/members/by-card/${cardNumber}`);
  },

  /**
   * 获取会员统计信息
   * @returns {Promise} 统计数据
   */
  getMemberStats() {
    return axios.get(`${API_BASE_URL}/api/v1/members/stats`);
  }
};

export default memberApi;
