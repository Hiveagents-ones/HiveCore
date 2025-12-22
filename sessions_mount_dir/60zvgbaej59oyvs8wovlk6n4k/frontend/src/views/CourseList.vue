<template>
  <div class="course-list">
    <h1>{{ $t('courseList.title') }}</h1>
    
    <div class="filters">
      <select v-model="selectedCategory" @change="filterCourses">
        <option value="">{{ $t('courseList.allCategories') }}</option>
        <option v-for="category in categories" :key="category" :value="category">
          {{ category }}
        </option>
      </select>
      
      <input 
        type="date" 
        v-model="selectedDate" 
        @change="filterCourses"
        :min="today"
      />
    </div>

    <div v-if="loading" class="loading">
      {{ $t('common.loading') }}
    </div>

    <div v-else-if="filteredCourses.length === 0" class="no-courses">
      {{ $t('courseList.noCourses') }}
    </div>

    <div v-else>
      <div class="course-grid">
        <div 
          v-for="course in paginatedCourses" 
          :key="course.id" 
          class="course-card"
        >
        <div class="course-header">
          <h3>{{ course.name }}</h3>
          <span class="category">{{ course.category }}</span>
        </div>
        
        <div class="course-info">
          <p><i class="fas fa-clock"></i> {{ formatTime(course.start_time) }} - {{ formatTime(course.end_time) }}</p>
          <p><i class="fas fa-calendar"></i> {{ formatDate(course.date) }}</p>
          <p><i class="fas fa-user"></i> {{ course.instructor }}</p>
          <p><i class="fas fa-map-marker-alt"></i> {{ course.location }}</p>
        </div>
        
        <div class="course-availability">
          <span :class="['availability', getAvailabilityClass(course)]">
            {{ $t('courseList.slotsAvailable', { available: course.available_slots, total: course.max_slots }) }}
          </span>
        </div>
        
        <div class="course-actions">
          <button 
            v-if="course.is_booked"
            @click="cancelBooking(course.id)"
            class="btn btn-cancel"
            :disabled="cancelling"
          >
            {{ $t('courseList.cancelBooking') }}
          </button>
          <button 
            v-else
            @click="bookCourse(course.id)"
            class="btn btn-book"
            :disabled="booking || course.available_slots === 0"
          >
            {{ $t('courseList.bookNow') }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useCourseStore } from '@/stores/course'
import { useAuthStore } from '@/stores/auth'
import { formatDate, formatTime } from '@/utils/date'
import Pagination from '@/components/Pagination.vue'

const { t } = useI18n()
const courseStore = useCourseStore()
const authStore = useAuthStore()

const loading = ref(true)
const booking = ref(false)
const cancelling = ref(false)
const selectedCategory = ref('')
const selectedDate = ref('')
const today = computed(() => new Date().toISOString().split('T')[0])

const currentPage = ref(1)
const itemsPerPage = ref(9)

const courses = computed(() => courseStore.courses)
const categories = computed(() => [...new Set(courses.value.map(c => c.category))])

const filteredCourses = computed(() => {
  let filtered = courses.value
  
  if (selectedCategory.value) {
    filtered = filtered.filter(c => c.category === selectedCategory.value)
  }
  
  if (selectedDate.value) {
    filtered = filtered.filter(c => c.date === selectedDate.value)
  }
  
  return filtered.sort((a, b) => {
    const dateA = new Date(`${a.date} ${a.start_time}`)
    const dateB = new Date(`${b.date} ${b.start_time}`)
    return dateA - dateB
  })
})

const getAvailabilityClass = (course) => {
  const ratio = course.available_slots / course.max_slots
  if (ratio === 0) return 'full'
  if (ratio < 0.3) return 'low'
  if (ratio < 0.7) return 'medium'
  return 'high'
}

const filterCourses = () => {
  currentPage.value = 1
}

const bookCourse = async (courseId) => {
  if (!authStore.isAuthenticated) {
    // Redirect to login or show login modal
    return
  }
  
  booking.value = true
  try {
    await courseStore.bookCourse(courseId)
    // Show success message
  } catch (error) {
    // Show error message
  } finally {
    booking.value = false
  }
}

const cancelBooking = async (courseId) => {
  cancelling.value = true
  try {
    await courseStore.cancelBooking(courseId)
    // Show success message
  } catch (error) {
    // Show error message
  } finally {
    cancelling.value = false
  }
}

