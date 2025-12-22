<template>
  <div class="time-slot-picker">
    <div class="calendar-header">
      <button @click="prevWeek">←</button>
      <h2>{{ currentWeekRange }}</h2>
      <button @click="nextWeek">→</button>
    </div>
    
    <div class="time-grid">
      <div class="time-column">
        <div class="time-header">Time</div>
        <div 
          class="time-cell" 
          v-for="time in timeSlots" 
          :key="time"
        >
          {{ time }}
        </div>
      </div>
      
      <div 
        class="day-column" 
        v-for="day in weekDays" 
        :key="day.date"
      >
        <div class="day-header">{{ day.label }}</div>
        <div 
          class="time-cell" 
          v-for="time in timeSlots" 
          :key="time"
          @click="selectSlot(day.date, time)"
          :class="{
            'available': isSlotAvailable(day.date, time),
            'selected': isSlotSelected(day.date, time),
            'booked': isSlotBooked(day.date, time)
          }"
        >
          <span v-if="isSlotBooked(day.date, time)">Booked</span>
          <span v-else-if="isSlotSelected(day.date, time)">Selected</span>
          <span v-else>Available</span>
        </div>
      </div>
    </div>
    
    <div class="selected-slot" v-if="selectedSlot">
      <p>Selected: {{ selectedSlot.date }} at {{ selectedSlot.time }}</p>
      <button @click="confirmBooking">Confirm Booking</button>
    </div>
  </div>
</template>

<script>
import { ref, computed, onMounted } from 'vue';
import { useBookingStore } from '../stores/booking';
import { format, addDays, parseISO, isSameDay } from 'date-fns';

export default {
  name: 'TimeSlotPicker',
  
  setup() {
    const bookingStore = useBookingStore();
    const currentDate = ref(new Date());
    const selectedSlot = ref(null);
    const bookedSlots = ref([]);
    
    // Generate time slots from 8:00 AM to 8:00 PM every 30 minutes
    const timeSlots = Array.from({ length: 24 }, (_, i) => {
      const hour = 8 + Math.floor(i / 2);
      const minute = i % 2 === 0 ? '00' : '30';
      return `${hour}:${minute}`;
    });
    
    // Generate week days starting from current week
    const weekDays = computed(() => {
      const startOfWeek = new Date(currentDate.value);
      startOfWeek.setDate(startOfWeek.getDate() - startOfWeek.getDay());
      
      return Array.from({ length: 7 }, (_, i) => {
        const date = addDays(startOfWeek, i);
        return {
          date: date,
          label: format(date, 'EEE MMM d')
        };
      });
    });
    
    const currentWeekRange = computed(() => {
      const start = weekDays.value[0].date;
      const end = weekDays.value[6].date;
      return `${format(start, 'MMM d')} - ${format(end, 'MMM d, yyyy')}`;
    });
    
    const prevWeek = () => {
      currentDate.value = addDays(currentDate.value, -7);
    };
    
    const nextWeek = () => {
      currentDate.value = addDays(currentDate.value, 7);
    };
    
    const selectSlot = (date, time) => {
      if (!isSlotAvailable(date, time) || isSlotBooked(date, time)) return;
      
      selectedSlot.value = { date, time };
    };
    
    const isSlotAvailable = (date, time) => {
      // In a real app, this would check against business hours
      return true;
    };
    
    const isSlotSelected = (date, time) => {
      if (!selectedSlot.value) return false;
      return (
        isSameDay(date, selectedSlot.value.date) && 
        time === selectedSlot.value.time
      );
    };
    
    const isSlotBooked = (date, time) => {
      return bookedSlots.value.some(slot => 
        isSameDay(parseISO(slot.date), date) && 
        slot.time === time
      );
    };
    
    const confirmBooking = () => {
      if (selectedSlot.value) {
        bookingStore.bookCourse({
          date: selectedSlot.value.date,
          time: selectedSlot.value.time
        });
        bookedSlots.value.push(selectedSlot.value);
        selectedSlot.value = null;
      }
    };
    
    onMounted(async () => {
      // Fetch booked slots from API
      // In a real app, this would be an API call
      // bookedSlots.value = await fetchBookedSlots();
    });
    
    return {
      timeSlots,
      weekDays,
      currentWeekRange,
      selectedSlot,
      prevWeek,
      nextWeek,
      selectSlot,
      isSlotAvailable,
      isSlotSelected,
      isSlotBooked,
      confirmBooking
    };
  }
};
</script>

<style scoped>
.time-slot-picker {
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

.time-grid {
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

.time-cell {
  height: 40px;
  padding: 10px;
  border-bottom: 1px solid #eee;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
}

.time-cell.available {
  background: #e8f5e9;
}

.time-cell.available:hover {
  background: #c8e6c9;
}

.time-cell.selected {
  background: #81c784;
  color: white;
}

.time-cell.booked {
  background: #ffcdd2;
  color: #c62828;
  cursor: not-allowed;
}

.selected-slot {
  margin-top: 20px;
  padding: 15px;
  background: #f5f5f5;
  border-radius: 4px;
  text-align: center;
}

.selected-slot button {
  margin-top: 10px;
  padding: 8px 20px;
  background: #4CAF50;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}
</style>