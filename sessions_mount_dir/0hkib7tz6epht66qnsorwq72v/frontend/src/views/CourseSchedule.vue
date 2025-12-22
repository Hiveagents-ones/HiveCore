<template>
  <div class="course-schedule">
    <div class="header">
      <h1>{{ t('schedule.title') }}</h1>
      <div class="filters">
        <select v-model="selectedDate" @change="fetchCourses">
          <option v-for="date in availableDates" :key="date" :value="date">
            {{ formatDate(date) }}
          </option>
        </select>
        <select v-model="selectedCategory" @change="fetchCourses">
          <option value="">{{ t('schedule.allCategories') }}</option>
          <option v-for="category in categories" :key="category" :value="category">
            {{ category }}
          </option>
        </select>
      </div>
    </div>

    <div class="schedule-grid" v-if="!loading">
      <div 
        v-for="course in filteredCourses" 
        :key="course.id" 
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
            @click="bookCourse(course.id)"
            class="btn btn-primary"
          >
            {{ t('schedule.book') }}
          </button>
          <button 
            v-if="course.isBooked"
            @click="cancelBooking(course.id)"
            class="btn btn-secondary"
          >
            {{ t('schedule.cancel') }}
          </button>
          <span v-if="course.isFull" class="full-text">{{ t('schedule.full') }}</span>
        </div>
      </div>
    </div>

    <div v-if="loading" class="loading">
      <i class="fas fa-spinner fa-spin"></i> {{ t('common.loading') }}
    </div>

    <div v-if="error" class="error">
      {{ error }}
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, computed, shallowRef } from 'vue'
import { useCourseStore } from '@/stores/course'
import { useAuthStore } from '@/stores/auth'
import { useI18n } from 'vue-i18n'

import { useToast } from 'vue-toastification'

const courseStore = useCourseStore()
const authStore = useAuthStore()
const { t } = useI18n()

const toast = useToast()

const selectedDate = ref(new Date().toISOString().split('T')[0])
const selectedCategory = ref('')
const loading = ref(false)
const error = ref('')
const courses = shallowRef([])

const availableDates = computed(() => {
  const dates = []
  const today = new Date()
  for (let i = 0; i < 7; i++) {
    const date = new Date(today)
    date.setDate(today.getDate() + i)
    dates.push(date.toISOString().split('T')[0])
  }
  return dates
})

const categories = computed(() => {
  const cats = new Set()
  courseStore.courses.forEach(course => cats.add(course.category))
  return Array.from(cats)
})

const filteredCourses = computed(() => {
  return courses.value.filter(course => {
    const courseDate = new Date(course.startTime).toISOString().split('T')[0]
    const dateMatch = courseDate === selectedDate.value
    const categoryMatch = !selectedCategory.value || course.category === selectedCategory.value
    return dateMatch && categoryMatch
  })
})

const fetchCourses = async () => {
  loading.value = true
  error.value = ''
  try {
    await courseStore.fetchCourses()
    courses.value = courseStore.courses.map(course => ({
      ...course,
      isFull: course.bookedCount >= course.capacity
    }))
  } catch (err) {
    toast.error(t('errors.fetchCourses'))
    console.error('Failed to fetch courses:', err)
  } finally {
    loading.value = false
  }
}

const bookCourse = async (courseId) => {
  if (!authStore.isAuthenticated) {
    error.value = '请先登录'
    return
  }
  
  try {
    await courseStore.bookCourse(courseId)

    toast.success(t('schedule.bookSuccess'))
  } catch (err) {
    error.value = '预约失败，请稍后重试'
    console.error('Failed to book course:', err)
  }
}

const cancelBooking = async (courseId) => {
  try {
    await courseStore.cancelBooking(courseId)

    toast.success(t('schedule.cancelSuccess'))
    const courseIndex = courses.value.findIndex(c => c.id === courseId)
    if (courseIndex !== -1) {
      courses.value[courseIndex] = { 
        ...courses.value[courseIndex], 
        isBooked: false, 
        bookedCount: courses.value[courseIndex].bookedCount - 1,
        isFull: false
      }
    }
  } catch (err) {
    toast.error(t('errors.cancelBooking'))
    console.error('Failed to cancel booking:', err)
  }
}

const formatDate = (dateString) => {
  const date = new Date(dateString)
  const options = { month: 'long', day: 'numeric', weekday: 'long' }
  return date.toLocaleDateString('zh-CN', options)
}

const formatTime = (timeString) => {
  const date = new Date(timeString)
  return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
}

onMounted(() => {
  fetchCourses()
})
</script>

<style scoped>
.course-schedule {
  padding: 20px;
  max-width: 1200px;
  margin: 0 auto;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 30px;
}

.header h1 {
  color: #2c3e50;
  font-size: 2rem;
}

.filters {
  display: flex;
  gap: 15px;
}

.filters select {
  padding: 8px 12px;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 14px;
  background: white;
  cursor: pointer;
}

.schedule-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 20px;
}

.course-card {
  background: white;
  border-radius: 8px;
  padding: 20px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  transition: transform 0.2s, box-shadow 0.2s;
}

.course-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.course-card.booked {
  border-left: 4px solid #42b983;
}

.course-card.full {
  opacity: 0.7;
}

.course-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 15px;
}

.course-header h3 {
  margin: 0;
  color: #2c3e50;
  font-size: 1.2rem;
}

.category {
  background: #f0f2f5;
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 12px;
  color: #666;
}

.course-details {
  margin-bottom: 15px;
}

.course-details p {
  margin: 5px 0;
  color: #666;
  font-size: 14px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.course-details i {
  width: 16px;
  text-align: center;
}

.course-actions {
  display: flex;
  justify-content: flex-end;
  align-items: center;
  gap: 10px;
}

.btn {
  padding: 8px 16px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
  transition: background-color 0.2s;
}

.btn-primary {
  background: #42b983;
  color: white;
}

.btn-primary:hover {
  background: #3aa876;
}

.btn-secondary {
  background: #e74c3c;
  color: white;
}

.btn-secondary:hover {
  background: #c0392b;
}

.full-text {
  color: #e74c3c;
  font-weight: bold;
}

.loading {
  text-align: center;
  padding: 40px;
  color: #666;
}

.error {
  background: #fee;
  color: #c33;
  padding: 15px;
  border-radius: 4px;
  text-align: center;
  margin-top: 20px;
}

@media (max-width: 768px) {
  .header {
    flex-direction: column;
    gap: 20px;
    align-items: stretch;
  }

  .filters {
    justify-content: center;
  }

  .schedule-grid {
    grid-template-columns: 1fr;
  }
}
</style>