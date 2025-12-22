import axios from 'axios';
import { i18n } from '@/i18n';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

/**
 * 获取所有课程列表
 * @returns {Promise<Array>} 课程列表
 */
export const getCourses = async () => {
  try {
    const response = await axios.get(`${API_BASE_URL}/api/v1/courses`);
    return response.data;
  } catch (error) {
    console.error('Error fetching courses:', error);
    throw new Error(`Failed to fetch courses: ${error.message}`);
  }
};

/**
 * 获取单个课程详情
 * @param {number} courseId 课程ID
 * @returns {Promise<Object>} 课程详情
 */
export const getCourseById = async (courseId) => {
  try {
    const response = await axios.get(`${API_BASE_URL}/api/v1/courses/${courseId}`);
    return response.data;
  } catch (error) {
    console.error(`Error fetching course with ID ${courseId}:`, error);
    throw new Error(`Failed to fetch course ${courseId}: ${error.message}`);
  }
};

/**
 * 创建课程预约
 * @param {Object} courseData 课程数据
 * @returns {Promise<Object>} 创建的课程
 */
export const createCourseBooking = async (courseData) => {
  try {
    const response = await axios.post(`${API_BASE_URL}/api/v1/courses`, courseData);
    return response.data;
  } catch (error) {
    console.error('Error creating course booking:', error);
    throw new Error(`Failed to create course booking: ${error.message}`);
  }
};

/**
 * 更新课程预约
 * @param {number} courseId 课程ID
 * @param {Object} courseData 更新的课程数据
 * @returns {Promise<Object>} 更新后的课程
 */
export const updateCourseBooking = async (courseId, courseData) => {
  try {
    const response = await axios.put(`${API_BASE_URL}/api/v1/courses/${courseId}`, courseData);
    return response.data;
  } catch (error) {
    console.error(`Error updating course with ID ${courseId}:`, error);
    throw new Error(`Failed to update course ${courseId}: ${error.message}`);
  }
};

/**
 * 取消课程预约
 * @param {number} courseId 课程ID
 * @returns {Promise<Object>} 删除结果
 */
export const cancelCourseBooking = async (courseId) => {
  try {
    const response = await axios.delete(`${API_BASE_URL}/api/v1/courses/${courseId}`);
    return response.data;
  } catch (error) {
    console.error(`Error canceling course with ID ${courseId}:`, error);
    throw new Error(`Failed to cancel course ${courseId}: ${error.message}`);
  }

/**
 * 获取会员的课程预约列表
 * @param {number} memberId 会员ID
 * @returns {Promise<Array>} 课程预约列表
 */
export const getMemberCourseBookings = async (memberId) => {
  try {
    const response = await axios.get(`${API_BASE_URL}/api/v1/members/${memberId}/courses`);
    return response.data;
  } catch (error) {
    console.error(`Error fetching course bookings for member ${memberId}:`, error);
    throw new Error(`Failed to fetch bookings for member ${memberId}: ${error.message}`);
  }

/**
 * 获取可预约的课程时间表
 * @param {string} date 查询日期 (YYYY-MM-DD)
 * @returns {Promise<Array>} 可预约课程时间表
 */
export const getAvailableCourseSchedules = async (date) => {

  try {
    const response = await axios.get(`${API_BASE_URL}/api/v1/courses/schedules`, {
      params: { date }
    });
    return response.data;
  } catch (error) {
    console.error('Error fetching available course schedules:', error);
    throw new Error(`Failed to fetch schedules for date ${date}: ${error.message}`);
  }
};

