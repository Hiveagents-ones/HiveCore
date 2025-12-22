<template>
  <div class="course-list-view">
    <h1>Available Courses</h1>
    
    <div class="filters">
      <input 
        type="text" 
        v-model="searchQuery" 
        placeholder="Search courses..."
        class="search-input"
      />
      <select v-model="selectedCategory" class="category-select">
        <option value="">All Categories</option>
        <option v-for="category in categories" :key="category" :value="category">
          {{ category }}
        </option>
      </select>
    </div>

    <div v-if="loading" class="loading">Loading courses...</div>
    <div v-if="error" class="error">{{ error }}</div>

    <div v-if="!loading && !error" class="course-grid">
      <div 
        v-for="course in paginatedCourses" 
        :key="course.id" 
        class="course-card"
      >
        <h3>{{ course.name }}</h3>
        <p class="category">{{ course.category }}</p>
        <p class="instructor">Instructor: {{ course.instructor }}</p>
        <p class="schedule">{{ course.schedule }}</p>
        <p class="slots">Available Slots: {{ course.availableSlots }}</p>
        <button 
          @click="bookCourse(course.id)"
          :disabled="course.availableSlots === 0 || loading"
          class="book-button"
        >
          {{ course.availableSlots === 0 ? 'Full' : 'Book Now' }}
        </button>
      </div>
    </div>

    <div v-if="!loading && !error && filteredCourses.length > itemsPerPage" class="pagination">
      <button 
        @click="currentPage--" 
        :disabled="currentPage === 1"
        class="page-button"
      >
        Previous
      </button>
      <span class="page-info">Page {{ currentPage }} of {{ totalPages }}</span>
      <button 
        @click="currentPage++" 
        :disabled="currentPage === totalPages"
        class="page-button"
      >
        Next
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue';
import { useBookingStore } from '../stores/booking.js';

const bookingStore = useBookingStore();
const searchQuery = ref('');
const selectedCategory = ref('');
const currentPage = ref(1);
const itemsPerPage = 6;

// Mock user ID - in a real app, this would come from authentication
const userId = ref('user123');

onMounted(() => {
  bookingStore.fetchCourses();
  bookingStore.fetchBookings(userId.value);
});

const categories = computed(() => {
  const cats = new Set(bookingStore.courses.map(course => course.category));
  return Array.from(cats);
});

const filteredCourses = computed(() => {
  let courses = bookingStore.availableCourses;
  
  if (searchQuery.value) {
    courses = courses.filter(course => 
      course.name.toLowerCase().includes(searchQuery.value.toLowerCase()) ||
      course.instructor.toLowerCase().includes(searchQuery.value.toLowerCase())
    );
  }
  
  if (selectedCategory.value) {
    courses = courses.filter(course => course.category === selectedCategory.value);
  }
  
  return courses;
});

const totalPages = computed(() => {
  return Math.ceil(filteredCourses.value.length / itemsPerPage);
});

const paginatedCourses = computed(() => {
  const start = (currentPage.value - 1) * itemsPerPage;
  const end = start + itemsPerPage;
  return filteredCourses.value.slice(start, end);
});

watch([searchQuery, selectedCategory], () => {
  currentPage.value = 1;
});

const bookCourse = async (courseId) => {
  try {
    await bookingStore.createBooking(courseId, userId.value);
    alert('Booking successful!');
  } catch (error) {
    alert(bookingStore.error || 'Failed to book course');
  }
};
</script>

<style scoped>
.course-list-view {
  max-width: 1200px;
  margin: 0 auto;
  padding: 20px;
}

h1 {
  text-align: center;
  color: #333;
  margin-bottom: 30px;
}

.filters {
  display: flex;
  gap: 15px;
  margin-bottom: 30px;
  justify-content: center;
}

.search-input {
  padding: 10px 15px;
  border: 1px solid #ddd;
  border-radius: 5px;
  width: 300px;
  font-size: 16px;
}

.category-select {
  padding: 10px 15px;
  border: 1px solid #ddd;
  border-radius: 5px;
  font-size: 16px;
  cursor: pointer;
}

.loading, .error {
  text-align: center;
  padding: 20px;
  font-size: 18px;
}

.error {
  color: #ff4444;
}

.course-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 20px;
  margin-bottom: 30px;
}

.course-card {
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  padding: 20px;
  background: white;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
  transition: transform 0.2s;
}

.course-card:hover {
  transform: translateY(-5px);
}

.course-card h3 {
  margin: 0 0 10px 0;
  color: #2c3e50;
}

.category {
  color: #3498db;
  font-weight: bold;
  margin-bottom: 10px;
}

.instructor, .schedule {
  color: #666;
  margin-bottom: 5px;
}

.slots {
  font-weight: bold;
  margin-bottom: 15px;
}

.book-button {
  background-color: #27ae60;
  color: white;
  border: none;
  padding: 10px 20px;
  border-radius: 5px;
  cursor: pointer;
  font-size: 16px;
  width: 100%;
  transition: background-color 0.2s;
}

.book-button:hover:not(:disabled) {
  background-color: #229954;
}

.book-button:disabled {
  background-color: #95a5a6;
  cursor: not-allowed;
}

.pagination {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 15px;
}

.page-button {
  padding: 8px 16px;
  border: 1px solid #ddd;
  background: white;
  border-radius: 5px;
  cursor: pointer;
  transition: all 0.2s;
}

.page-button:hover:not(:disabled) {
  background-color: #f0f0f0;
}

.page-button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.page-info {
  font-size: 16px;
  color: #666;
}
</style>