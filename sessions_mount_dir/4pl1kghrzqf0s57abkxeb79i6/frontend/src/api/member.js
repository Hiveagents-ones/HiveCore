import axios from 'axios';

const API_BASE_URL = '/api/v1';

/**
 * 获取会员列表
 * @param {Object} params - 查询参数
 * @returns {Promise} 会员列表数据
 */
export const getMembers = (params) => {
  return axios.get(`${API_BASE_URL}/members`, { params });
};

/**
 * 创建新会员
 * @param {Object} data - 会员数据
 * @returns {Promise} 创建的会员信息
 */
export const createMember = (data) => {
  return axios.post(`${API_BASE_URL}/members`, data);
};

/**
 * 更新会员信息
 * @param {number} id - 会员ID
 * @param {Object} data - 更新的会员数据
 * @returns {Promise} 更新后的会员信息
 */
export const updateMember = (id, data) => {
  return axios.put(`${API_BASE_URL}/members/${id}`, data);
};

/**
 * 删除会员
 * @param {number} id - 会员ID
 * @returns {Promise} 删除结果
 */
export const deleteMember = (id) => {
  return axios.delete(`${API_BASE_URL}/members/${id}`);
};

/**
 * 批量导入会员
 * @param {FormData} formData - 包含文件的FormData
 * @returns {Promise} 导入结果
 */
export const batchImportMembers = (formData) => {
  return axios.post(`${API_BASE_URL}/members/batch`, formData, {
    headers: {
      'Content-Type': 'multipart/form-data'
    }
  });
};

/**
 * 批量导出会员
 * @param {Object} params - 导出条件
 * @returns {Promise} 导出文件
 */
export const batchExportMembers = (params) => {
  return axios.get(`${API_BASE_URL}/members/batch`, {
    params,
    responseType: 'blob'
  });
};

/**
 * 会员卡续费
 * @param {number} memberId - 会员ID
 * @param {Object} data - 续费信息
 * @returns {Promise} 续费结果
 */
export const renewMembership = (memberId, data) => {
  return axios.post(`${API_BASE_URL}/members/${memberId}/renew`, data);
};

/**
 * 获取会员详情
 * @param {number} id - 会员ID
 * @returns {Promise} 会员详细信息
 */
export const getMemberDetail = (id) => {
  return axios.get(`${API_BASE_URL}/members/${id}`);
};

/**
 * 获取会员入场记录
 * @param {number} id - 会员ID
 * @param {Object} params - 查询参数
 * @returns {Promise} 入场记录列表
 */
export const getMemberCheckInRecords = (id, params) => {
  return axios.get(`${API_BASE_URL}/members/${id}/checkins`, { params });
};

/**
 * 更新会员健身目标
 * @param {number} id - 会员ID
 * @param {Object} data - 健身目标数据
 * @returns {Promise} 更新结果
 */
export const updateMemberGoals = (id, data) => {
  return axios.put(`${API_BASE_URL}/members/${id}/goals`, data);
};

/**
 * 冻结/解冻会员
 * @param {number} id - 会员ID
 * @param {Object} data - 冻结信息
 * @returns {Promise} 操作结果
 */
export const toggleMemberStatus = (id, data) => {
  return axios.put(`${API_BASE_URL}/members/${id}/status`, data);
};

/**
 * 升级会员卡类型
 * @param {number} id - 会员ID
 * @param {Object} data - 升级信息
 * @returns {Promise} 升级结果
 */
export const upgradeMembership = (id, data) => {
  return axios.post(`${API_BASE_URL}/members/${id}/upgrade`, data);
};
