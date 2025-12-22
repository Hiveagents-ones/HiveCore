<template>
  <div class="course-detail">
    <div v-if="loading" class="loading">Loading...</div>
    <div v-else-if="error" class="error">{{ error }}</div>
    <div v-else-if="course" class="course-content">
      <h1>{{ course.name }}</h1>
      <p><strong>Coach:</strong> {{ course.coach }}</p>
      <p><strong>Time:</strong> {{ course.time }}</p>
      <p><strong>Duration:</strong> {{ course.duration }} minutes</p>
      <p><strong>Available Slots:</strong> {{ course.availableSlots }}</p>
      <p><strong>Description:</strong> {{ course.description }}</p>
      
      <button 
        @click="handleBooking" 
        :disabled="isBooking || course.availableSlots === 0"
        class="booking-button"
      >
        {{ isBooking ? 'Booking...' : course.availableSlots > 0 ? 'Book Now' : 'Fully Booked' }}
      </button>
      
      <div v-if="bookingError" class="booking-error">
        {{ bookingError }}
      </div>
      
      <div v-if="bookingSuccess" class="booking-success">
        Booking successful!
      </div>
    </div>
    <div v-else class="not-found">
      Course not found.
    </div>
  </div>
</template>

<script>
import { ref, computed, onMounted } from 'vue';
import { useRoute } from 'vue-router';
import { useBookingStore } from '../stores/booking.js';

export default {
  name: 'CourseDetailView',
  setup() {
    const route = useRoute();
    const bookingStore = useBookingStore();
    
    const isBooking = ref(false);
    const bookingError = ref(null);
    const bookingSuccess = ref(false);
    
    const courseId = computed(() => parseInt(route.params.id));
    const course = computed(() => bookingStore.getCourseById(courseId.value));
    const loading = computed(() => bookingStore.loading);
    const error = computed(() => bookingStore.error);
    
    const handleBooking = async () => {
      if (!course.value || course.value.availableSlots === 0) return;
      
      isBooking.value = true;
      bookingError.value = null;
      bookingSuccess.value = false;
      
      try {
        // In a real app, you would get userId from authentication
        const userId = 1; // Mock user ID
        await bookingStore.createBooking(courseId.value, userId);
        bookingSuccess.value = true;
        setTimeout(() => {
          bookingSuccess.value = false;
        }, 3000);
      } catch (err) {
        bookingError.value = bookingStore.error || 'Booking failed. Please try again.';
      } finally {
        isBooking.value = false;
      }
    };
    
    onMounted(async () => {
      if (!bookingStore.courses.length) {
        await bookingStore.fetchCourses();
      }
    });
    
    return {
      course,
      loading,
      error,
      isBooking,
      bookingError,
      bookingSuccess,
      handleBooking
    };
  }
};
</script>

<style scoped>
.course-detail {
  max-width: 800px;
  margin: 0 auto;
  padding: 20px;
}

.course-content {
  background: #f9f9f9;
  padding: 20px;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.course-content h1 {
  margin-top: 0;
  color: #333;
}

.course-content p {
  margin: 10px 0;
  line-height: 1.6;
}

.booking-button {
  background-color: #4CAF50;
  color: white;
  padding: 10px 20px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 16px;
  margin-top: 20px;
  transition: background-color 0.3s;
}

.booking-button:hover:not(:disabled) {
  background-color: #45a049;
}

.booking-button:disabled {
  background-color: #cccccc;
  cursor: not-allowed;
}

.booking-error {
  color: #d32f2f;
  margin-top: 10px;
  padding: 10px;
  background-color: #ffebee;
  border-radius: 4px;
}

.booking-success {
  color: #388e3c;
  margin-top: 10px;
  padding: 10px;
  background-color: #e8f5e9;
  border-radius: 4px;
}

.loading, .error, .not-found {
  text-align: center;
  padding: 20px;
  font-size: 18px;
}

.error {
  color: #d32f2f;
}

.not-found {
  color: #757575;
}
</style>