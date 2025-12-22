import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';

/**
 * 预约API调用模块
 * 提供与预约相关的所有API接口调用
 */
export const bookingApi = {
  /**
   * 获取用户预约列表
   * @param {Object} params - 查询参数
   * @param {number} params.page - 页码
   * @param {number} params.size - 每页数量
   * @param {string} params.status - 预约状态
   * @returns {Promise} 预约列表数据
   */
  getBookings(params = {}) {
    return axios.get(`${API_BASE_URL}/bookings`, { params });
  },

  /**
   * 创建新预约
   * @param {Object} bookingData - 预约数据
   * @param {number} bookingData.course_id - 课程ID
   * @param {string} bookingData.booking_date - 预约日期
   * @param {string} bookingData.booking_time - 预约时间
   * @param {string} bookingData.notes - 备注信息
   * @returns {Promise} 创建的预约数据
   */
  createBooking(bookingData) {
    return axios.post(`${API_BASE_URL}/bookings`, bookingData);
  },

  /**
   * 获取单个预约详情
   * @param {number} bookingId - 预约ID
   * @returns {Promise} 预约详情数据
   */
  getBookingById(bookingId) {
    return axios.get(`${API_BASE_URL}/bookings/${bookingId}`);
  },

  /**
   * 更新预约信息
   * @param {number} bookingId - 预约ID
   * @param {Object} updateData - 更新数据
   * @returns {Promise} 更新后的预约数据
   */
  updateBooking(bookingId, updateData) {
    return axios.put(`${API_BASE_URL}/bookings/${bookingId}`, updateData);
  },

  /**
   * 取消预约
   * @param {number} bookingId - 预约ID
   * @returns {Promise} 操作结果
   */
  cancelBooking(bookingId) {
    return axios.delete(`${API_BASE_URL}/bookings/${bookingId}`);
  },

  /**
   * 获取课程可用时间段
   * @param {number} courseId - 课程ID
   * @param {string} date - 查询日期
   * @returns {Promise} 可用时间段列表
   */
  getAvailableSlots(courseId, date) {
    return axios.get(`${API_BASE_URL}/courses/${courseId}/available-slots`, {
      params: { date }
    });
  },

  /**
   * 批量取消预约
   * @param {Array<number>} bookingIds - 预约ID列表
   * @returns {Promise} 操作结果
   */
  batchCancelBookings(bookingIds) {
    return axios.post(`${API_BASE_URL}/bookings/batch-cancel`, {
      booking_ids: bookingIds
    });
  },

  /**
   * 获取预约统计信息
   * @param {Object} params - 查询参数
   * @param {string} params.start_date - 开始日期
   * @param {string} params.end_date - 结束日期
   * @returns {Promise} 统计数据
   */
  getBookingStats(params = {}) {
    return axios.get(`${API_BASE_URL}/bookings/stats`, { params });
  }
};

export default bookingApi;