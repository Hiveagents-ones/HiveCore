<template>
  <div 
    class="course-card" 
    :class="{ 'booked': course.isBooked, 'full': course.isFull }"
  >
    <div class="course-header">
      <h3>{{ course.name }}</h3>
      <span class="category">{{ course.category }}</span>
    </div>
    <div class="course-details">
      <p><i class="far fa-clock"></i> {{ formatTime(course.startTime) }} - {{ formatTime(course.endTime) }}</p>
      <p><i class="far fa-user"></i> {{ course.instructor }}</p>
      <p><i class="fas fa-map-marker-alt"></i> {{ course.location }}</p>
      <p><i class="fas fa-users"></i> {{ course.bookedCount }}/{{ course.capacity }}</p>
    </div>
    <div class="course-actions">
      <button 
        v-if="!course.isBooked && !course.isFull"
        @click="$emit('book', course.id)"
        class="btn btn-primary"
      >
        预约
      </button>
      <button 
        v-if="course.isBooked"
        @click="$emit('cancel', course.id)"
        class="btn btn-secondary"
      >
        取消预约
      </button>
      <span v-if="course.isFull" class="full-text">已满</span>
    </div>
  </div>
</template>

<script setup>
import { defineProps, defineEmits } from 'vue'

const props = defineProps({
  course: {
    type: Object,
    required: true
  }
})

const emit = defineEmits(['book', 'cancel'])

const formatTime = (timeString) => {
  if (!timeString) return ''
  const date = new Date(timeString)
  return date.toLocaleTimeString('zh-CN', { 
    hour: '2-digit', 
    minute: '2-digit' 
  })
}
</script>

<style scoped>
.course-card {
  background: white;
  border-radius: 8px;
  padding: 1rem;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  transition: transform 0.2s, box-shadow 0.2s;
}

.course-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.15);
}

.course-card.booked {
  border-left: 4px solid #28a745;
}

.course-card.full {
  opacity: 0.7;
  border-left: 4px solid #dc3545;
}

.course-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.75rem;
}

.course-header h3 {
  margin: 0;
  font-size: 1.1rem;
  color: #333;
}

.category {
  background: #f0f0f0;
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
  font-size: 0.85rem;
  color: #666;
}

.course-details {
  margin-bottom: 1rem;
}

.course-details p {
  margin: 0.25rem 0;
  font-size: 0.9rem;
  color: #555;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.course-details i {
  width: 16px;
  text-align: center;
  color: #888;
}

.course-actions {
  display: flex;
  justify-content: flex-end;
  align-items: center;
  gap: 0.5rem;
}

.btn {
  padding: 0.5rem 1rem;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.9rem;
  transition: background-color 0.2s;
}

.btn-primary {
  background-color: #007bff;
  color: white;
}

.btn-primary:hover {
  background-color: #0056b3;
}

.btn-secondary {
  background-color: #6c757d;
  color: white;
}

.btn-secondary:hover {
  background-color: #545b62;
}

.full-text {
  color: #dc3545;
  font-weight: bold;
}
</style>