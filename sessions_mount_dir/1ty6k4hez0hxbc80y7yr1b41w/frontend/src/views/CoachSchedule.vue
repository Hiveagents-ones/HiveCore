<template>
  <div class="coach-schedule">
    <div class="header">
      <h1>教练排班管理</h1>
      <div class="actions">
        <button class="btn primary" @click="exportSchedule">导出排班表</button>
        <button class="btn" @click="printSchedule">打印排班表</button>
        <button class="btn success" @click="showAddCoachDialog = true">添加教练</button>
      </div>
    </div>
    <div class="schedule-container">
      <ScheduleCalendar />
    </div>
  </div>
</template>

<script>
import ScheduleCalendar from '../components/ScheduleCalendar.vue';
import { useToast } from 'vue-toastification';
import { ref } from 'vue';

export default {
  name: 'CoachSchedule',
  components: {
    ScheduleCalendar
  },
  setup() {
    const toast = useToast();
const showAddCoachDialog = ref(false);
    
    const exportSchedule = () => {
      toast.success('排班表导出成功');
    };
    
    const printSchedule = () => {
      toast.info('准备打印排班表');
      window.print();
    };
    
    return {
      exportSchedule,
      printSchedule,
      showAddCoachDialog
    };
  }
};
</script>

<style scoped>
.coach-schedule {
  padding: 20px;
  max-width: 1200px;
  margin: 0 auto;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

h1 {
  margin: 0;
  color: #333;
}

.actions {
  display: flex;
  gap: 10px;
}

.btn {
  padding: 8px 16px;
  border-radius: 4px;
  border: 1px solid #ddd;
  background: white;
  cursor: pointer;
}

.btn.primary {
  background: #409eff;
  color: white;
  border-color: #409eff;
}

.schedule-container {
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
  padding: 20px;
}

@media print {
  .actions {
    display: none;
  }
}
</style>