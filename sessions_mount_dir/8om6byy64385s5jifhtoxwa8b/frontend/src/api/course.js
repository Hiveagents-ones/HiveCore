import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// 获取课程列表
export const getCourses = async () => {
  try {
    const response = await apiClient.get('/courses');
    return response.data;
  } catch (error) {
    console.error('Error fetching courses:', error);
    throw error;
  }
};

// 获取单个课程详情
export const getCourse = async (courseId) => {
  try {
    const response = await apiClient.get(`/courses/${courseId}`);
    return response.data;
  } catch (error) {
    console.error('Error fetching course:', error);
    throw error;
  }
};

// 预约课程
export const bookCourse = async (courseId, userId) => {
  try {
    const response = await apiClient.post(`/courses/${courseId}/book`, {
      user_id: userId,
    });
    return response.data;
  } catch (error) {
    console.error('Error booking course:', error);
    throw error;
  }
};

// 取消预约课程
export const cancelBooking = async (courseId, userId) => {
  try {
    const response = await apiClient.post(`/courses/${courseId}/cancel`, {
      user_id: userId,
    });
    return response.data;
  } catch (error) {
    console.error('Error canceling booking:', error);
    throw error;
  }
};

// 获取用户的预约记录
export const getUserBookings = async (userId) => {
  try {
    const response = await apiClient.get(`/users/${userId}/bookings`);
    return response.data;
  } catch (error) {
    console.error('Error fetching user bookings:', error);
    throw error;
  }
};

// 创建课程
export const createCourse = async (courseData) => {
  try {
    const response = await apiClient.post('/courses', courseData);
    return response.data;
  } catch (error) {
    console.error('Error creating course:', error);
    throw error;
  }
};

// 更新课程
export const updateCourse = async (courseId, courseData) => {
  try {
    const response = await apiClient.put(`/courses/${courseId}`, courseData);
    return response.data;
  } catch (error) {
    console.error('Error updating course:', error);
    throw error;
  }
};

// 删除课程
export const deleteCourse = async (courseId) => {
  try {
    const response = await apiClient.delete(`/courses/${courseId}`);
    return response.data;
  } catch (error) {
    console.error('Error deleting course:', error);
    throw error;
  }
};

// 创建排课
export const createSchedule = async (scheduleData) => {
  try {
    const response = await apiClient.post('/schedules', scheduleData);
    return response.data;
  } catch (error) {
    console.error('Error creating schedule:', error);
    throw error;
  }
};

// 更新排课
export const updateSchedule = async (scheduleId, scheduleData) => {
  try {
    const response = await apiClient.put(`/schedules/${scheduleId}`, scheduleData);
    return response.data;
  } catch (error) {
    console.error('Error updating schedule:', error);
    throw error;
  }
};

// 删除排课
export const deleteSchedule = async (scheduleId) => {
  try {
    const response = await apiClient.delete(`/schedules/${scheduleId}`);
    return response.data;
  } catch (error) {
    console.error('Error deleting schedule:', error);
    throw error;
  }
};

// 获取课程排课列表
export const getCourseSchedules = async (courseId) => {
  try {
    const response = await apiClient.get(`/courses/${courseId}/schedules`);
    return response.data;
  } catch (error) {
    console.error('Error fetching course schedules:', error);
    throw error;
  }
};

export default {
  getCourses,
  getCourse,
  bookCourse,
  cancelBooking,
  getUserBookings,
  createCourse,
  updateCourse,
  deleteCourse,
  createSchedule,
  updateSchedule,
  deleteSchedule,
  getCourseSchedules,
};