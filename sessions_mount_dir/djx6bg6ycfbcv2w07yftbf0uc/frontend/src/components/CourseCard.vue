<template>
  <div class="course-card">
    <div class="course-image">
      <img :src="course.imageUrl || '/default-course.jpg'" :alt="course.title" />
    </div>
    <div class="course-content">
      <h3 class="course-title">{{ course.title }}</h3>
      <div class="course-info">
        <div class="info-item">
          <i class="icon-time"></i>
          <span>{{ formatTime(course.startTime) }} - {{ formatTime(course.endTime) }}</span>
        </div>
        <div class="info-item">
          <i class="icon-location"></i>
          <span>{{ course.location }}</span>
        </div>
        <div class="info-item">
          <i class="icon-coach"></i>
          <span>{{ course.coach }}</span>
        </div>
        <div class="info-item">
          <i class="icon-price"></i>
          <span class="price">¥{{ course.price }}</span>
        </div>
      </div>
      <div class="course-footer">
        <div class="capacity">
          <span>剩余名额: {{ course.capacity - course.booked }}/{{ course.capacity }}</span>
        </div>
        <button 
          class="book-button" 
          :disabled="course.capacity <= course.booked"
          @click="handleBook"
        >
          {{ course.capacity <= course.booked ? '已约满' : '立即预约' }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { defineProps, defineEmits } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '../stores/user'

const props = defineProps({
  course: {
    type: Object,
    required: true,
    default: () => ({
      id: '',
      title: '',
      startTime: '',
      endTime: '',
      location: '',
      coach: '',
      price: 0,
      capacity: 0,
      booked: 0,
      imageUrl: ''
    })
  }
})

const emit = defineEmits(['book'])
const router = useRouter()
const userStore = useUserStore()

const formatTime = (timeString) => {
  if (!timeString) return ''
  const date = new Date(timeString)
  return date.toLocaleTimeString('zh-CN', { 
    hour: '2-digit', 
    minute: '2-digit' 
  })
}

const handleBook = () => {
  if (!userStore.isLoggedIn) {
    router.push('/login')
    return
  }
  emit('book', props.course)
}
</script>

<style scoped>
.course-card {
  background: white;
  border-radius: 12px;
  overflow: hidden;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
  transition: transform 0.3s ease, box-shadow 0.3s ease;
  max-width: 320px;
}

.course-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
}

.course-image {
  width: 100%;
  height: 180px;
  overflow: hidden;
}

.course-image img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.course-content {
  padding: 16px;
}

.course-title {
  font-size: 18px;
  font-weight: 600;
  margin: 0 0 12px 0;
  color: #333;
  line-height: 1.4;
}

.course-info {
  margin-bottom: 16px;
}

.info-item {
  display: flex;
  align-items: center;
  margin-bottom: 8px;
  font-size: 14px;
  color: #666;
}

.info-item:last-child {
  margin-bottom: 0;
}

.info-item i {
  width: 16px;
  height: 16px;
  margin-right: 8px;
  background-size: contain;
}

.icon-time::before {
  content: '🕐';
}

.icon-location::before {
  content: '📍';
}

.icon-coach::before {
  content: '👤';
}

.icon-price::before {
  content: '💰';
}

.price {
  font-weight: 600;
  color: #ff6b6b;
}

.course-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-top: 12px;
  border-top: 1px solid #f0f0f0;
}

.capacity {
  font-size: 12px;
  color: #999;
}

.book-button {
  padding: 8px 20px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border: none;
  border-radius: 20px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.3s ease;
}

.book-button:hover:not(:disabled) {
  transform: scale(1.05);
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
}

.book-button:disabled {
  background: #ccc;
  cursor: not-allowed;
}

@media (max-width: 768px) {
  .course-card {
    max-width: 100%;
  }
}
</style>