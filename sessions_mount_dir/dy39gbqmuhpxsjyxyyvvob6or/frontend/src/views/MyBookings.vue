<template>
  <div class="my-bookings">
    <h1>我的预约</h1>
    
    <div v-if="loading" class="loading">
      加载中...
    </div>
    
    <div v-else-if="bookings.length === 0" class="no-bookings">
      您还没有任何课程预约
    </div>
    
    <div v-else class="bookings-list">
      <div v-for="booking in bookings" :key="booking.id" class="booking-card">
        <div class="booking-info">
          <h3>{{ booking.name }}</h3>
          <p>{{ booking.description }}</p>
          <p>时间: {{ formatDateTime(booking.start_time) }} - {{ formatDateTime(booking.end_time) }}</p>
        </div>
        <button 
          @click="cancelBooking(booking.id)" 
          class="cancel-btn"
        >
          取消预约
        </button>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, onMounted } from 'vue';
import { getCourses, cancelCourseBooking } from '../api/courses';

export default {
  name: 'MyBookings',
  
  setup() {
    const bookings = ref([]);
    const loading = ref(true);
    
    const fetchBookings = async () => {
      try {
        loading.value = true;
        const data = await getCourses();
        bookings.value = data;
      } catch (error) {
        console.error('Failed to fetch bookings:', error);
      } finally {
        loading.value = false;
      }
    };
    
    const cancelBooking = async (courseId) => {
      try {
        if (confirm('确定要取消这个预约吗？')) {
          await cancelCourseBooking(courseId);
          await fetchBookings();
        }
      } catch (error) {
        console.error('Failed to cancel booking:', error);
        alert('取消预约失败，请稍后重试');
      }
    };
    
    const formatDateTime = (dateTimeString) => {
      const options = { 
        year: 'numeric', 
        month: '2-digit', 
        day: '2-digit',
        hour: '2-digit', 
        minute: '2-digit',
        hour12: false
      };
      return new Date(dateTimeString).toLocaleString('zh-CN', options);
    };
    
    onMounted(() => {
      fetchBookings();
    });
    
    return {
      bookings,
      loading,
      cancelBooking,
      formatDateTime
    };
  }
};
</script>

<style scoped>
.my-bookings {
  padding: 20px;
  max-width: 800px;
  margin: 0 auto;
}

h1 {
  text-align: center;
  margin-bottom: 30px;
  color: #2c3e50;
}

.loading, .no-bookings {
  text-align: center;
  padding: 40px;
  font-size: 18px;
  color: #666;
}

.bookings-list {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.booking-card {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  background-color: #fff;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
}

.booking-info h3 {
  margin: 0 0 10px 0;
  color: #2c3e50;
}

.booking-info p {
  margin: 5px 0;
  color: #666;
}

.cancel-btn {
  padding: 8px 16px;
  background-color: #ff4757;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  transition: background-color 0.3s;
}

.cancel-btn:hover {
  background-color: #ff6b81;
}
</style>