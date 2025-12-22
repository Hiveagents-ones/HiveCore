<template>
  <div class="schedule-calendar">
    <div class="calendar-header">
      <button @click="prevWeek">上一周</button>
      <h2>{{ currentWeekRange }}</h2>
      <button @click="nextWeek">下一周</button>
    </div>
    
    <div class="calendar-grid">
      <div class="time-column">
        <div class="time-header">时间</div>
        <div 
          v-for="time in timeSlots" 
          :key="time" 
          class="time-slot"
        >
          {{ time }}
        </div>
      </div>
      
      <div 
        v-for="day in daysOfWeek" 
        :key="day.date" 
        class="day-column"
      >
        <div class="day-header">
          {{ day.name }}<br>{{ day.date }}
        </div>
        <div 
          v-for="time in timeSlots" 
          :key="time" 
          class="time-slot"
          @dragover.prevent
          @drop="handleDrop(day.date, time)"
        >
          <div 
            v-for="schedule in getSchedulesForDayAndTime(day.date, time)" 
            :key="schedule.id"
            class="schedule-item"
            draggable
            @dragstart="handleDragStart($event, schedule)"
          >
            {{ schedule.coach_name || `教练 ${schedule.coach_id}` }}
            <button class="delete-btn" @click="deleteSchedule(schedule.id)">×</button>
          </div>
        </div>
      </div>
    </div>
    
    <div class="coach-list">
      <h3>教练列表</h3>
      <div 
        v-for="coach in coaches" 
        :key="coach.id" 
        class="coach-item"
        draggable
        @dragstart="handleCoachDragStart($event, coach)"
      >
        {{ coach.name }}
      </div>
    </div>
  </div>
</template>

<script>
import { ref, computed, onMounted } from 'vue';
import { 
  getCoachSchedules, 
  createCoachSchedule, 
  updateCoachSchedule,
  getCoachScheduleById,
  deleteCoachSchedule,
  fetchCoachesList
} from '../api/coaches';