onMounted(async () => {
  try {
    await courseStore.fetchCourses()
  } catch (error) {
    // Handle error
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.course-list {
  padding: 2rem;
  max-width: 1200px;
  margin: 0 auto;
}

h1 {
  margin-bottom: 2rem;
  color: #2c3e50;
}

.filters {
  display: flex;
  gap: 1rem;
  margin-bottom: 2rem;
  flex-wrap: wrap;
}

.filters select,
.filters input {
  padding: 0.5rem 1rem;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 1rem;
}

.loading,
.no-courses {
  text-align: center;
  padding: 3rem;
  color: #666;
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
  transition: transform 0.2s, box-shadow 0.2s;
}

.course-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.course-header {
  display: flex;
  justify-content: space-between;
  align-items: start;
  margin-bottom: 1rem;
}

.course-header h3 {
  margin: 0;
  color: #2c3e50;
  font-size: 1.2rem;
}

.category {
  background: #e3f2fd;
  color: #1976d2;
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
  font-size: 0.875rem;
}

.course-info {
  margin-bottom: 1rem;
}

.course-info p {
  margin: 0.5rem 0;
  color: #666;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.course-info i {
  width: 20px;
  color: #999;
}

.course-availability {
  margin-bottom: 1rem;
}

.availability {
  font-weight: 500;
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
  display: inline-block;
}

.availability.high {
  background: #e8f5e9;
  color: #2e7d32;
}

.availability.medium {
  background: #fff3e0;
  color: #f57c00;
}

.availability.low {
  background: #ffebee;
  color: #c62828;
}

.availability.full {
  background: #f5f5f5;
  color: #666;
}

.course-actions {
  display: flex;
  justify-content: flex-end;
}

.btn {
  padding: 0.5rem 1rem;
  border: none;
  border-radius: 4px;
  font-size: 1rem;
  cursor: pointer;
  transition: background-color 0.2s;
}

.btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-book {
  background: #4caf50;
  color: white;
}

.btn-book:hover:not(:disabled) {
  background: #45a049;
}

.btn-cancel {
  background: #f44336;
  color: white;
}

.btn-cancel:hover:not(:disabled) {
  background: #da190b;
}

@media (max-width: 768px) {
  .course-list {
    padding: 1rem;
  }
  
  .course-grid {
    grid-template-columns: 1fr;
  }
}
</style>

# ========== AUTO-APPENDED CODE (编辑失败自动追加) ==========
# [AUTO-APPENDED] Failed to replace, adding new code:
const currentPage = ref(1)
const itemsPerPage = ref(9)

const filteredCourses = computed(() => {
  let filtered = courses.value

  if (selectedCategory.value) {
    filtered = filtered.filter(c => c.category === selectedCategory.value)
  }

  if (selectedDate.value) {
    filtered = filtered.filter(c => c.date === selectedDate.value)
  }

  return filtered.sort((a, b) => {
    const dateA = new Date(`${a.date} ${a.start_time}`)
    const dateB = new Date(`${b.date} ${b.start_time}`)
    return dateA - dateB
  })
})

const paginatedCourses = computed(() => {
  const start = (currentPage.value - 1) * itemsPerPage.value
  const end = start + itemsPerPage.value
  return filteredCourses.value.slice(start, end)
})

const totalPages = computed(() => {
  return Math.ceil(filteredCourses.value.length / itemsPerPage.value)
})

const paginatedCourses = computed(() => {
  const start = (currentPage.value - 1) * itemsPerPage.value
  const end = start + itemsPerPage.value
  return filteredCourses.value.slice(start, end)
})

const totalPages = computed(() => {
  return Math.ceil(filteredCourses.value.length / itemsPerPage.value)
})

const paginatedCourses = computed(() => {
  const start = (currentPage.value - 1) * itemsPerPage.value
  const end = start + itemsPerPage.value
  return filteredCourses.value.slice(start, end)
})

const totalPages = computed(() => {
  return Math.ceil(filteredCourses.value.length / itemsPerPage.value)
})

const paginatedCourses = computed(() => {
  const start = (currentPage.value - 1) * itemsPerPage.value
  const end = start + itemsPerPage.value
  return filteredCourses.value.slice(start, end)
})

const totalPages = computed(() => {
  return Math.ceil(filteredCourses.value.length / itemsPerPage.value)
})

# [AUTO-APPENDED] Failed to insert:

    <Pagination
      v-if="totalPages > 1"
      :current-page="currentPage"
      :total-pages="totalPages"
      @page-changed="currentPage = $event"
    />

# ========== AUTO-APPENDED CODE (编辑失败自动追加) ==========
# [AUTO-APPENDED] Failed to insert:

    <Pagination
      v-if="totalPages > 1"
      :current-page="currentPage"
      :total-pages="totalPages"
      @page-changed="currentPage = $event"
    />

# ========== AUTO-APPENDED CODE (编辑失败自动追加) ==========
# [AUTO-APPENDED] Failed to insert:

    <Pagination
      v-if="totalPages > 1"
      :current-page="currentPage"
      :total-pages="totalPages"
      @page-changed="currentPage = $event"
    />