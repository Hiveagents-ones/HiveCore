<template>
  <div class="course-detail-container">
    <div v-if="loading" class="loading-indicator">
      <p>加载中...</p>
    </div>

    <div v-else-if="error" class="error-message">
      <p>{{ error }}</p>
      <button @click="fetchCourseData">重试</button>
    </div>

    <div v-else-if="course" class="course-detail">
      <div class="course-header">
        <h1>{{ course.name }}</h1>
        <p class="coach-name">教练: {{ course.coach_name }}</p>
      </div>

      <div class="course-content">
        <div class="course-info">
          <div class="info-section">
            <h3>课程描述</h3>
            <p>{{ course.description }}</p>
          </div>

          <div class="info-section">
            <h3>课程时间</h3>
            <p>开始时间: {{ formatDateTime(course.start_time) }}</p>
            <p>结束时间: {{ formatDateTime(course.end_time) }}</p>
            <p>时长: {{ calculateDuration(course.start_time, course.end_time) }} 分钟</p>
          </div>

          <div class="info-section">
            <h3>课程状态</h3>
            <p>剩余名额: {{ course.available_slots }}</p>
            <p>总容量: {{ course.total_slots }}</p>
          </div>
        </div>

        <div class="action-section">
          <button 
            @click="handleBooking" 
            :disabled="course.available_slots <= 0 || isBooked" 
            class="book-button"
          >
            {{ isBooked ? '已预约' : course.available_slots <= 0 ? '已满员' : '立即预约' }}
          </button>
          
          <div v-if="bookingSuccess" class="success-message">
            预约成功！
          </div>
        </div>
      </div>
    </div>

    <div v-else class="no-course">
      <p>未找到课程信息</p>
    </div>
  </div>
</template>

<script>
import { computed, onMounted, ref } from 'vue';
import { useRoute } from 'vue-router';
import { useCourseStore } from '../stores/courseStore';
import { format } from 'date-fns';

export default {
  name: 'CourseDetailView',
  
  setup() {
    const route = useRoute();
    const courseStore = useCourseStore();
    
    const bookingSuccess = ref(false);
    const memberId = ref(1); // 假设当前会员ID为1，实际项目中应从登录状态获取
    
    const course = computed(() => courseStore.selectedCourse);
    const loading = computed(() => courseStore.loading);
    const error = computed(() => courseStore.error);
    const isBooked = computed(() => {
      return courseStore.memberBookings.some(
        booking => booking.course_id === parseInt(route.params.id)
      );
    });
    
    const fetchCourseData = async () => {
      await courseStore.fetchCourseById(route.params.id);
    };
    
    const formatDateTime = (dateTime) => {
      return format(new Date(dateTime), 'yyyy-MM-dd HH:mm');
    };
    
    const calculateDuration = (startTime, endTime) => {
      const start = new Date(startTime);
      const end = new Date(endTime);
      return Math.round((end - start) / (1000 * 60));
    };
    
    const handleBooking = async () => {
      try {
        await courseStore.bookCourse(route.params.id, memberId.value);
        bookingSuccess.value = true;
        setTimeout(() => bookingSuccess.value = false, 3000);
      } catch (err) {
        console.error('预约失败:', err);
      }
    };
    
    onMounted(() => {
      fetchCourseData();
    });
    
    return {
      course,
      loading,
      error,
      isBooked,
      bookingSuccess,
      formatDateTime,
      calculateDuration,
      handleBooking,
      fetchCourseData
    };
  }
};
</script>

<style scoped>
.course-detail-container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 2rem;
}

.loading-indicator,
.error-message,
.no-course {
  text-align: center;
  padding: 2rem;
}

.error-message button {
  margin-top: 1rem;
  padding: 0.5rem 1rem;
  background-color: #42b983;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

.course-header {
  margin-bottom: 2rem;
  text-align: center;
}

.course-header h1 {
  font-size: 2rem;
  margin-bottom: 0.5rem;
}

.coach-name {
  color: #666;
  font-size: 1.2rem;
}

.course-content {
  display: flex;
  flex-wrap: wrap;
  gap: 2rem;
}

.course-info {
  flex: 2;
  min-width: 300px;
}

.info-section {
  margin-bottom: 2rem;
  padding: 1.5rem;
  background-color: #f9f9f9;
  border-radius: 8px;
}

.info-section h3 {
  margin-top: 0;
  margin-bottom: 1rem;
  color: #42b983;
}

.action-section {
  flex: 1;
  min-width: 250px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}

.book-button {
  padding: 1rem 2rem;
  font-size: 1.2rem;
  background-color: #42b983;
  color: white;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  transition: background-color 0.3s;
}

.book-button:hover:not(:disabled) {
  background-color: #3aa876;
}

.book-button:disabled {
  background-color: #cccccc;
  cursor: not-allowed;
}

.success-message {
  margin-top: 1rem;
  padding: 0.5rem 1rem;
  background-color: #dff0d8;
  color: #3c763d;
  border-radius: 4px;
}
</style>