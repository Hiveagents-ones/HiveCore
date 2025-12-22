<template>
  <div class="calendar-view">
    <div class="calendar-header">
      <button @click="prevMonth">上个月</button>
      <h2>{{ currentMonth }}</h2>
      <button @click="nextMonth">下个月</button>
    </div>
    
    <div class="calendar-grid">
      <div 
        v-for="day in daysInMonth" 
        :key="day.date" 
        class="calendar-day"
        :class="{
          'today': day.isToday,
          'has-schedule': day.hasSchedule
        }"
        @click="selectDay(day)">
        <div class="day-number">{{ day.day }}</div>
        <div 
          v-if="day.hasSchedule" 
          class="schedule-indicator"></div>
      </div>
    </div>
    
    <div v-if="selectedDay" class="day-schedule">
      <h3>{{ selectedDay.date }} 排班</h3>
      <div 
        v-for="(shift, index) in selectedDay.schedule" 
        :key="index" 
        class="shift-item">
        <span>{{ shift.time }}</span>
        <span>{{ shift.course }}</span>
        <button @click="removeShift(index)">删除</button>
      </div>
      <div class="add-shift">
        <input v-model="newShift.time" placeholder="时间">
        <input v-model="newShift.course" placeholder="课程">
        <button @click="addShift">添加</button>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, computed, watch } from 'vue';

export default {
  name: 'CalendarView',
  props: {
    schedule: {
      type: Object,
      required: true
    }
  },
  emits: ['update-schedule'],
  setup(props, { emit }) {
    const currentDate = ref(new Date());
    const selectedDay = ref(null);
    const newShift = ref({ time: '', course: '' });
    
    const currentMonth = computed(() => {
      return currentDate.value.toLocaleString('default', { 
        month: 'long', 
        year: 'numeric' 
      });
    });
    
    const daysInMonth = computed(() => {
      const year = currentDate.value.getFullYear();
      const month = currentDate.value.getMonth();
      const today = new Date();
      
      const firstDay = new Date(year, month, 1);
      const lastDay = new Date(year, month + 1, 0);
      
      const days = [];
      
      for (let i = 1; i <= lastDay.getDate(); i++) {
        const date = new Date(year, month, i);
        const dateStr = date.toISOString().split('T')[0];
        const isToday = date.toDateString() === today.toDateString();
        const hasSchedule = props.schedule[dateStr] && props.schedule[dateStr].length > 0;
        
        days.push({
          day: i,
          date: dateStr,
          isToday,
          hasSchedule,
          schedule: hasSchedule ? [...props.schedule[dateStr]] : []
        });
      }
      
      return days;
    });
    
    const prevMonth = () => {
      currentDate.value = new Date(
        currentDate.value.getFullYear(), 
        currentDate.value.getMonth() - 1, 
        1
      );
    };
    
    const nextMonth = () => {
      currentDate.value = new Date(
        currentDate.value.getFullYear(), 
        currentDate.value.getMonth() + 1, 
        1
      );
    };
    
    const selectDay = (day) => {
      selectedDay.value = day;
    };
    
    const addShift = () => {
      if (!newShift.value.time || !newShift.value.course) return;
      
      selectedDay.value.schedule.push({ 
        ...newShift.value 
      });
      
      updateSchedule();
      newShift.value = { time: '', course: '' };
    };
    
    const removeShift = (index) => {
      selectedDay.value.schedule.splice(index, 1);
      updateSchedule();
    };
    
    const updateSchedule = () => {
      const updatedSchedule = { ...props.schedule };
      
      if (selectedDay.value.schedule.length > 0) {
        updatedSchedule[selectedDay.value.date] = selectedDay.value.schedule;
      } else {
        delete updatedSchedule[selectedDay.value.date];
      }
      
      emit('update-schedule', updatedSchedule);
    };
    
    watch(() => props.schedule, () => {
      if (selectedDay.value) {
        const day = daysInMonth.value.find(
          d => d.date === selectedDay.value.date
        );
        if (day) {
          selectedDay.value.schedule = day.schedule;
        }
      }
    }, { deep: true });
    
    return {
      currentDate,
      currentMonth,
      daysInMonth,
      selectedDay,
      newShift,
      prevMonth,
      nextMonth,
      selectDay,
      addShift,
      removeShift
    };
  }
};
</script>

<style scoped>
.calendar-view {
  max-width: 800px;
  margin: 0 auto;
}

.calendar-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.calendar-grid {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  gap: 10px;
}

.calendar-day {
  border: 1px solid #ddd;
  padding: 10px;
  min-height: 80px;
  cursor: pointer;
  position: relative;
}

.calendar-day:hover {
  background-color: #f5f5f5;
}

.calendar-day.today {
  background-color: #e6f7ff;
  border-color: #91d5ff;
}

.calendar-day.has-schedule {
  border-color: #52c41a;
}

.day-number {
  font-weight: bold;
  margin-bottom: 5px;
}

.schedule-indicator {
  width: 8px;
  height: 8px;
  background-color: #52c41a;
  border-radius: 50%;
  position: absolute;
  top: 5px;
  right: 5px;
}

.day-schedule {
  margin-top: 30px;
  padding: 20px;
  border: 1px solid #ddd;
  border-radius: 4px;
}

.shift-item {
  display: flex;
  justify-content: space-between;
  padding: 8px 0;
  border-bottom: 1px solid #eee;
}

.add-shift {
  display: flex;
  gap: 10px;
  margin-top: 15px;
}

.add-shift input {
  flex: 1;
  padding: 5px 10px;
}
</style>