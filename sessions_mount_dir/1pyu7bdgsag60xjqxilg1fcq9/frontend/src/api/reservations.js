import axios from 'axios';
import { handleResponse, handleError } from './utils';

const BASE_URL = '/api/v1';

const reservationsApi = {
  /**
   * 获取会员预约列表
   * @param {number} memberId - 会员ID
   * @returns {Promise} - 包含预约列表的Promise
   */
  getReservationsByMember(memberId) {
    return axios.get(`${BASE_URL}/reservations?member_id=${memberId}`)
      .then(handleResponse)
      .catch(handleError);
  },

  /**
   * 创建新的课程预约
   * @param {object} reservationData - 预约数据
   * @param {number} reservationData.course_id - 课程ID
   * @param {number} reservationData.member_id - 会员ID
   * @param {string} reservationData.reservation_time - 预约时间
   * @returns {Promise} - 包含创建结果的Promise
   */
  createReservation(reservationData) {
    return axios.post(`${BASE_URL}/reservations`, reservationData)
      .then(handleResponse)
      .catch(handleError);
  },

  /**
   * 取消预约
   * @param {number} reservationId - 预约ID
   * @returns {Promise} - 包含取消结果的Promise
   */
  cancelReservation(reservationId) {
    return axios.delete(`${BASE_URL}/reservations/${reservationId}`)
      .then(handleResponse)
      .catch(handleError);
  },

  /**
   * 获取可预约的课程列表
   * @param {string} date - 查询日期 (YYYY-MM-DD)
   * @returns {Promise} - 包含课程列表的Promise
   */
  getAvailableCourses(date) {
    return axios.get(`${BASE_URL}/courses/available?date=${date}`)
      .then(handleResponse)
      .catch(handleError);
  },

  /**
   * 获取教练排班信息
   * @param {string} date - 查询日期 (YYYY-MM-DD)
   * @returns {Promise} - 包含教练排班信息的Promise
   */
  getCoachSchedules(date) {
    return axios.get(`${BASE_URL}/coaches/schedules?date=${date}`)
      .then(handleResponse)
      .catch(handleError);
  }
};

export default reservationsApi;