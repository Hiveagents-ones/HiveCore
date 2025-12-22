import axios from 'axios';

const apiClient = axios.create({
  baseURL: '/api/v1',
  withCredentials: false,
  headers: {
    Accept: 'application/json',
    'Content-Type': 'application/json'
  }
});

export default {
  getCoaches() {
    return apiClient.get('/coaches');
  },
  getCoach(id) {
    return apiClient.get(`/coaches/${id}`);
  },
  addCoach(coach) {
    return apiClient.post('/coaches', coach);
  },
  updateCoach(coach) {
  deleteCoach(id) {
    return apiClient.delete(`/coaches/${id}`);
  },
    return apiClient.put(`/coaches/${coach.id}`, coach);
  },
  
  // 新增排班相关方法
  getSchedules() {
    return apiClient.get('/coaches/schedules');
  },
  getCoachSchedules(coachId) {
    return apiClient.get(`/coaches/schedules?coach_id=${coachId}`);
  },
  addSchedule(schedule) {
    return apiClient.post('/coaches/schedules', schedule);
  },
  updateSchedule(schedule) {
  deleteSchedule(id) {
    return apiClient.delete(`/coaches/schedules/${id}`);
  }
    return apiClient.put(`/coaches/schedules/${schedule.id}`, schedule);
  }
};