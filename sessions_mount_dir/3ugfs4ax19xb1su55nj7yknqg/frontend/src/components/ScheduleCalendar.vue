<template>
  <div class="schedule-calendar">
    <div class="calendar-header">
      <h2>教练排班表</h2>
      <div class="controls">
        <select v-model="selectedCoach" @change="fetchSchedule">
          <option value="">选择教练</option>
          <option v-for="coach in coaches" :key="coach.id" :value="coach.id">
            {{ coach.name }}
          </option>
        </select>
        <button @click="showAddForm = true">添加排班</button>
      </div>
    </div>

    <div class="calendar-grid">
      <div class="day-header" v-for="day in days" :key="day">{{ day }}</div>
      <div 
        class="time-slot" 
        v-for="timeSlot in timeSlots" 
        :key="timeSlot"
        @click="handleSlotClick(timeSlot)"
      >
        <div class="time-label">{{ timeSlot }}</div>
        <div 
          class="day-slot" 
          v-for="day in days" 
          :key="day"
          :class="{ 'has-schedule': hasSchedule(day, timeSlot) }"
        >
          <div v-if="hasSchedule(day, timeSlot)" class="schedule-item">
            {{ getSchedule(day, timeSlot).courseName || '排班' }}
          </div>
        </div>
      </div>
    </div>

    <div v-if="showAddForm" class="modal">
      <div class="modal-content">
        <h3>添加排班</h3>
        <form @submit.prevent="addSchedule">
          <div class="form-group">
            <label>星期</label>
            <select v-model="newSchedule.day">
              <option v-for="(day, index) in days" :key="index" :value="day">
                {{ day }}
              </option>
            </select>
          </div>
          <div class="form-group">
            <label>开始时间</label>
            <select v-model="newSchedule.startTime">
              <option v-for="time in timeSlots" :key="time" :value="time">
                {{ time }}
              </option>
            </select>
          </div>
          <div class="form-group">
            <label>结束时间</label>
            <select v-model="newSchedule.endTime">
              <option v-for="time in timeSlots" :key="time" :value="time">
                {{ time }}
              </option>
            </select>
          </div>
          <div class="form-group">
            <label>关联课程</label>
            <select v-model="newSchedule.courseId">
              <option value="">不关联课程</option>
              <option v-for="course in courses" :key="course.id" :value="course.id">
                {{ course.name }}
              </option>
            </select>
          </div>
          <div class="form-actions">
            <button type="button" @click="showAddForm = false">取消</button>
            <button type="submit">保存</button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, onMounted } from 'vue';
import { getCoaches, getCoachSchedule, addCoachSchedule } from '../api/schedules';
import { getCourses } from '../api/courses';

