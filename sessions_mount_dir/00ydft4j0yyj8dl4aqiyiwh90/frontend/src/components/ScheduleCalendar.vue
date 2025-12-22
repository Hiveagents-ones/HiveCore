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
          v-for="timeSlot in timeSlots" 
          :key="timeSlot" 
          class="time-slot"
        >
          {{ timeSlot }}
        </div>
      </div>
      
      <div 
        v-for="day in weekDays" 
        :key="day.date" 
        class="day-column"
      >
        <div class="day-header">
          {{ day.name }}<br>
          {{ day.date }}
        </div>
        
        <div 
          v-for="timeSlot in timeSlots" 
          :key="timeSlot" 
          class="time-slot"
          @click="handleSlotClick(day.date, timeSlot)"
          :class="{ 
            'booked': isSlotBooked(day.date, timeSlot),
            'selected': isSlotSelected(day.date, timeSlot)
          }"
        >
          <div v-if="isSlotBooked(day.date, timeSlot)" class="booked-slot">
            {{ getSlotInfo(day.date, timeSlot) }}
          </div>
        </div>
      </div>
    </div>
    
    <div class="calendar-actions" v-if="selectedSlots.length > 0">
      <button @click="clearSelection">清除选择</button>
      <button @click="saveSchedule" :disabled="isSaving">
        {{ isSaving ? '保存中...' : '保存排班' }}
      </button>
    </div>
  </div>
</template>

<script>
import { ref, computed, onMounted } from 'vue';
import { getCoachSchedules, updateCoachSchedules } from '../api/coach';

export default {
  name: 'ScheduleCalendar',
  props: {
    coachId: {
      type: Number,
      required: true
    }
  },
  setup(props) {
    const currentDate = ref(new Date());
    const schedules = ref([]);
    const selectedSlots = ref([]);
    const isSaving = ref(false);
    
    const timeSlots = Array.from({ length: 16 }, (_, i) => {
      const hour = 7 + i;
      return `${hour}:00 - ${hour + 1}:00`;
    });
    
    const weekDays = computed(() => {
      const startOfWeek = new Date(currentDate.value);
      startOfWeek.setDate(startOfWeek.getDate() - startOfWeek.getDay());
      
      return Array.from({ length: 7 }, (_, i) => {
        const date = new Date(startOfWeek);
        date.setDate(date.getDate() + i);
        
        return {
          date: date.toISOString().split('T')[0],
          name: ['周日', '周一', '周二', '周三', '周四', '周五', '周六'][date.getDay()],
          fullDate: date
        };
      });
    });
    
    const currentWeekRange = computed(() => {
      const start = weekDays.value[0].fullDate;
      const end = weekDays.value[6].fullDate;
      return `${start.getMonth() + 1}月${start.getDate()}日 - ${end.getMonth() + 1}月${end.getDate()}日`;
    });
    
    const prevWeek = () => {
      currentDate.value = new Date(currentDate.value);
      currentDate.value.setDate(currentDate.value.getDate() - 7);
      fetchSchedules();
    };
    
    const nextWeek = () => {
      currentDate.value = new Date(currentDate.value);
      currentDate.value.setDate(currentDate.value.getDate() + 7);
      fetchSchedules();
    };
    
    const isSlotBooked = (date, timeSlot) => {
      return schedules.value.some(schedule => 
        schedule.date === date && schedule.time_slot === timeSlot
      );
    };
    
    const getSlotInfo = (date, timeSlot) => {
      const schedule = schedules.value.find(s => 
        s.date === date && s.time_slot === timeSlot
      );
      return schedule ? schedule.course_name : '';
    };
    
    const getSlotTimeRange = (timeSlot) => {
      const [startTime, endTime] = timeSlot.split(' - ');
      return {
        start: parseInt(startTime.split(':')[0]),
        end: parseInt(endTime.split(':')[0])
      };
    };
    
    const isSlotSelected = (date, timeSlot) => {

      return selectedSlots.value.some(slot => 
        slot.date === date && slot.timeSlot === timeSlot
      );
    };
    
    const handleSlotClick = (date, timeSlot) => {
      const { start, end } = getSlotTimeRange(timeSlot);
      const currentHour = new Date().getHours();
      
      // 不允许选择过去的时间段
      if (new Date(date) < new Date(new Date().setHours(0, 0, 0, 0)) || 
          (new Date(date).toDateString() === new Date().toDateString() && end <= currentHour)) {
        return;
      }
      const index = selectedSlots.value.findIndex(slot => 
        slot.date === date && slot.timeSlot === timeSlot
      );
      
      if (index === -1) {
        selectedSlots.value.push({ date, timeSlot });
      } else {
        selectedSlots.value.splice(index, 1);
      }
    };
    
    const clearSelection = () => {
      selectedSlots.value = [];
    };
    
    const saveSchedule = async () => {
      try {
        isSaving.value = true;
        const scheduleData = selectedSlots.value.map(slot => ({
          date: slot.date,
          time_slot: slot.timeSlot,
          coach_id: props.coachId
        }));
        
        await updateCoachSchedules(props.coachId, scheduleData);
        await fetchSchedules();
        selectedSlots.value = [];
      } catch (error) {
        console.error('Error saving schedule:', error);
      } finally {
        isSaving.value = false;
      }
    };
    
    const fetchSchedules = async () => {
      try {
        const data = await getCoachSchedules(props.coachId);
        schedules.value = data.filter(schedule => {
          const scheduleDate = new Date(schedule.date);
          const weekStart = new Date(weekDays.value[0].date);
          const weekEnd = new Date(weekDays.value[6].date);
          return scheduleDate >= weekStart && scheduleDate <= weekEnd;
        });
      } catch (error) {
        console.error('Error fetching schedules:', error);
      }
    };
    
    onMounted(() => {
      fetchSchedules();
    });
    
    return {
      currentDate,
      timeSlots,
      weekDays,
      currentWeekRange,
      schedules,
      selectedSlots,
      isSaving,
      prevWeek,
      nextWeek,
      isSlotBooked,
      getSlotInfo,
      isSlotSelected,
      handleSlotClick,
      clearSelection,
      saveSchedule
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
  padding: 8px 16px;
  background-color: #4CAF50;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

.calendar-header button:hover {
  background-color: #45a049;
}

.calendar-grid {
  display: flex;
  border: 1px solid #ddd;
  border-radius: 4px;
  overflow: hidden;
}

.time-column, .day-column {
  flex: 1;
}

.time-header, .day-header {
  padding: 10px;
  text-align: center;
  background-color: #f5f5f5;
  font-weight: bold;
  border-bottom: 1px solid #ddd;
}

.day-header {
  min-height: 50px;
}

.time-slot {
  height: 50px;
  border-bottom: 1px solid #eee;
  padding: 5px;
  cursor: pointer;
  position: relative;
}

.time-slot:hover {
  background-color: #f9f9f9;
}

.time-slot.booked {
  background-color: #e3f2fd;
}

.time-slot.selected {
  background-color: #bbdefb;
}

.booked-slot {
  background-color: #2196F3;
  color: white;
  padding: 4px;
  border-radius: 3px;
  font-size: 12px;
}

.calendar-actions {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}

.calendar-actions button {
  padding: 8px 16px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

.calendar-actions button:first-child {
  background-color: #f44336;
  color: white;
}

.calendar-actions button:last-child {
  background-color: #4CAF50;
  color: white;
}

.calendar-actions button:disabled {
  background-color: #cccccc;
  cursor: not-allowed;
}
</style>