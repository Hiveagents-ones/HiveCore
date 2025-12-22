<template>
  <div v-if="isVisible" class="modal-overlay" @click="closeModal">
    <div class="modal-content" @click.stop>
      <div class="modal-header">
        <h2>确认预约</h2>
        <button class="close-btn" @click="closeModal">&times;</button>
      </div>
      <div class="modal-body">
        <p>您确定要预约以下课程吗？</p>
        <div class="course-info">
          <h3>{{ course.name }}</h3>
          <p><strong>教练：</strong>{{ course.coach }}</p>
          <p><strong>时间：</strong>{{ formatDateTime(course.start_time) }}</p>
          <p><strong>剩余名额：</strong>{{ course.remaining_slots }}</p>
        </div>
      </div>
      <div class="modal-footer">
        <button class="btn btn-cancel" @click="closeModal">取消</button>
        <button class="btn btn-confirm" @click="confirmBooking" :disabled="isLoading">
          {{ isLoading ? '预约中...' : '确认预约' }}
        </button>
      </div>
    </div>
  </div>
</template>

<script>
import { ref } from 'vue';
import { useBookingStore } from '../stores/booking';

export default {
  name: 'BookingConfirmModal',
  props: {
    isVisible: {
      type: Boolean,
      required: true
    },
    course: {
      type: Object,
      required: true
    }
  },
  emits: ['close', 'success'],
  setup(props, { emit }) {
    const bookingStore = useBookingStore();
    const isLoading = ref(false);

    const closeModal = () => {
      emit('close');
    };

    const confirmBooking = async () => {
      isLoading.value = true;
      try {
        await bookingStore.bookCourse(props.course.id);
        emit('success');
        closeModal();
      } catch (error) {
        console.error('预约失败:', error);
        // 这里可以添加错误提示
      } finally {
        isLoading.value = false;
      }
    };

    const formatDateTime = (dateTimeString) => {
      const date = new Date(dateTimeString);
      return date.toLocaleString('zh-CN', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit'
      });
    };

    return {
      isLoading,
      closeModal,
      confirmBooking,
      formatDateTime
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

.modal-content {
  background: white;
  border-radius: 8px;
  width: 90%;
  max-width: 500px;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px;
  border-bottom: 1px solid #eee;
}

.modal-header h2 {
  margin: 0;
  color: #333;
}

.close-btn {
  background: none;
  border: none;
  font-size: 24px;
  cursor: pointer;
  color: #666;
}

.close-btn:hover {
  color: #333;
}

.modal-body {
  padding: 20px;
}

.course-info {
  background: #f8f9fa;
  padding: 15px;
  border-radius: 6px;
  margin-top: 15px;
}

.course-info h3 {
  margin: 0 0 10px 0;
  color: #2c3e50;
}

.course-info p {
  margin: 5px 0;
  color: #666;
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  padding: 20px;
  border-top: 1px solid #eee;
}

.btn {
  padding: 8px 20px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
  transition: background-color 0.3s;
}

.btn-cancel {
  background: #e0e0e0;
  color: #333;
}

.btn-cancel:hover {
  background: #d0d0d0;
}

.btn-confirm {
  background: #4CAF50;
  color: white;
}

.btn-confirm:hover:not(:disabled) {
  background: #45a049;
}

.btn-confirm:disabled {
  background: #cccccc;
  cursor: not-allowed;
}
</style>