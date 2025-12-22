import axios from 'axios';
import { handleApiError } from './errorHandler';
import { formatDateForAPI } from '../utils/date';

const API_BASE_URL = '/api/v1';

/**
 * 教练排班API客户端
 */
export default {
  /**
   * 获取教练排班列表
   * @returns {Promise} Axios promise
   */
  getSchedules() {
    return axios.get(`${API_BASE_URL}/coaches/schedule`).catch(handleApiError);
  },

  /**
   * 创建教练排班
   * @param {Object} scheduleData 排班数据
   * @returns {Promise} Axios promise
   */
  createSchedule(scheduleData) {
    return axios.post(`${API_BASE_URL}/coaches/schedule`, scheduleData).catch(handleApiError);
  },

  /**
   * 更新教练排班
   * @param {number} scheduleId 排班ID
   * @param {Object} scheduleData 排班数据
   * @returns {Promise} Axios promise
   */
  updateSchedule(scheduleId, scheduleData) {
    return axios.put(`${API_BASE_URL}/coaches/schedule/${scheduleId}`, scheduleData).catch(handleApiError);
  },

  /**
   * 删除教练排班
   * @param {number} scheduleId 排班ID
   * @returns {Promise} Axios promise
   */
  deleteSchedule(scheduleId) {
    return axios.delete(`${API_BASE_URL}/coaches/schedule/${scheduleId}`).catch(handleApiError);
  },

  /**
   * 获取所有教练列表
   * @returns {Promise} Axios promise
   */
  getCoaches() {
    return axios.get(`${API_BASE_URL}/coaches`).catch(handleApiError);
  },

  /**
   * 获取教练详情
   * @param {number} coachId 教练ID
   * @returns {Promise} Axios promise
   */
  getCoach(coachId) {
    return axios.get(`${API_BASE_URL}/coaches/${coachId}`).catch(handleApiError);
  },

  /**
   * 获取教练可用时间段
   * @param {number} coachId 教练ID
   * @param {string} date 查询日期
   * @returns {Promise} Axios promise
   */
  getCoachAvailability(coachId, date) {
    const formattedDate = formatDateForAPI(date);
,

  /**
   * 批量更新教练排班
   * @param {Array} schedules 排班数据数组
   * @returns {Promise} Axios promise
   */
  batchUpdateSchedules(schedules) {
    return axios.put(`${API_BASE_URL}/coaches/schedule/batch`, { schedules }).catch(handleApiError);
  }

  },
    return axios.get(`${API_BASE_URL}/coaches/${coachId}/availability?date=${formattedDate}`).catch(handleApiError);
    const formattedDate = formatDateForAPI(date);
    return axios.get(`${API_BASE_URL}/coaches/${coachId}/availability?date=${formattedDate}`).catch(handleApiError);
  }

};