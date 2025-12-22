<template>
  <div class="course-list">
    <div class="header">
      <h1>课程列表</h1>
      <div class="filters">
        <div class="search-box">
          <input
            type="text"
            v-model="searchQuery"
            placeholder="搜索课程名称..."
            @input="filterCourses"
          />
        </div>
        <div class="category-filter">
          <select v-model="selectedCategory" @change="filterCourses">
            <option value="">全部分类</option>
            <option v-for="category in categories" :key="category" :value="category">
              {{ category }}
            </option>
          </select>
        </div>
      </div>
    </div>

    <div class="courses-grid" v-if="filteredCourses.length > 0">
      <div
        v-for="course in filteredCourses"
        :key="course.id"
        class="course-card"
      >
        <div class="course-header">
          <h3>{{ course.name }}</h3>
          <span class="category-badge">{{ course.category }}</span>
        </div>
        <div class="course-info">
          <p class="instructor">教练: {{ course.instructor }}</p>
          <p class="schedule">
            时间: {{ formatDateTime(course.start_time) }} - {{ formatTime(course.end_time) }}
          </p>
          <p class="duration">时长: {{ course.duration }} 分钟</p>
          <p class="location">地点: {{ course.location }}</p>
        </div>
        <div class="course-footer">
          <div class="availability">
            <span class="remaining" :class="getAvailabilityClass(course.remaining_slots, course.max_capacity)">
              剩余名额: {{ course.remaining_slots }}/{{ course.max_capacity }}
            </span>
          </div>
          <button
            class="book-btn"
            :disabled="course.remaining_slots === 0 || isBooking"
            @click="bookCourse(course.id)"
          >
            {{ course.remaining_slots === 0 ? '已满员' : '立即预约' }}
          </button>
        </div>
      </div>
    </div>

    <div v-else class="no-courses">
      <p>暂无符合条件的课程</p>
    </div>

    <div v-if="loading" class="loading">
      <p>加载中...</p>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { useCourseStore } from '@/stores/course'
import { useBookingStore } from '@/stores/booking'
import { useRouter } from 'vue-router'

const router = useRouter()
const courseStore = useCourseStore()
const bookingStore = useBookingStore()

const courses = ref([])
const loading = ref(true)
const isBooking = ref(false)
const searchQuery = ref('')
const selectedCategory = ref('')

const categories = computed(() => {
  const cats = new Set(courses.value.map(course => course.category))
  return Array.from(cats)
})

const filteredCourses = computed(() => {
  let filtered = courses.value

  if (searchQuery.value) {
    filtered = filtered.filter(course =>
      course.name.toLowerCase().includes(searchQuery.value.toLowerCase())
    )
  }

  if (selectedCategory.value) {
    filtered = filtered.filter(course => course.category === selectedCategory.value)
  }

  return filtered
})

const fetchCourses = async () => {
  try {
    loading.value = true
    const response = await courseStore.fetchCourses()
    courses.value = response.data
  } catch (error) {
    console.error('获取课程列表失败:', error)
  } finally {
    loading.value = false
  }
}

const bookCourse = async (courseId) => {
  try {
    isBooking.value = true
    await bookingStore.createBooking({ course_id: courseId })
    
    // 更新课程剩余名额
    const courseIndex = courses.value.findIndex(c => c.id === courseId)
    if (courseIndex !== -1) {
      courses.value[courseIndex].remaining_slots -= 1
    }
    
    alert('预约成功！')
  } catch (error) {
    console.error('预约失败:', error)
    alert(error.response?.data?.detail || '预约失败，请重试')
  } finally {
    isBooking.value = false
  }
}

const filterCourses = () => {
  // 触发计算属性更新
}

const formatDateTime = (dateTimeStr) => {
  const date = new Date(dateTimeStr)
  return date.toLocaleDateString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}

const formatTime = (dateTimeStr) => {
  const date = new Date(dateTimeStr)
  return date.toLocaleTimeString('zh-CN', {
    hour: '2-digit',
    minute: '2-digit'
  })
}

const getAvailabilityClass = (remaining, max) => {
  const ratio = remaining / max
  if (ratio === 0) return 'full'
  if (ratio < 0.2) return 'low'
  if (ratio < 0.5) return 'medium'
  return 'high'
}

onMounted(() => {
  fetchCourses()
})
</script>

<style scoped>
.course-list {
  max-width: 1200px;
  margin: 0 auto;
  padding: 20px;
}

.header {
  margin-bottom: 30px;
}

.header h1 {
  color: #333;
  margin-bottom: 20px;
}

.filters {
  display: flex;
  gap: 20px;
  flex-wrap: wrap;
}

.search-box input {
  padding: 10px 15px;
  border: 1px solid #ddd;
  border-radius: 5px;
  width: 300px;
  font-size: 14px;
}

.category-filter select {
  padding: 10px 15px;
  border: 1px solid #ddd;
  border-radius: 5px;
  font-size: 14px;
  background-color: white;
  cursor: pointer;
}

.courses-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
  gap: 20px;
}

.course-card {
  border: 1px solid #e0e0e0;
  border-radius: 10px;
  padding: 20px;
  background: white;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  transition: transform 0.2s, box-shadow 0.2s;
}

.course-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.15);
}

.course-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 15px;
}

.course-header h3 {
  margin: 0;
  color: #333;
  font-size: 18px;
}

.category-badge {
  background-color: #f0f0f0;
  color: #666;
  padding: 4px 8px;
  border-radius: 15px;
  font-size: 12px;
}

.course-info {
  margin-bottom: 20px;
}

.course-info p {
  margin: 8px 0;
  color: #666;
  font-size: 14px;
}

.course-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.availability {
  font-size: 14px;
}

.remaining {
  font-weight: bold;
}

.remaining.high {
  color: #4caf50;
}

.remaining.medium {
  color: #ff9800;
}

.remaining.low {
  color: #f44336;
}

.remaining.full {
  color: #9e9e9e;
}

.book-btn {
  padding: 8px 20px;
  background-color: #4caf50;
  color: white;
  border: none;
  border-radius: 5px;
  cursor: pointer;
  font-size: 14px;
  transition: background-color 0.2s;
}

.book-btn:hover:not(:disabled) {
  background-color: #45a049;
}

.book-btn:disabled {
  background-color: #ccc;
  cursor: not-allowed;
}

.no-courses {
  text-align: center;
  padding: 40px;
  color: #666;
}

.loading {
  text-align: center;
  padding: 40px;
  color: #666;
}

@media (max-width: 768px) {
  .courses-grid {
    grid-template-columns: 1fr;
  }
  
  .filters {
    flex-direction: column;
  }
  
  .search-box input {
    width: 100%;
  }
}
</style>