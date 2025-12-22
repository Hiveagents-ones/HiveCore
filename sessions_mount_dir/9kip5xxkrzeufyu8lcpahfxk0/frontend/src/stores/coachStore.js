import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import { fetchCoaches, fetchCoachSchedules, createCoachSchedule, updateCoachSchedule } from '../api/coaches';

/**
 * 教练排班状态管理
 * 管理教练信息、排班数据及相关操作
 */
export const useCoachStore = defineStore('coach', () => {
  // 状态
  const coaches = ref([]);
  const schedules = ref([]);
  const loading = ref(false);
  const error = ref(null);

  // Getters
  const availableCoaches = computed(() => {
    return coaches.value.filter(coach => coach.status === 'active');
  });

  const coachScheduleMap = computed(() => {
    const map = new Map();
    schedules.value.forEach(schedule => {
      if (!map.has(schedule.coach_id)) {
        map.set(schedule.coach_id, []);
      }
      map.get(schedule.coach_id).push(schedule);
    });
    return map;
  });

  // Actions
  const loadCoaches = async () => {
    try {
      loading.value = true;
      const response = await fetchCoaches();
      coaches.value = response.data;
    } catch (err) {
      error.value = err.message;
    } finally {
      loading.value = false;
    }
  };

  const loadSchedules = async () => {
    try {
      loading.value = true;
      const response = await fetchCoachSchedules();
      schedules.value = response.data;
    } catch (err) {
      error.value = err.message;
    } finally {
      loading.value = false;
    }
  };

  const addSchedule = async (scheduleData) => {
    try {
      loading.value = true;
      const response = await createCoachSchedule(scheduleData);
      schedules.value.push(response.data);
      return response.data;
    } catch (err) {
      error.value = err.message;
      throw err;
    } finally {
      loading.value = false;
    }
  };

  const updateSchedule = async (scheduleId, updateData) => {
    try {
      loading.value = true;
      const response = await updateCoachSchedule(scheduleId, updateData);
      const index = schedules.value.findIndex(s => s.id === scheduleId);
      if (index !== -1) {
        schedules.value[index] = response.data;
      }
      return response.data;
    } catch (err) {
      error.value = err.message;
      throw err;
    } finally {
      loading.value = false;
    }
  };

  // 初始化加载数据
  const initialize = async () => {
    await Promise.all([loadCoaches(), loadSchedules()]);
  };

  return {
    // State
    coaches,
    schedules,
    loading,
    error,
    
    // Getters
    availableCoaches,
    coachScheduleMap,
    
    // Actions
    loadCoaches,
    loadSchedules,
    addSchedule,
    updateSchedule,
    initialize
  };
});