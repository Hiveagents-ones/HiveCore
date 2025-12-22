import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const coursesApi = {
  // 获取所有课程
  async getCourses() {
    try {
      const response = await apiClient.get('/api/v1/courses');
      return response.data;
    } catch (error) {
      console.error('Error fetching courses:', error);
      throw error;
    }
  },

  // 获取单个课程详情
  async getCourseById(courseId) {
    try {
      const response = await apiClient.get(`/api/v1/courses/${courseId}`);
      return response.data;
    } catch (error) {
      console.error('Error fetching course:', error);
      throw error;
    }
  },

  // 创建新课程
  async createCourse(courseData) {
    try {
      const response = await apiClient.post('/api/v1/courses', courseData);
      return response.data;
    } catch (error) {
      console.error('Error creating course:', error);
      throw error;
    }
  },

  // 更新课程信息
  async updateCourse(courseId, courseData) {
    try {
      const response = await apiClient.put(`/api/v1/courses/${courseId}`, courseData);
      return response.data;
    } catch (error) {
      console.error('Error updating course:', error);
      throw error;
    }
  },

  // 删除课程
  async deleteCourse(courseId) {
    try {
      const response = await apiClient.delete(`/api/v1/courses/${courseId}`);
      return response.data;
    } catch (error) {
      console.error('Error deleting course:', error);
      throw error;
    }
  },

  // 获取课程的预约列表
  async getCourseBookings(courseId) {
    try {
      const response = await apiClient.get(`/api/v1/courses/${courseId}/bookings`);
      return response.data;
    } catch (error) {
      console.error('Error fetching course bookings:', error);
      throw error;
    }
  },

  // 预约课程
  async bookCourse(courseId, memberId) {
    try {
      const response = await apiClient.post(`/api/v1/courses/${courseId}/bookings`, {
        member_id: memberId,
      });
      return response.data;
    } catch (error) {
      console.error('Error booking course:', error);
      throw error;
    }
  },

  // 取消预约
  async cancelBooking(courseId, bookingId) {
    try {
      const response = await apiClient.delete(`/api/v1/courses/${courseId}/bookings/${bookingId}`);
      return response.data;
    } catch (error) {
      console.error('Error canceling booking:', error);
      throw error;
    }
  },
};

export default coursesApi;
