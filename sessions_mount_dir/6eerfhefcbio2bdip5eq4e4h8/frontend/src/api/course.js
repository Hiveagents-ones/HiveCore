import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';

/**
 * 课程API调用模块
 * 提供与课程相关的所有API接口调用功能
 */
export const courseApi = {
  /**
   * 获取所有课程列表
   * @returns {Promise} 课程列表数据
   */
  async getCourses() {
    try {
      const response = await axios.get(`${API_BASE_URL}/courses`);
      return response.data;
    } catch (error) {
      console.error('获取课程列表失败:', error);
      throw error;
    }
  },

  /**
   * 根据ID获取单个课程详情
   * @param {number} courseId - 课程ID
   * @returns {Promise} 课程详情数据
   */
  async getCourseById(courseId) {
    try {
      const response = await axios.get(`${API_BASE_URL}/courses/${courseId}`);
      return response.data;
    } catch (error) {
      console.error('获取课程详情失败:', error);
      throw error;
    }
  },

  /**
   * 创建新课程
   * @param {Object} courseData - 课程数据
   * @returns {Promise} 创建的课程数据
   */
  async createCourse(courseData) {
    try {
      const response = await axios.post(`${API_BASE_URL}/courses`, courseData);
      return response.data;
    } catch (error) {
      console.error('创建课程失败:', error);
      throw error;
    }
  },

  /**
   * 更新课程信息
   * @param {number} courseId - 课程ID
   * @param {Object} courseData - 更新的课程数据
   * @returns {Promise} 更新后的课程数据
   */
  async updateCourse(courseId, courseData) {
    try {
      const response = await axios.put(`${API_BASE_URL}/courses/${courseId}`, courseData);
      return response.data;
    } catch (error) {
      console.error('更新课程失败:', error);
      throw error;
    }
  },

  /**
   * 删除课程
   * @param {number} courseId - 课程ID
   * @returns {Promise} 删除结果
   */
  async deleteCourse(courseId) {
    try {
      const response = await axios.delete(`${API_BASE_URL}/courses/${courseId}`);
      return response.data;
    } catch (error) {
      console.error('删除课程失败:', error);
      throw error;
    }
  },

  /**
   * 获取课程表
   * @param {Object} params - 查询参数
   * @returns {Promise} 课程表数据
   */
  async getSchedule(params = {}) {
    try {
      const response = await axios.get(`${API_BASE_URL}/courses/schedule`, { params });
      return response.data;
    } catch (error) {
      console.error('获取课程表失败:', error);
      throw error;
    }
  },

  /**
   * 预约课程
   * @param {number} courseId - 课程ID
   * @returns {Promise} 预约结果
   */
  async bookCourse(courseId) {
    try {
      const response = await axios.post(`${API_BASE_URL}/courses/${courseId}/book`);
      return response.data;
    } catch (error) {
      console.error('预约课程失败:', error);
      throw error;
    }
  },

  /**
   * 取消预约
   * @param {number} courseId - 课程ID
   * @returns {Promise} 取消结果
   */
  async cancelBooking(courseId) {
    try {
      const response = await axios.delete(`${API_BASE_URL}/courses/${courseId}/book`);
      return response.data;
    } catch (error) {
      console.error('取消预约失败:', error);
      throw error;
    }
  },

  /**
   * 获取教练列表
   * @returns {Promise} 教练列表数据
   */
  async getCoaches() {
    try {
      const response = await axios.get(`${API_BASE_URL}/coaches`);
      return response.data;
    } catch (error) {
      console.error('获取教练列表失败:', error);
      throw error;
    }
  },

  /**
   * 获取教练的课程
   * @param {number} coachId - 教练ID
   * @returns {Promise} 教练的课程列表
   */
  async getCoachCourses(coachId) {
    try {
      const response = await axios.get(`${API_BASE_URL}/coaches/${coachId}/courses`);
      return response.data;
    } catch (error) {
      console.error('获取教练课程失败:', error);
      throw error;
    }
  }
};

export default courseApi;