<template>
  <div class="course-list-view">
    <div class="header">
      <h1>{{ $t('courses.title') }}</h1>
      <div class="filters">
        <select v-model="selectedCategory" @change="filterCourses">
          <option value="">{{ $t('courses.allCategories') }}</option>
          <option v-for="category in categories" :key="category" :value="category">
            {{ $t(`courses.categories.${category}`) }}
          </option>
        </select>
        <input 
          type="date" 
          v-model="selectedDate" 
          @change="filterCourses"
          :min="today"
        />
      </div>
    </div>

    <div v-if="isLoading" class="loading">
      {{ $t('common.loading') }}
    </div>

    <div v-else-if="error" class="error">
      {{ error }}
    </div>

    <div v-else class="course-grid">
      <div 
        v-for="course in filteredCourses" 
        :key="course.id" 
        class="course-card"
      >
        <div class="course-header">
          <h3>{{ course.name }}</h3>
          <span class="category">{{ $t(`courses.categories.${course.category}`) }}</span>
        </div>
        
        <div class="course-info">
          <div class="info-item">
            <i class="icon-calendar"></i>
            <span>{{ formatDate(course.date) }}</span>
          </div>
          <div class="info-item">
            <i class="icon-clock"></i>
            <span>{{ course.time }}</span>
          </div>
          <div class="info-item">
            <i class="icon-user"></i>
            <span>{{ course.instructor }}</span>
          </div>
          <div class="info-item">
            <i class="icon-users"></i>
            <span>{{ $t('courses.spotsAvailable', { available: course.available_spots, total: course.max_spots }) }}</span>
          </div>
        </div>

        <div class="course-actions">
          <button 
            v-if="isAuthenticated && !course.is_booked && course.available_spots > 0"
            @click="bookCourse(course.id)"
            class="btn btn-primary"
            :disabled="isBooking"
          >
            {{ $t('courses.book') }}
          </button>
          <button 
            v-if="isAuthenticated && course.is_booked"
            @click="cancelBooking(course.id)"
            class="btn btn-secondary"
            :disabled="isCancelling"
          >
            {{ $t('courses.cancel') }}
          </button>
          <span v-if="!isAuthenticated" class="login-prompt">
            {{ $t('courses.loginRequired') }}
          </span>
          <span v-if="course.available_spots === 0" class="full-course">
            {{ $t('courses.full') }}
          </span>
        </div>
      </div>
    </div>

    <div v-if="filteredCourses.length === 0 && !isLoading" class="no-results">
      {{ $t('courses.noResults') }}
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useAuthStore } from '@/stores/auth'
import { courseApi } from '@/services/api'

const { t } = useI18n()
const authStore = useAuthStore()

// State
const courses = ref([])
const isLoading = ref(false)
const error = ref(null)
const isBooking = ref(false)
const isCancelling = ref(false)
const selectedCategory = ref('')
const selectedDate = ref('')

// Computed
const isAuthenticated = computed(() => authStore.isAuthenticated)
const today = computed(() => new Date().toISOString().split('T')[0])

const categories = computed(() => {
  const cats = new Set(courses.value.map(c => c.category))
  return Array.from(cats)
})

const filteredCourses = computed(() => {
  let filtered = courses.value
  
  if (selectedCategory.value) {
    filtered = filtered.filter(c => c.category === selectedCategory.value)
  }
  
  if (selectedDate.value) {
    filtered = filtered.filter(c => c.date === selectedDate.value)
  }
  
  return filtered.sort((a, b) => {
    const dateA = new Date(`${a.date} ${a.time}`)
    const dateB = new Date(`${b.date} ${b.time}`)
    return dateA - dateB
  })
})

// Methods
const fetchCourses = async () => {
  isLoading.value = true
  error.value = null
  try {
    const response = await courseApi.getCourses()
    courses.value = response.data
  } catch (err) {
    error.value = err.response?.data?.detail || t('courses.fetchError')
  } finally {
    isLoading.value = false
  }
}

const bookCourse = async (courseId) => {
  if (!isAuthenticated.value) return
  
  isBooking.value = true
  try {
    await courseApi.bookCourse(courseId)
    // Update the course in the list
    const course = courses.value.find(c => c.id === courseId)
    if (course) {
      course.is_booked = true
      course.available_spots -= 1
    }
  } catch (err) {
    error.value = err.response?.data?.detail || t('courses.bookingError')
  } finally {
    isBooking.value = false
  }
}

const cancelBooking = async (courseId) => {
  if (!isAuthenticated.value) return
  
  isCancelling.value = true
  try {
    await courseApi.cancelBooking(courseId)
    // Update the course in the list
    const course = courses.value.find(c => c.id === courseId)
    if (course) {
      course.is_booked = false
      course.available_spots += 1
    }
  } catch (err) {
    error.value = err.response?.data?.detail || t('courses.cancelError')
  } finally {
    isCancelling.value = false
  }
}

const formatDate = (dateString) => {
  const date = new Date(dateString)
  return date.toLocaleDateString()
}

const filterCourses = () => {
  // Trigger reactivity
  // The computed property will handle the filtering
}

// Lifecycle
onMounted(() => {
  fetchCourses()
})
</script>

<style scoped>
.course-list-view {
  padding: 2rem;
  max-width: 1200px;
  margin: 0 auto;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 2rem;
  flex-wrap: wrap;
  gap: 1rem;
}

.header h1 {
  margin: 0;
  color: #2c3e50;
}

.filters {
  display: flex;
  gap: 1rem;
  align-items: center;
}

.filters select,
.filters input {
  padding: 0.5rem;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 1rem;
}

.loading,
.error {
  text-align: center;
  padding: 2rem;
  font-size: 1.2rem;
}

.error {
  color: #e74c3c;
}

.course-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 1.5rem;
}

.course-card {
  background: white;
  border-radius: 8px;
  padding: 1.5rem;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  transition: transform 0.2s;
}

.course-card:hover {
  transform: translateY(-2px);
}

.course-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
}

.course-header h3 {
  margin: 0;
  color: #2c3e50;
}

.category {
  background: #3498db;
  color: white;
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
  font-size: 0.875rem;
}

.course-info {
  margin-bottom: 1rem;
}

.info-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.5rem;
  color: #555;
}

.info-item i {
  width: 16px;
  text-align: center;
}

.course-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.btn {
  padding: 0.5rem 1rem;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 1rem;
  transition: background-color 0.2s;
}

.btn-primary {
  background: #27ae60;
  color: white;
}

.btn-primary:hover:not(:disabled) {
  background: #229954;
}

.btn-secondary {
  background: #e74c3c;
  color: white;
}

.btn-secondary:hover:not(:disabled) {
  background: #c0392b;
}

.btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.login-prompt,
.full-course {
  color: #7f8c8d;
  font-size: 0.875rem;
}

.no-results {
  text-align: center;
  padding: 2rem;
  color: #7f8c8d;
}

@media (max-width: 768px) {
  .course-list-view {
    padding: 1rem;
  }
  
  .header {
    flex-direction: column;
    align-items: stretch;
  }
  
  .filters {
    flex-direction: column;
    align-items: stretch;
  }
  
  .course-grid {
    grid-template-columns: 1fr;
  }
}
</style>