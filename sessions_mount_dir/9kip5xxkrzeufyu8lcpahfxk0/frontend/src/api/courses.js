import axios from 'axios';

const API_BASE_URL = '/api/v1';

/**
 * 获取所有课程列表
 * @returns {Promise<Array>} 课程列表
 */
export const getCourses = async () => {

/**
 * 获取课程详情
 * @param {number} courseId 课程ID
 * @returns {Promise<Object>} 课程详情
 */
export const getCourseDetails = async (courseId) => {
  try {
    const response = await axios.get(`${API_BASE_URL}/courses/${courseId}`);
    return response.data;
  } catch (error) {
    console.error('Error fetching course details:', error);
    throw error;
  }
};
  try {
    const response = await axios.get(`${API_BASE_URL}/courses`);
    return response.data;
  } catch (error) {
    console.error('Error fetching courses:', error);
    throw error;
  }
};

/**
 * 获取课程安排
 * @param {Object} params 查询参数
 * @param {string} [params.coachId] 教练ID
 * @param {string} [params.startDate] 开始日期
 * @param {string} [params.endDate] 结束日期
 * @param {string} [params.status] 课程状态
 * @returns {Promise<Array>} 课程安排列表
 */
export const getCourseSchedules = async (params = {}) => {

/**
 * 获取课程安排详情
 * @param {number} scheduleId 安排ID
 * @returns {Promise<Object>} 课程安排详情
 */
export const getScheduleDetails = async (scheduleId) => {
  try {
    const response = await axios.get(`${API_BASE_URL}/courses/schedule/${scheduleId}`);
    return response.data;
  } catch (error) {
    console.error('Error fetching schedule details:', error);
    throw error;
  }
};
  try {
    const response = await axios.get(`${API_BASE_URL}/courses/schedule`, { params });
    return response.data;
  } catch (error) {
    console.error('Error fetching course schedules:', error);
    throw error;
  }
};

/**
 * 预约课程
 * @param {number} courseId 课程ID
 * @param {number} memberId 会员ID
 * @returns {Promise<Object>} 预约结果
 */
export const bookCourse = async (courseId, memberId) => {
  try {
    const response = await axios.post(`${API_BASE_URL}/courses/${courseId}/bookings`, { member_id: memberId });
    return response.data;
  } catch (error) {
    console.error('Error booking course:', error);
    throw error;
  }
};

/**
 * 取消预约
 * @param {number} bookingId 预约ID
 * @returns {Promise<Object>} 取消结果
 */
export const cancelBooking = async (bookingId) => {
  try {
    const response = await axios.delete(`${API_BASE_URL}/courses/bookings/${bookingId}`);
    return response.data;
  } catch (error) {
    console.error('Error canceling booking:', error);
    throw error;
  }
};

/**
 * 获取会员的课程预约记录
 * @param {number} memberId 会员ID
 * @returns {Promise<Array>} 预约记录列表
 */
export const getMemberBookings = async (memberId) => {
/**
 * 获取会员的课程预约记录
 * @param {number} memberId 会员ID
 * @param {string} [status] 预约状态
 * @returns {Promise<Array>} 预约记录列表
 */


/**
 * 获取预约详情
 * @param {number} bookingId 预约ID
 * @returns {Promise<Object>} 预约详情
 */
export const getBookingDetails = async (bookingId) => {
  try {
    const response = await axios.get(`${API_BASE_URL}/courses/bookings/${bookingId}`);
    return response.data;
  } catch (error) {
    console.error('Error fetching booking details:', error);
    throw error;
  }
};
  try {
    const response = await axios.get(`${API_BASE_URL}/members/${memberId}/bookings`);
    return response.data;
  } catch (error) {
    console.error('Error fetching member bookings:', error);
    throw error;
  }
};
/**
 * 获取课程评价
 * @param {number} courseId 课程ID
 * @returns {Promise<Array>} 评价列表
 */
export const getCourseReviews = async (courseId) => {
  try {
    const response = await axios.get(`${API_BASE_URL}/courses/${courseId}/reviews`);
    return response.data;
  } catch (error) {
    console.error('Error fetching course reviews:', error);
    throw error;
  }
};

/**
 * 提交课程评价
 * @param {number} courseId 课程ID
 * @param {number} memberId 会员ID
 * @param {Object} reviewData 评价数据
 * @param {string} reviewData.content 评价内容
 * @param {number} reviewData.rating 评分
 * @returns {Promise<Object>} 提交结果
 */
export const submitCourseReview = async (courseId, memberId, reviewData) => {
/**
 * 更新预约状态
 * @param {number} bookingId 预约ID
 * @param {string} status 新状态
 * @returns {Promise<Object>} 更新结果
 */
export const updateBookingStatus = async (bookingId, status) => {
/**
 * 获取课程类型
 * @returns {Promise<Array>} 课程类型列表
 */
export const getCourseTypes = async () => {
  try {
    const response = await axios.get(`${API_BASE_URL}/courses/types`);
    return response.data;
  } catch (error) {
    console.error('Error fetching course types:', error);
    throw error;
  }
};
  try {
    const response = await axios.patch(`${API_BASE_URL}/courses/bookings/${bookingId}`, { status });
    return response.data;
  } catch (error) {
    console.error('Error updating booking status:', error);
    throw error;
  }
};
  try {
    const response = await axios.post(
      `${API_BASE_URL}/courses/${courseId}/reviews`,
      { ...reviewData, member_id: memberId }
    );
    return response.data;
  } catch (error) {
    console.error('Error submitting course review:', error);
    throw error;
  }
};