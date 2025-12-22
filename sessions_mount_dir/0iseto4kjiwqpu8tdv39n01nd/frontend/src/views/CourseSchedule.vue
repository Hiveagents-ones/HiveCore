<template>
  <div class="course-schedule">
    <h1>课程表</h1>
    <div class="schedule-container">
      <div v-if="loading" class="loading">加载中...</div>
      <div v-else-if="error" class="error">{{ error }}</div>
      <div v-else class="schedule-grid">
        <div v-for="course in courses" :key="course.id" class="course-card">
          <h3>{{ course.name }}</h3>
          <p><strong>教练:</strong> {{ course.instructor }}</p>
          <p><strong>时间:</strong> {{ formatTime(course.start_time) }} - {{ formatTime(course.end_time) }}</p>
          <p><strong>容量:</strong> {{ course.booked_count }}/{{ course.capacity }}</p>
          <div class="course-actions">
            <button 
              v-if="!course.is_booked && course.booked_count < course.capacity"
              @click="bookCourse(course.id)"
              class="btn btn-primary"
            >
              预约
            </button>
            <button 
              v-if="course.is_booked"
              @click="cancelBooking(course.id)"
              class="btn btn-danger"
            >
              取消预约
            </button>
            <span v-if="course.booked_count >= course.capacity && !course.is_booked" class="full">
              已满
            </span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import axios from 'axios'

const courses = ref([])
const loading = ref(true)
const error = ref('')

const fetchCourses = async () => {
  try {
    const response = await axios.get('/api/v1/courses')
    courses.value = response.data
  } catch (err) {
    error.value = '获取课程表失败'
    console.error('Error fetching courses:', err)
  } finally {
    loading.value = false
  }
}

const bookCourse = async (courseId) => {
  try {
    await axios.post(`/api/v1/courses/${courseId}/book`)
    await fetchCourses()
  } catch (err) {
    error.value = '预约失败'
    console.error('Error booking course:', err)
  }
}

const cancelBooking = async (courseId) => {
  try {
    await axios.delete(`/api/v1/courses/${courseId}/book`)
    await fetchCourses()
  } catch (err) {
    error.value = '取消预约失败'
    console.error('Error canceling booking:', err)
  }
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

.schedule-container {
  margin-top: 20px;
}

.loading, .error {
  text-align: center;
  padding: 20px;
  font-size: 18px;
}

.error {
  color: #ff4444;
}

.schedule-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 20px;
}

.course-card {
  border: 1px solid #ddd;
  border-radius: 8px;
  padding: 15px;
  background: #fff;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

.course-card h3 {
  margin-top: 0;
  color: #333;
}

.course-card p {
  margin: 8px 0;
  color: #666;
}

.course-actions {
  margin-top: 15px;
  display: flex;
  align-items: center;
  gap: 10px;
}

.btn {
  padding: 8px 16px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
  transition: background-color 0.3s;
}

.btn-primary {
  background-color: #007bff;
  color: white;
}

.btn-primary:hover {
  background-color: #0056b3;
}

.btn-danger {
  background-color: #dc3545;
  color: white;
}

.btn-danger:hover {
  background-color: #c82333;
}

.full {
  color: #999;
  font-style: italic;
}
</style>