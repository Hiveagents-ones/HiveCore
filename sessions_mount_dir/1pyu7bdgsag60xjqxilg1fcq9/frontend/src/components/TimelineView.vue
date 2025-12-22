<template>
  <div class="timeline-view">
    <div class="timeline-header">
      <h2>时间轴排班视图</h2>
      <div class="time-range">
        <span>08:00</span>
        <span>12:00</span>
        <span>16:00</span>
        <span>20:00</span>
      </div>
    </div>
    
    <div class="timeline-container">
      <div 
        v-for="(day, index) in weekDays" 
        :key="index" 
        class="timeline-day">
        <div class="day-header">{{ day }}</div>
        <div class="time-slots">
          <div 
            v-for="slot in timeSlots" 
            :key="slot" 
            class="time-slot"
            @click="handleSlotClick(day, slot)"
            :class="{ 'booked': isBooked(day, slot) }">
            <span v-if="isBooked(day, slot)">已排班</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'TimelineView',
  props: {
    schedule: {
      type: Object,
      required: true
    }
  },
  emits: ['update-schedule'],
  setup(props, { emit }) {
    const weekDays = ['周一', '周二', '周三', '周四', '周五', '周六', '周日'];
    const timeSlots = [
      '08:00-10:00',
      '10:00-12:00',
      '12:00-14:00',
      '14:00-16:00',
      '16:00-18:00',
      '18:00-20:00'
    ];

    const isBooked = (day, slot) => {
      if (!props.schedule || !props.schedule[day]) return false;
      return props.schedule[day].includes(slot);
    };

    const handleSlotClick = (day, slot) => {
      const updatedSchedule = { ...props.schedule };
      
      if (!updatedSchedule[day]) {
        updatedSchedule[day] = [];
      }
      
      const index = updatedSchedule[day].indexOf(slot);
      if (index > -1) {
        // 取消排班
        updatedSchedule[day].splice(index, 1);
      } else {
        // 添加排班
        updatedSchedule[day].push(slot);
      }
      
      emit('update-schedule', updatedSchedule);
    };

    return {
      weekDays,
      timeSlots,
      isBooked,
      handleSlotClick
    };
  }
};
</script>

<style scoped>
.timeline-view {
  margin-top: 20px;
}

.timeline-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 15px;
}

.time-range {
  display: flex;
  gap: 30px;
}

.timeline-container {
  display: flex;
  gap: 10px;
}

.timeline-day {
  flex: 1;
  border: 1px solid #ddd;
  border-radius: 4px;
  overflow: hidden;
}

.day-header {
  padding: 8px;
  background-color: #f5f5f5;
  text-align: center;
  font-weight: bold;
}

.time-slots {
  display: flex;
  flex-direction: column;
  gap: 5px;
  padding: 5px;
}

.time-slot {
  height: 40px;
  border: 1px solid #eee;
  border-radius: 4px;
  display: flex;
  justify-content: center;
  align-items: center;
  cursor: pointer;
  transition: all 0.2s;
}

.time-slot:hover {
  background-color: #f0f0f0;
}

.time-slot.booked {
  background-color: #e3f2fd;
  border-color: #bbdefb;
  color: #1976d2;
}
</style>