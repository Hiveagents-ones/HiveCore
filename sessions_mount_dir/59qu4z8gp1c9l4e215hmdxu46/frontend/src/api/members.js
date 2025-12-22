import axios from 'axios';
import { handleResponse, handleError } from './utils';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api/v1';
const DEFAULT_FIELDS = ['id', 'name', 'phone', 'email', 'join_date', 'gender', 'birth_date', 'address', 'status', 'notes'];
const DEFAULT_PER_PAGE = 20;
const DEFAULT_SORT_FIELD = 'join_date';
const DEFAULT_SORT_ORDER = 'desc';

/**
 * 获取会员列表
 * @param {Object} params - 查询参数
 * @returns {Promise} - 包含会员列表的Promise
 */
export const getMembers = (params = {}) => {
  return axios
    .get(`${API_BASE_URL}/members`, { 
      params: {
        ...params,
        _fields: (params.fields || DEFAULT_FIELDS).join(','),
        _per_page: params.per_page || DEFAULT_PER_PAGE,
        _sort: params.sort || DEFAULT_SORT_FIELD,
        _order: params.order || DEFAULT_SORT_ORDER,
        _cache: params.cache !== false,
        _expand: params.expand ? params.expand.join(',') : undefined
      }
    })
    .then(handleResponse)
    .catch(handleError);
};

/**
 * 创建新会员
 * @param {Object} memberData - 会员数据
 * @returns {Promise} - 包含新会员信息的Promise
 */
export const createMember = (memberData) => {
  return axios
    .post(`${API_BASE_URL}/members`, memberData)
    .then(handleResponse)
    .catch(handleError);
};

/**
 * 更新会员信息
 * @param {Number} memberId - 会员ID
 * @param {Object} memberData - 更新的会员数据
 * @returns {Promise} - 包含更新结果的Promise
 */
export const updateMember = (memberId, memberData) => {
  return axios
    .put(`${API_BASE_URL}/members/${memberId}`, memberData)
    .then(handleResponse)
    .catch(handleError);
};

/**
 * 删除会员
 * @param {Number} memberId - 会员ID
 * @returns {Promise} - 包含删除结果的Promise
 */
export const deleteMember = (memberId) => {
  return axios
    .delete(`${API_BASE_URL}/members/${memberId}`)
    .then(handleResponse)
    .catch(handleError);
};

/**
 * 获取会员卡信息
 * @param {Number} memberId - 会员ID
 * @returns {Promise} - 包含会员卡信息的Promise
 */
export const getMemberCards = (memberId, params = {}) => {

  return axios
    .get(`${API_BASE_URL}/members/${memberId}/cards`, { 
      params: {
        ...params,
        _fields: (params.fields || ['id', 'card_number', 'status', 'expiry_date', 'balance', 'points', 'card_type', 'issue_date']).join(','),
        _sort: params.sort || 'expiry_date',
        _order: params.order || 'desc',
        _cache: params.cache !== false
      }
    })
    .then(handleResponse)
    .catch(handleError);
};

/**
 * 更新会员卡信息
 * @param {Number} memberId - 会员ID
 * @param {Number} cardId - 会员卡ID
 * @param {Object} cardData - 更新的会员卡数据
 * @returns {Promise} - 包含更新结果的Promise
 */
export const updateMemberCard = (memberId, cardId, cardData) => {
  return axios
    .put(`${API_BASE_URL}/members/${memberId}/cards/${cardId}`, cardData, {
      params: {
        _fields: ['id', 'card_number', 'status', 'expiry_date', 'balance', 'points'].join(',')
      }
    })
    .then(handleResponse)
    .catch(handleError);

/**
 * 获取会员等级信息
 * @param {Number} memberId - 会员ID
 * @returns {Promise} - 包含会员等级信息的Promise
 */
export const getMemberLevel = (memberId, params = {}) => {
  return axios
    .get(`${API_BASE_URL}/members/${memberId}/level`, { 
      params: {
        ...params,
        _fields: (params.fields || ['id', 'level_name', 'discount_rate', 'upgrade_points']).join(','),
        _cache: true
      }
    })
    .then(handleResponse)
    .catch(handleError);
};

/**
 * 更新会员等级
 * @param {Number} memberId - 会员ID
 * @param {Object} levelData - 更新的等级数据
 * @returns {Promise} - 包含更新结果的Promise
 */
export const updateMemberLevel = (memberId, levelData) => {
  return axios
    .put(`${API_BASE_URL}/members/${memberId}/level`, levelData, {
      params: {
        _fields: ['id', 'level_name', 'discount_rate', 'upgrade_points', 'current_points'].join(',')
      }
    })
    .then(handleResponse)
    .catch(handleError);

};

/**
 * 获取会员审计日志
 * @param {Number} memberId - 会员ID
 * @param {Object} params - 查询参数
 * @returns {Promise} - 包含审计日志的Promise
 */
export const getMemberAuditLogs = (memberId, params = {}) => {
  return axios
    .get(`${API_BASE_URL}/members/${memberId}/audit-logs`, { 
      params: {
        ...params,
        _fields: (params.fields || ['id', 'action', 'timestamp', 'changed_by', 'old_value', 'new_value', 'entity_type']).join(','),
        _per_page: params.per_page || DEFAULT_PER_PAGE,
        _sort: params.sort || 'timestamp',
        _order: params.order || 'desc',
        _cache: params.cache !== false
      }
    })
    .then(handleResponse)
    .catch(handleError);


};

