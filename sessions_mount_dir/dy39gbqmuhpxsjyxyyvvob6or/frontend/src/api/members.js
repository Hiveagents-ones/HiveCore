import axios from 'axios';
import { handleApiError } from './errorHandler';
import { useAuthStore } from '../stores/auth';

const API_BASE_URL = process.env.VUE_APP_API_BASE_URL || '/api/v1';
const getAuthHeaders = () => {
  const authStore = useAuthStore();
  return {
    headers: {
      'Authorization': `Bearer ${authStore.token}`
    }
  };
};

/**
 * 获取所有会员列表
 * @returns {Promise<Array>} 会员列表
 */
export const getMembers = async () => {
  try {
    const response = await axios.get(`${API_BASE_URL}/members`, getAuthHeaders());
    return response.data;
  } catch (error) {
    return handleApiError(error, '获取会员列表失败');
  }
};

/**
 * 获取单个会员详情
 * @param {number} memberId 会员ID
 * @returns {Promise<Object>} 会员详情
 */
export const getMemberById = async (memberId) => {
  try {
    const response = await axios.get(`${API_BASE_URL}/members/${memberId}`, getAuthHeaders());
    return response.data;
  } catch (error) {
    return handleApiError(error, `获取会员ID ${memberId} 详情失败`);
  }
};

/**
 * 创建新会员
 * @param {Object} memberData 会员数据
 * @returns {Promise<Object>} 创建成功的会员数据
 */
export const createMember = async (memberData) => {
  try {
    const response = await axios.post(`${API_BASE_URL}/members`, memberData, getAuthHeaders());
    return response.data;
  } catch (error) {
    return handleApiError(error, '创建会员失败');
  }
};

/**
 * 更新会员信息
 * @param {number} memberId 会员ID
 * @param {Object} memberData 更新的会员数据
 * @returns {Promise<Object>} 更新后的会员数据
 */
export const updateMember = async (memberId, memberData) => {
  try {
    const response = await axios.put(`${API_BASE_URL}/members/${memberId}`, memberData, getAuthHeaders());
    return response.data;
  } catch (error) {
    return handleApiError(error, `更新会员ID ${memberId} 失败`);
  }
};

/**
 * 删除会员
 * @param {number} memberId 会员ID
 * @returns {Promise<void>}
 */
export const deleteMember = async (memberId) => {
  try {
    await axios.delete(`${API_BASE_URL}/members/${memberId}`, getAuthHeaders());
  } catch (error) {
    return handleApiError(error, `删除会员ID ${memberId} 失败`);
  }
};

/**
 * 获取会员的课程预约列表
 * @param {number} memberId 会员ID
 * @returns {Promise<Array>} 课程预约列表
 */
export const getMemberCourses = async (memberId) => {
  try {
    const response = await axios.get(`${API_BASE_URL}/members/${memberId}/courses`, getAuthHeaders());
    return response.data;
  } catch (error) {
    return handleApiError(error, `获取会员ID ${memberId} 的课程预约列表失败`);
  }
};

/**
 * 会员预约课程
 * @param {number} memberId 会员ID
 * @param {number} courseId 课程ID
 * @returns {Promise<Object>} 预约结果
 */
export const bookCourse = async (memberId, courseId) => {
  try {
    const response = await axios.post(`${API_BASE_URL}/members/${memberId}/courses`, { course_id: courseId }, getAuthHeaders());
    return response.data;
  } catch (error) {
    return handleApiError(error, `会员ID ${memberId} 预约课程ID ${courseId} 失败`);
  }
};

/**
 * 取消课程预约
 * @param {number} memberId 会员ID
 * @param {number} bookingId 预约ID
 * @returns {Promise<void>}
 */
export const cancelCourseBooking = async (memberId, bookingId) => {
  try {
    await axios.delete(`${API_BASE_URL}/members/${memberId}/courses/${bookingId}`, getAuthHeaders());
  } catch (error) {
    return handleApiError(error, `会员ID ${memberId} 取消预约ID ${bookingId} 失败`);
  }
};