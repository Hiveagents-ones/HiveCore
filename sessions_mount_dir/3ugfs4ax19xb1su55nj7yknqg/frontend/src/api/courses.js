import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

/**
 * 课程API客户端
 */
export default {
  /**
   * 获取所有课程列表
   * @returns {Promise<Array>} 课程列表
   */
  async getAllCourses() {
  /**
   * 获取热门课程
   * @returns {Promise<Array>} 热门课程列表
   */
  async getPopularCourses() {
    try {
      const response = await axios.get(`${API_BASE_URL}/api/v1/courses/popular`);
      return response.data;
    } catch (error) {
      console.error('Error fetching popular courses:', error);
      throw error;
    }
  },
    try {
      const response = await axios.get(`${API_BASE_URL}/api/v1/courses`);
      return response.data;
    } catch (error) {
      console.error('Error fetching courses:', error);
      throw error;
    }
  },

  /**
   * 获取单个课程详情
   * @param {number} courseId 课程ID
   * @returns {Promise<Object>} 课程详情
   */
  async getCourseById(courseId) {
    try {
      const response = await axios.get(`${API_BASE_URL}/api/v1/courses/${courseId}`);
      return response.data;
    } catch (error) {
      console.error(`Error fetching course ${courseId}:`, error);
      throw error;
    }
  },

  /**
   * 预约课程
   * @param {number} courseId 课程ID
   * @param {number} memberId 会员ID
   * @returns {Promise<Object>} 预约结果
   */
  async bookCourse(courseId, memberId) {
    try {
      const response = await axios.post(
        `${API_BASE_URL}/api/v1/courses/${courseId}/book`,
        { member_id: memberId }
      );
      return response.data;
    } catch (error) {
      console.error(`Error booking course ${courseId}:`, error);
      throw error;
    }
  },

  /**
   * 获取教练排班
   * @param {number} coachId 教练ID
   * @returns {Promise<Array>} 排班列表
   */
  async getCoachSchedule(coachId) {
  /**
   * 取消预约
   * @param {number} bookingId 预约ID
   * @returns {Promise<Object>} 取消结果
   */
  async cancelBooking(bookingId) {
    try {
      const response = await axios.delete(`${API_BASE_URL}/api/v1/bookings/${bookingId}`);
      return response.data;
    } catch (error) {
      console.error(`Error canceling booking ${bookingId}:`, error);
      throw error;
    }
  },

  /**
   * 获取会员的课程预约记录
   * @param {number} memberId 会员ID
   * @returns {Promise<Array>} 预约记录列表
   */
  async getMemberBookings(memberId) {
    try {
      const response = await axios.get(`${API_BASE_URL}/api/v1/members/${memberId}/bookings`);
      return response.data;
    } catch (error) {
      console.error(`Error fetching bookings for member ${memberId}:`, error);
      throw error;
    }
  },

  /**
   * 获取所有教练列表
   * @returns {Promise<Array>} 教练列表
   */
  async getAllCoaches() {
    try {
      const response = await axios.get(`${API_BASE_URL}/api/v1/coaches`);
      return response.data;
    } catch (error) {
      console.error('Error fetching coaches:', error);
      throw error;
    }
  },
    try {
      const response = await axios.get(`${API_BASE_URL}/api/v1/coaches/${coachId}/schedule`);
      return response.data;
    } catch (error) {
      console.error(`Error fetching schedule for coach ${coachId}:`, error);
      throw error;
    }
  }
};