export default {
  name: 'ScheduleCalendar',
  setup() {
    const days = ['周一', '周二', '周三', '周四', '周五', '周六', '周日'];
    const timeSlots = Array.from({ length: 14 }, (_, i) => `${8 + i}:00`);
    
    const coaches = ref([]);
    const courses = ref([]);
    const schedules = ref([]);
    const selectedCoach = ref('');
    const showAddForm = ref(false);
    const selectedSlot = ref(null);
    
    const newSchedule = ref({
      day: '周一',
      startTime: '8:00',
      endTime: '9:00',
      courseId: ''
    });

    const fetchCoaches = async () => {
      try {
        const response = await getCoaches();
        coaches.value = response.data;
      } catch (error) {
        console.error('获取教练列表失败:', error);
      }
    };

    const fetchCourses = async () => {
      try {
        const response = await getCourses();
        courses.value = response.data;
      } catch (error) {
        console.error('获取课程列表失败:', error);
      }
    };

    const fetchSchedule = async () => {
      if (!selectedCoach.value) return;
      
      try {
        const response = await getCoachSchedule(selectedCoach.value);
        schedules.value = response.data;
      } catch (error) {
        console.error('获取排班表失败:', error);
      }
    };

    const addSchedule = async () => {
      if (!selectedCoach.value) {
        alert('请先选择教练');
        return;
      }
      
      try {
        const scheduleData = {
          coach_id: selectedCoach.value,
          day_of_week: days.indexOf(newSchedule.value.day) + 1,
          start_hour: parseInt(newSchedule.value.startTime.split(':')[0]),
          end_hour: parseInt(newSchedule.value.endTime.split(':')[0]),
          course_id: newSchedule.value.courseId || null
        };
        
        await addCoachSchedule(scheduleData);
        await fetchSchedule();
        showAddForm.value = false;
        resetNewSchedule();
      } catch (error) {
        console.error('添加排班失败:', error);
      }
    };

    const resetNewSchedule = () => {
      newSchedule.value = {
        day: '周一',
        startTime: '8:00',
        endTime: '9:00',
        courseId: ''
      };
    };

    const handleSlotClick = (time) => {
      if (!selectedCoach.value) return;
      
      selectedSlot.value = time;
      resetNewSchedule();
      newSchedule.value.startTime = time;
      newSchedule.value.endTime = `${parseInt(time.split(':')[0]) + 1}:00`;
      showAddForm.value = true;
    };

    const hasSchedule = (day, time) => {
      if (!schedules.value.length) return false;
      
      const hour = parseInt(time.split(':')[0]);
      const dayIndex = days.indexOf(day) + 1;
      
      return schedules.value.some(schedule => 
        schedule.day_of_week === dayIndex && 
        schedule.start_hour <= hour && 
        schedule.end_hour > hour
      );
    };

    const getSchedule = (day, time) => {
      const hour = parseInt(time.split(':')[0]);
      const dayIndex = days.indexOf(day) + 1;
      
      return schedules.value.find(schedule => 
        schedule.day_of_week === dayIndex && 
        schedule.start_hour <= hour && 
        schedule.end_hour > hour
      ) || {};
    };

    onMounted(() => {
      fetchCoaches();
      fetchCourses();
    });

    return {
      days,
      timeSlots,
      coaches,
      courses,
      schedules,
      selectedCoach,
      showAddForm,
      newSchedule,
      fetchSchedule,
      addSchedule,
      handleSlotClick,
      hasSchedule,
      getSchedule
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

.controls {
  display: flex;
  gap: 10px;
}

select, button {
  padding: 8px 12px;
  border-radius: 4px;
  border: 1px solid #ddd;
}

button {
  background-color: #4CAF50;
  color: white;
  border: none;
  cursor: pointer;
}

button:hover {
  background-color: #45a049;
}

.calendar-grid {
  display: grid;
  grid-template-columns: 100px repeat(7, 1fr);
  gap: 1px;
  background-color: #ddd;
  border: 1px solid #ddd;
}

.day-header, .time-slot {
  background-color: white;
  padding: 10px;
  text-align: center;
}

.day-header {
  font-weight: bold;
  background-color: #f5f5f5;
}

.time-slot {
  display: grid;
  grid-template-columns: 50px repeat(7, 1fr);
  gap: 1px;
}

.time-label {
  grid-column: 1;
  font-weight: bold;
}

.day-slot {
  min-height: 50px;
  border: 1px solid #eee;
  cursor: pointer;
}

.day-slot:hover {
  background-color: #f9f9f9;
}

.has-schedule {
  background-color: #e3f2fd;
}

.schedule-item {
  padding: 5px;
  margin: 2px;
  background-color: #bbdefb;
  border-radius: 3px;
  font-size: 12px;
}

.modal {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background-color: rgba(0, 0, 0, 0.5);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1000;
}

.modal-content {
  background-color: white;
  padding: 20px;
  border-radius: 5px;
  width: 400px;
}

.form-group {
  margin-bottom: 15px;
}

.form-group label {
  display: block;
  margin-bottom: 5px;
}

.form-group select {
  width: 100%;
  padding: 8px;
}

.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 20px;
}

.form-actions button {
  padding: 8px 16px;
}

.form-actions button[type="button"] {
  background-color: #f44336;
}

.form-actions button[type="button"]:hover {
  background-color: #d32f2f;
}
</style>