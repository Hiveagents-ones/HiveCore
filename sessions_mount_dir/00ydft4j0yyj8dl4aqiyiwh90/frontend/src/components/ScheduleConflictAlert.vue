<template>
  <div v-if="showAlert" class="alert-container">
    <div class="alert alert-warning">
      <div class="alert-content">
        <span class="alert-icon">⚠️</span>
        <div>
          <h3>排班冲突预警</h3>
          <p>{{ conflictMessage }}</p>
        </div>
      </div>
      <button @click="dismissAlert" class="close-btn">&times;</button>
    </div>
  </div>
</template>

<script>
import { ref, computed } from 'vue';
import { useScheduleStore } from '../stores/schedule';

export default {
  name: 'ScheduleConflictAlert',
  setup() {
    const scheduleStore = useScheduleStore();
    const showAlert = ref(false);

    const conflictMessage = computed(() => {
      if (scheduleStore.conflictType === 'time') {
        return `检测到教练在同一时间段被安排了多个课程！ (冲突ID: ${scheduleStore.conflictId || '未知'})`;
      } else if (scheduleStore.conflictType === 'leave') {
        return `检测到教练在请假期间被安排了课程！ (冲突ID: ${scheduleStore.conflictId || '未知'})`;
      } else if (scheduleStore.conflictType === 'threshold') {
        return `检测到教练排班超过每日最大课时限制！ (教练: ${scheduleStore.conflictData?.coachName || '未知'}, 当前: ${scheduleStore.conflictData?.current || 0}, 最大: ${scheduleStore.conflictData?.max || 0})`;
      }
      return `检测到排班冲突！ (冲突ID: ${scheduleStore.conflictId || '未知'})`;
    });

    // 监听store中的冲突状态
    scheduleStore.$subscribe((mutation, state) => {
      showAlert.value = state.hasConflict;
    });

    const dismissAlert = () => {
      showAlert.value = false;
      scheduleStore.clearConflict();
      // 记录用户已查看的冲突ID
      if (scheduleStore.conflictId) {
        scheduleStore.addViewedConflict(scheduleStore.conflictId);
      }
    };

    return {
      showAlert,
      conflictMessage,
      dismissAlert
    };
  }
};
</script>

<style scoped>
.alert-container {
  position: fixed;
  top: 20px;
  right: 20px;
  z-index: 1000;
  max-width: 400px;
}

.alert {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  padding: 15px;
  border-radius: 4px;
  background-color: #fff3cd;
  border-left: 5px solid #ffc107;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
}

.alert-content {
  display: flex;
  align-items: flex-start;
  gap: 10px;
}

.alert-icon {
  font-size: 24px;
  margin-right: 10px;
}

.alert h3 {
  margin: 0 0 5px 0;
  font-size: 16px;
  color: #856404;
}

.alert p {
  margin: 0;
  font-size: 14px;
  color: #856404;
}

.close-btn {
  background: none;
  border: none;
  font-size: 20px;
  cursor: pointer;
  color: #856404;
  padding: 0 0 0 15px;
}

.close-btn:hover {
  opacity: 0.8;
}
</style>