export default {
  name: 'ScheduleCalendar',
  
  setup() {
    const currentDate = ref(new Date());
    const schedules = ref([]);
    const coaches = ref([]);
    const draggedSchedule = ref(null);
    const draggedCoach = ref(null);
    
    const timeSlots = Array.from({ length: 24 }, (_, i) => `${i}:00 - ${i + 1}:00`);
    
    const daysOfWeek = computed(() => {
      const startOfWeek = new Date(currentDate.value);
      startOfWeek.setDate(startOfWeek.getDate() - startOfWeek.getDay());
      
      return Array.from({ length: 7 }, (_, i) => {
        const date = new Date(startOfWeek);
        date.setDate(date.getDate() + i);
        
        return {
          name: ['周日', '周一', '周二', '周三', '周四', '周五', '周六'][date.getDay()],
          date: date.toISOString().split('T')[0]
        };
      });
    });
    
    const currentWeekRange = computed(() => {
      const start = new Date(daysOfWeek.value[0].date);
      const end = new Date(daysOfWeek.value[6].date);
      return `${start.getMonth() + 1}月${start.getDate()}日 - ${end.getMonth() + 1}月${end.getDate()}日`;
    });
    
    const getSchedulesForDayAndTime = (date, timeSlot) => {
      const [startHour] = timeSlot.split(':').map(Number);
      const startTime = new Date(date);
      startTime.setHours(startHour);
      
      const endTime = new Date(startTime);
      endTime.setHours(startHour + 1);
      
      return schedules.value.filter(schedule => {
        const scheduleStart = new Date(schedule.start_time);
        const scheduleEnd = new Date(schedule.end_time);
        
        return scheduleStart >= startTime && scheduleEnd <= endTime;
      });
    };
    
    const prevWeek = () => {
      currentDate.value.setDate(currentDate.value.getDate() - 7);
      fetchSchedules();
    };
    
    const nextWeek = () => {
      currentDate.value.setDate(currentDate.value.getDate() + 7);
      fetchSchedules();
    };
    
    const fetchSchedules = async () => {
      try {
        const response = await getCoachSchedules({
          start_date: daysOfWeek.value[0].date,
          end_date: daysOfWeek.value[6].date
        });
        schedules.value = response.data;
      } catch (error) {
        console.error('获取排班失败:', error);
      }
    };
    
    const fetchCoaches = async () => {
      try {
        const response = await fetchCoachesList();
        coaches.value = response.data;
      } catch (error) {
        console.error('获取教练列表失败:', error);
      }
    };
    
    const handleDragStart = (event, schedule) => {
      draggedSchedule.value = schedule;
      event.dataTransfer.setData('text/plain', '');
    };
    
    const handleCoachDragStart = (event, coach) => {
      draggedCoach.value = coach;
      event.dataTransfer.setData('text/plain', '');
    };
    
    const handleDrop = async (date, timeSlot) => {
      const [startHour] = timeSlot.split(':').map(Number);
      const startTime = new Date(date);
      startTime.setHours(startHour);
      
      const endTime = new Date(startTime);
      endTime.setHours(startHour + 1);
      
      try {
        if (draggedSchedule.value) {
          // 更新现有排班
          await updateCoachSchedule(draggedSchedule.value.id, {
            start_time: startTime.toISOString(),
            end_time: endTime.toISOString()
          });
        } else if (draggedCoach.value) {
          // 创建新排班
          await createCoachSchedule({
            coach_id: draggedCoach.value.id,
            start_time: startTime.toISOString(),
            end_time: endTime.toISOString(),
            status: 'scheduled'
          });
        }
        
        await fetchSchedules();
      } catch (error) {
        console.error('更新排班失败:', error);
      } finally {
        draggedSchedule.value = null;
        draggedCoach.value = null;
      }
    };
    
    const deleteSchedule = async (id) => {
      try {
        const schedule = schedules.value.find(s => s.id === id);
        if (schedule && confirm(`确定要删除 ${schedule.coach_name || `教练 ${schedule.coach_id}`} 的排班吗？`)) {
          await deleteCoachSchedule(id);
          await fetchSchedules();
        }
      } catch (error) {
        console.error('删除排班失败:', error);
      }
    };
    
    onMounted(() => {
      fetchSchedules();
      fetchCoaches();
    });
    
    return {
      currentDate,
      schedules,
      coaches,
      timeSlots,
      daysOfWeek,
      currentWeekRange,
      getSchedulesForDayAndTime,
      prevWeek,
      nextWeek,
      handleDragStart,
      handleCoachDragStart,
      handleDrop,
      deleteSchedule
    };
  }
};
</script>

<style scoped>
.schedule-calendar {
  font-family: Arial, sans-serif;
  max-width: 1200px;
  margin: 0 auto;
}

.calendar-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.calendar-header button {
  padding: 5px 15px;
  background: #4CAF50;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

.calendar-header button:hover {
  background: #45a049;
}

.calendar-grid {
  display: flex;
  border: 1px solid #ddd;
}

.time-column, .day-column {
  flex: 1;
}

.time-header, .day-header {
  padding: 10px;
  text-align: center;
  background: #f5f5f5;
  border-bottom: 1px solid #ddd;
  font-weight: bold;
}

.time-slot {
  height: 60px;
  border-bottom: 1px solid #eee;
  padding: 5px;
  position: relative;
}

.schedule-item {
  background: #4CAF50;
  color: white;
  padding: 5px;
  margin: 2px 0;
  border-radius: 3px;
  cursor: move;
  position: relative;
}

.delete-btn {
  position: absolute;
  right: 5px;
  top: 50%;
  transform: translateY(-50%);
  background: none;
  border: none;
  color: white;
  cursor: pointer;
  font-size: 16px;
}

.coach-list {
  margin-top: 30px;
}

.coach-item {
  display: inline-block;
  padding: 8px 15px;
  margin: 5px;
  background: #2196F3;
  color: white;
  border-radius: 4px;
  cursor: move;
}
</style>