<template>
  <div class="modal-overlay" v-if="show" @click.self="closeModal">
    <div class="modal-container">
      <div class="modal-header">
        <h2>课程预约确认</h2>
        <button class="close-button" @click="closeModal">&times;</button>
      </div>

      <div class="modal-body">
        <div v-if="loading" class="loading-indicator">
          处理中...
        </div>

        <div v-else>
          <div v-if="error" class="error-message">
            {{ error }}
          </div>

          <div class="course-info">
            <h3>{{ currentCourse.name }}</h3>
            <p>时间: {{ formatSchedule(currentCourse.schedule) }}</p>
            <p>时长: {{ currentCourse.duration }}分钟</p>
            <p>当前预约人数: {{ bookingCount }}</p>
          <div class="cancellation-policy">
            <h4>取消政策</h4>
            <p>如需取消预约，请至少提前2小时操作</p>
            <p>未按时取消将计入违约记录</p>
          </div>
          </div>

          <div class="action-buttons">
            <button 
              class="confirm-button" 
              @click="handleBooking"
              :disabled="isBooked"
            >
              {{ isBooked ? '已预约' : '确认预约' }}
            </button>
            <button class="cancel-button" @click="closeModal">取消</button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { computed, ref } from 'vue';
import { useCourseStore } from '../stores/courseStore';
import { storeToRefs } from 'pinia';

export default {
  name: 'CourseBookingModal',
  
  props: {
    show: {
      type: Boolean,
      required: true
    },
    memberId: {
      type: String,
      required: true
    }
  },

  setup(props, { emit }) {
    const courseStore = useCourseStore();
    const { currentCourse, bookings, loading, error } = storeToRefs(courseStore);
    
    const isBooked = ref(false);

    const bookingCount = computed(() => {
      if (!currentCourse.value) return 0;
      return bookings.value[currentCourse.value.id] || 0;
    });

    const formatSchedule = (dateTime) => {
      if (!dateTime) return '';
      return new Date(dateTime).toLocaleString();
    };

    const closeModal = () => {
      emit('close');
    };

    const handleBooking = async () => {
      if (!currentCourse.value) return;
      
      try {
        await courseStore.bookCourse({
          courseId: currentCourse.value.id,
          memberId: props.memberId
        });
        isBooked.value = true;
      } catch (err) {
        console.error('Booking failed:', err);
      }
    };

    return {
      currentCourse,
      bookingCount,
      loading,
      error,
      isBooked,
      formatSchedule,
      closeModal,
      handleBooking
    };
  }
};
</script>

<style scoped>
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(0, 0, 0, 0.5);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1000;
}

.modal-container {
  background-color: white;
  border-radius: 8px;
  width: 500px;
  max-width: 90%;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
  overflow: hidden;
}

.modal-header {
  padding: 16px 24px;
  border-bottom: 1px solid #eee;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.modal-header h2 {
  margin: 0;
  font-size: 1.5rem;
}

.close-button {
  background: none;
  border: none;
  font-size: 1.5rem;
  cursor: pointer;
  padding: 0;
}

.modal-body {
  padding: 24px;
}

.loading-indicator,
.error-message {
  text-align: center;
  padding: 20px;
}

.error-message {
  color: #ff4444;
}

.course-info {
  margin-bottom: 24px;
}

.course-info h3 {
  .cancellation-policy {
    margin: 20px 0;
    padding: 15px;
    background-color: #f8f9fa;
    border-radius: 4px;
    border-left: 4px solid #ff9800;
  }

  .cancellation-policy h4 {
    margin-top: 0;
    color: #ff9800;
  }

  .cancellation-policy p {
    margin: 8px 0;
    font-size: 0.9rem;
    color: #666;
  }
  margin-top: 0;
}

.action-buttons {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}

.confirm-button,
.cancel-button {
  padding: 8px 16px;
  border-radius: 4px;
  cursor: pointer;
  font-weight: 500;
}

.confirm-button {
  background-color: #4CAF50;
  color: white;
  border: none;
}

.confirm-button:disabled {
  background-color: #81C784;
  cursor: not-allowed;
}

.cancel-button {
  background-color: white;
  border: 1px solid #ddd;
}

.cancel-button:hover {
  background-color: #f5f5f5;
}
</style>