import axios from 'axios';
import { API_BASE_URL } from '@/config';

/**
 * 获取所有教练列表
 * @returns {Promise} axios promise
 */
export function getCoaches() {
  return axios.get(`${API_BASE_URL}/coaches`);
}

/**
 * 创建新教练
 * @param {Object} coachData 教练数据
 * @returns {Promise} axios promise
 */
export function createCoach(coachData) {
  return axios.post(`${API_BASE_URL}/coaches`, coachData);
}

/**
 * 更新教练信息
 * @param {Number} coachId 教练ID
 * @param {Object} coachData 教练数据
 * @returns {Promise} axios promise
 */
export function updateCoach(coachId, coachData) {
  return axios.put(`${API_BASE_URL}/coaches/${coachId}`, coachData);
}

/**
 * 删除教练
 * @param {Number} coachId 教练ID
 * @returns {Promise} axios promise
 */
export function deleteCoach(coachId) {
  return axios.delete(`${API_BASE_URL}/coaches/${coachId}`);
}

/**
 * 获取教练排班信息
 * @param {Number} coachId 教练ID
 * @returns {Promise} axios promise
 */
export function getCoachSchedules(coachId) {
  return axios.get(`${API_BASE_URL}/coaches/${coachId}/schedules`);
}

/**
 * 创建教练排班
 * @param {Number} coachId 教练ID
 * @param {Object} scheduleData 排班数据
 * @returns {Promise} axios promise
 */
export function createCoachSchedule(coachId, scheduleData) {
  return axios.post(`${API_BASE_URL}/coaches/${coachId}/schedules`, scheduleData);
}

/**
 * 更新教练排班
 * @param {Number} coachId 教练ID
 * @param {Number} scheduleId 排班ID
 * @param {Object} scheduleData 排班数据
 * @returns {Promise} axios promise
 */
export function updateCoachSchedule(coachId, scheduleId, scheduleData) {
  return axios.put(`${API_BASE_URL}/coaches/${coachId}/schedules/${scheduleId}`, scheduleData);
}


/**
 * 删除教练排班
 * @param {Number} coachId 教练ID
 * @param {Number} scheduleId 排班ID
 * @returns {Promise} axios promise
 */
export function deleteCoachSchedule(coachId, scheduleId) {
  return axios.delete(`${API_BASE_URL}/coaches/${coachId}/schedules/${scheduleId}`);
}

/**
 * 获取教练可用时间段
 * @param {Number} coachId 教练ID
 * @param {String} date 查询日期 (YYYY-MM-DD)
 * @returns {Promise} axios promise
 */
export function getCoachAvailability(coachId, date) {
  return axios.get(`${API_BASE_URL}/coaches/${coachId}/availability?date=${date}`);
}

/**
 * 批量创建教练排班
 * @param {Number} coachId 教练ID
 * @param {Array} schedulesData 排班数据数组
 * @returns {Promise} axios promise
 */
export function batchCreateCoachSchedules(coachId, schedulesData) {
  return axios.post(`${API_BASE_URL}/coaches/${coachId}/schedules/batch`, schedulesData);
}

/**
 * 批量更新教练排班
 * @param {Number} coachId 教练ID
 * @param {Array} schedulesData 排班数据数组
 * @returns {Promise} axios promise
 */
export function batchUpdateCoachSchedules(coachId, schedulesData) {
  return axios.put(`${API_BASE_URL}/coaches/${coachId}/schedules/batch`, schedulesData);
}

/**
 * 批量删除教练排班
 * @param {Number} coachId 教练ID
 * @param {Array} scheduleIds 排班ID数组
 * @returns {Promise} axios promise
 */
export function batchDeleteCoachSchedules(coachId, scheduleIds) {


/**
 * 获取教练排班模板
 * @param {Number} coachId 教练ID
 * @returns {Promise} axios promise
 */
export function getCoachScheduleTemplate(coachId) {

  return axios.get(`${API_BASE_URL}/coaches/${coachId}/schedules/template`);
}

/**
 * 获取教练排班统计
 * @param {Number} coachId 教练ID
 * @param {String} startDate 开始日期 (YYYY-MM-DD)
 * @param {String} endDate 结束日期 (YYYY-MM-DD)
 * @returns {Promise} axios promise
 */
export function getCoachScheduleStats(coachId, startDate, endDate) {

  return axios.get(`${API_BASE_URL}/coaches/${coachId}/schedules/stats?start_date=${startDate}&end_date=${endDate}`);
}

/**
 * 获取教练排班导出数据
 * @param {Number} coachId 教练ID
 * @param {String} startDate 开始日期 (YYYY-MM-DD)
 * @param {String} endDate 结束日期 (YYYY-MM-DD)
 * @returns {Promise} axios promise
 */
export function exportCoachSchedules(coachId, startDate, endDate) {


  return axios.delete(`${API_BASE_URL}/coaches/${coachId}/schedules/batch`, { data: { schedule_ids: scheduleIds } });
}

/**
 * 获取教练排班冲突检查
 * @param {Number} coachId 教练ID
 * @param {Object} scheduleData 排班数据
 * @returns {Promise} axios promise
 */
export function checkScheduleConflict(coachId, scheduleData) {
  return axios.post(`${API_BASE_URL}/coaches/${coachId}/schedules/check-conflict`, scheduleData);
}

/**
 * 获取教练排班模板
 * @param {Number} coachId 教练ID
 * @returns {Promise} axios promise
 */
export function getCoachScheduleTemplate(coachId) {
  return axios.get(`${API_BASE_URL}/coaches/${coachId}/schedules/template`);
}

/**
 * 获取教练排班统计
 * @param {Number} coachId 教练ID
 * @param {String} startDate 开始日期 (YYYY-MM-DD)
 * @param {String} endDate 结束日期 (YYYY-MM-DD)
 * @returns {Promise} axios promise
 */
export function getCoachScheduleStats(coachId, startDate, endDate) {
  return axios.get(`${API_BASE_URL}/coaches/${coachId}/schedules/stats?start_date=${startDate}&end_date=${endDate}`);
}

/**
 * 获取教练排班导出数据
 * @param {Number} coachId 教练ID
 * @param {String} startDate 开始日期 (YYYY-MM-DD)
 * @param {String} endDate 结束日期 (YYYY-MM-DD)
 * @returns {Promise} axios promise
 */
export function exportCoachSchedules(coachId, startDate, endDate) {
  return axios.get(`${API_BASE_URL}/coaches/${coachId}/schedules/export?start_date=${startDate}&end_date=${endDate}`, {
    responseType: 'blob'
  });
}

/**
 * 批量删除教练排班
 * @param {Number} coachId 教练ID
 * @param {Array} scheduleIds 排班ID数组
 * @returns {Promise} axios promise
 */
export function batchDeleteCoachSchedules(coachId, scheduleIds) {
  return axios.delete(`${API_BASE_URL}/coaches/${coachId}/schedules/batch`, { data: { schedule_ids: scheduleIds } });
}
  return axios.post(`${API_BASE_URL}/coaches/${coachId}/schedules/check-conflict`, scheduleData);
}
