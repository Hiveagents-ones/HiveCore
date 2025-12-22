<template>
  <div class="coach-schedule-view">
    <div class="view-header">
      <h1>教练排班管理</h1>
      <div class="view-switcher">
        <button 
          @click="activeView = 'calendar'" 
          :class="{ active: activeView === 'calendar' }">
          日历视图
        </button>
        <button 
          @click="activeView = 'timeline'" 
          :class="{ active: activeView === 'timeline' }">
          时间轴视图
        </button>
      </div>
    </div>

    <div class="coach-selector">
      <label for="coach-select">选择教练：</label>
      <select 
        id="coach-select" 
        v-model="selectedCoachId" 
        @change="fetchSchedule">
        <option 
          v-for="coach in coaches" 
          :key="coach.id" 
          :value="coach.id">
          {{ coach.name }}
        </option>
      </select>
    </div>

    <div class="schedule-container">
      <CalendarView 
        v-if="activeView === 'calendar'" 
        :schedule="currentSchedule" 
        @update-schedule="handleScheduleUpdate" />
      
      <TimelineView 
        v-else 
        :schedule="currentSchedule" 
        @update-schedule="handleScheduleUpdate" />
    </div>
  </div>
</template>

<script>
import { ref, onMounted } from 'vue';
import CalendarView from '../components/coach/CalendarView.vue';
import TimelineView from '../components/coach/TimelineView.vue';
import coachesApi from '../api/coaches';

export default {
  name: 'CoachScheduleView',
  components: {
    CalendarView,
    TimelineView
  },
  setup() {
    const activeView = ref('calendar');
    const coaches = ref([]);
    const selectedCoachId = ref(null);
    const currentSchedule = ref({});

    const fetchCoaches = async () => {
      try {
        const response = await coachesApi.getCoaches();
        coaches.value = response.data;
        if (coaches.value.length > 0) {
          selectedCoachId.value = coaches.value[0].id;
          fetchSchedule();
        }
      } catch (error) {
        console.error('获取教练列表失败:', error);
      }
    };

    const fetchSchedule = async () => {
      if (!selectedCoachId.value) return;
      try {
        const response = await coachesApi.getCoachSchedule(selectedCoachId.value);
        currentSchedule.value = response.data;
      } catch (error) {
        console.error('获取排班表失败:', error);
      }
    };

    const handleScheduleUpdate = async (updatedSchedule) => {
      try {
        await coachesApi.updateCoachSchedule(selectedCoachId.value, updatedSchedule);
        currentSchedule.value = updatedSchedule;
        alert('排班表更新成功');
      } catch (error) {
        console.error('更新排班表失败:', error);
        alert('排班表更新失败');
      }
    };

    onMounted(() => {
      fetchCoaches();
    });

    return {
      activeView,
      coaches,
      selectedCoachId,
      currentSchedule,
      fetchSchedule,
      handleScheduleUpdate
    };
  }
};
</script>

<style scoped>
.coach-schedule-view {
  padding: 20px;
}

.view-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.view-switcher button {
  padding: 8px 16px;
  margin-left: 10px;
  border: 1px solid #ccc;
  background: #fff;
  cursor: pointer;
  border-radius: 4px;
}

.view-switcher button.active {
  background: #42b983;
  color: white;
  border-color: #42b983;
}

.coach-selector {
  margin-bottom: 20px;
}

.coach-selector select {
  padding: 8px;
  border-radius: 4px;
  border: 1px solid #ccc;
  min-width: 200px;
}

.schedule-container {
  border: 1px solid #eee;
  border-radius: 8px;
  padding: 20px;
  background: #fff;
}
</style>