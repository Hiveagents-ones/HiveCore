<template>
  <div v-if="isVisible" class="modal-overlay" @click="closeModal">
    <div class="modal-content" @click.stop>
      <header class="modal-header">
        <h2>预约课程</h2>
        <button class="close-button" @click="closeModal">&times;</button>
      </header>
      <main class="modal-body">
        <div v-if="course" class="course-info">
          <h3>{{ course.name }}</h3>
          <p><strong>教练:</strong> {{ course.coach }}</p>
          <p><strong>时间:</strong> {{ formatTime(course.time) }}</p>
          <p><strong>地点:</strong> {{ course.location }}</p>
          <p><strong>容量:</strong> {{ course.capacity }} 人</p>
          <p><strong>已预约:</strong> {{ course.booked_count || 0 }} 人</p>
        </div>
        <form @submit.prevent="submitBooking" class="booking-form">
          <div class="form-group">
            <label for="memberId">会员ID:</label>
            <input
              type="text"
              id="memberId"
              v-model="memberId"
              required
              placeholder="请输入会员ID"
              :disabled="isMember"
            />
            <small v-if="isMember" class="form-hint">当前登录会员ID</small>
          </div>
          <div class="form-actions">
            <button type="button" class="btn btn-secondary" @click="closeModal">
              取消
            </button>
            <button type="submit" class="btn btn-primary" :disabled="isLoading">
              {{ isLoading ? '预约中...' : '确认预约' }}
            </button>
          </div>
        </form>
      </main>
      <footer class="modal-footer">
        <p v-if="errorMessage" class="error-message">{{ errorMessage }}</p>
        <p v-if="successMessage" class="success-message">{{ successMessage }}</p>
      </footer>
    </div>
  </div>
</template>

<script>
import { ref, watch, onMounted } from 'vue';
import { coursesApi } from '../api/courses.js';
import { authAPI } from '../api/auth.js';

export default {
  name: 'BookingModal',
  props: {
    isVisible: {
      type: Boolean,
      required: true,
    },
    courseId: {
      type: [String, Number],
      required: true,
    },
  },
  emits: ['close', 'booking-success'],
  setup(props, { emit }) {
    const course = ref(null);
    const memberId = ref('');
    const isLoading = ref(false);
    const errorMessage = ref('');
    const successMessage = ref('');
    const currentUser = ref(null);
    const isMember = ref(false);

    // 格式化时间
    const formatTime = (timeString) => {
      if (!timeString) return '';
      const date = new Date(timeString);
      return date.toLocaleString('zh-CN', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
      });
    };

    // 获取当前用户信息
    const fetchCurrentUser = async () => {
      try {
        const user = await authAPI.getCurrentUser();
        currentUser.value = user;
        isMember.value = user.role === 'member';
        if (isMember.value) {
          memberId.value = user.id.toString();
        }
      } catch (error) {
        console.error('获取用户信息失败:', error);
        errorMessage.value = '无法获取用户信息';
      }
    };
    const formatTime = (timeString) => {
      if (!timeString) return '';
      const date = new Date(timeString);
      return date.toLocaleString('zh-CN', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
      });
    };

    // 获取课程详情
    const fetchCourseDetails = async () => {
      try {
        const courseData = await coursesApi.getCourseById(props.courseId);
        course.value = courseData;
      } catch (error) {
        console.error('获取课程详情失败:', error);
        errorMessage.value = '无法加载课程信息';
      }
    };

    // 提交预约
    const submitBooking = async () => {
      if (!memberId.value.trim()) {
        errorMessage.value = '请输入会员ID';
        return;
      }

      // 权限验证：只有会员可以预约
      if (!isMember.value) {
        errorMessage.value = '只有会员才能预约课程';
        return;
      }

      isLoading.value = true;
      errorMessage.value = '';
      successMessage.value = '';

      try {
        await coursesApi.bookCourse(props.courseId, memberId.value);
        successMessage.value = '预约成功！';
        emit('booking-success');
        setTimeout(() => {
          closeModal();
        }, 1500);
      } catch (error) {
        console.error('预约失败:', error);
        errorMessage.value = error.response?.data?.detail || '预约失败，请重试';
      } finally {
        isLoading.value = false;
      }
    };

    // 关闭弹窗
    const closeModal = () => {
      memberId.value = '';
      errorMessage.value = '';
      successMessage.value = '';
      emit('close');
    };

    // 监听弹窗显示状态
    watch(
      () => props.isVisible,
      (newVal) => {
        if (newVal) {
          fetchCourseDetails();
          fetchCurrentUser();
        }
      }
    );

    return {
      course,
      memberId,
      isLoading,
      errorMessage,
      successMessage,
      currentUser,
      isMember,
      formatTime,
      submitBooking,
      closeModal,
    };
  },
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
  max-height: 90vh;
  overflow-y: auto;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem;
  border-bottom: 1px solid #eee;
}

.modal-header h2 {
  margin: 0;
  font-size: 1.5rem;
  color: #333;
}

.close-button {
  background: none;
  border: none;
  font-size: 1.5rem;
  cursor: pointer;
  color: #666;
  padding: 0;
  width: 30px;
  height: 30px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.close-button:hover {
  color: #333;
}

.modal-body {
  padding: 1rem;
}

.course-info {
  margin-bottom: 1.5rem;
  padding: 1rem;
  background-color: #f8f9fa;
  border-radius: 4px;
}

.course-info h3 {
  margin-top: 0;
  margin-bottom: 0.5rem;
  color: #2c3e50;
}

.course-info p {
  margin: 0.25rem 0;
  font-size: 0.9rem;
  color: #555;
}

.booking-form {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.form-group label {
  font-weight: 500;
  color: #333;
}

.form-group input {
  padding: 0.5rem;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 1rem;
}

.form-group input:focus {
  outline: none;
  border-color: #4a90e2;
  box-shadow: 0 0 0 2px rgba(74, 144, 226, 0.2);
}

.form-actions {
  display: flex;
  gap: 1rem;
  justify-content: flex-end;
  margin-top: 1rem;
}

.btn {
  padding: 0.5rem 1rem;
  border: none;
  border-radius: 4px;
  font-size: 1rem;
  cursor: pointer;
  transition: background-color 0.2s;
}

.btn-primary {
  background-color: #4a90e2;
  color: white;
}

.btn-primary:hover:not(:disabled) {
  background-color: #357abd;
}

.btn-primary:disabled {
  background-color: #a0c3e7;
  cursor: not-allowed;
}

.btn-secondary {
  background-color: #e0e0e0;
  color: #333;
}

.btn-secondary:hover {
  background-color: #d0d0d0;
}

.modal-footer {
  padding: 1rem;
  border-top: 1px solid #eee;
}

.error-message {
  color: #e74c3c;
  font-size: 0.9rem;
  margin: 0;
}

.success-message {
  color: #2ecc71;
  font-size: 0.9rem;
  margin: 0;
}
</style>