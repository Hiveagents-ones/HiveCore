<template>
  <div class="my-bookings">
    <div class="page-header">
      <h1>我的预约</h1>
      <p class="subtitle">查和管理您的课程预约</p>
    </div>

    <div v-if="loading" class="loading">
      <div class="spinner"></div>
      <p>加载中...</p>
    </div>

    <div v-else-if="error" class="error-message">
      <p>{{ error }}</p>
      <button @click="fetchBookings" class="retry-btn">重试</button>
    </div>

    <div v-else-if="bookings.length === 0" class="empty-state">
      <div class="empty-icon">📋</div>
      <h3>暂无预约记录</h3>
      <p>您还没有预约任何课程</p>
      <router-link to="/courses" class="browse-courses-btn">
        浏览课程
      </router-link>
    </div>

    <div v-else class="bookings-list">
      <div v-for="booking in bookings" :key="booking.id" class="booking-card">
        <div class="booking-header">
          <h3>{{ booking.course_name }}</h3>
          <span :class="['status-badge', booking.status]">
            {{ getStatusText(booking.status) }}
          </span>
        </div>
        
        <div class="booking-details">
          <div class="detail-item">
            <span class="label">日期：</span>
            <span>{{ formatDate(booking.course_date) }}</span>
          </div>
          <div class="detail-item">
            <span class="label">时间：</span>
            <span>{{ booking.start_time }} - {{ booking.end_time }}</span>
          </div>
          <div class="detail-item">
            <span class="label">教练：</span>
            <span>{{ booking.instructor_name || '待定' }}</span>
          </div>
          <div class="detail-item">
            <span class="label">预约时间：</span>
            <span>{{ formatDateTime(booking.created_at) }}</span>
          </div>
        </div>

        <div class="booking-actions">
          <button
            v-if="booking.status === 'confirmed' && canCancel(booking.course_date)"
            @click="handleCancel(booking.id)"
            class="cancel-btn"
            :disabled="cancelling === booking.id"
          >
            {{ cancelling === booking.id ? '取消中...' : '取消预约' }}
          </button>
          <span v-else-if="!canCancel(booking.course_date)" class="cannot-cancel">
            课程即将开始，无法取消
          </span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useToast } from 'vue-toastification'
import axios from 'axios'

const toast = useToast()
const bookings = ref([])
const loading = ref(true)
const error = ref(null)
const cancelling = ref(null)

const fetchBookings = async () => {
  try {
    loading.value = true
    error.value = null
    const response = await axios.get('/api/v1/bookings/my-bookings')
    bookings.value = response.data
  } catch (err) {
    console.error('Failed to fetch bookings:', err)
    error.value = '获取预约记录失败，请稍后重试'
  } finally {
    loading.value = false
  }
}

const handleCancel = async (bookingId) => {
  if (!confirm('确定要取消这个预约吗？')) {
    return
  }

  try {
    cancelling.value = bookingId
    await axios.delete(`/api/v1/bookings/${bookingId}`)
    toast.success('预约已取消')
    // 从列表中移除已取消的预约
    bookings.value = bookings.value.filter(b => b.id !== bookingId)
  } catch (err) {
    console.error('Failed to cancel booking:', err)
    toast.error(err.response?.data?.detail || '取消预约失败，请重试')
  } finally {
    cancelling.value = null
  }
}

const getStatusText = (status) => {
  const statusMap = {
    confirmed: '已确认',
    cancelled: '已取消',
    completed: '已完成'
  }
  return statusMap[status] || status
}

const formatDate = (dateString) => {
  const date = new Date(dateString)
  return date.toLocaleDateString('zh-CN', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
    weekday: 'long'
  })
}

const formatDateTime = (dateString) => {
  const date = new Date(dateString)
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}

const canCancel = (courseDate) => {
  const now = new Date()
  const courseDateTime = new Date(courseDate)
  // 课程开始前2小时内不能取消
  const twoHoursBeforeCourse = new Date(courseDateTime.getTime() - 2 * 60 * 60 * 1000)
  return now < twoHoursBeforeCourse
}

onMounted(() => {
  fetchBookings()
})
</script>

<style scoped>
.my-bookings {
  max-width: 800px;
  margin: 0 auto;
  padding: 2rem;
}

.page-header {
  text-align: center;
  margin-bottom: 2rem;
}

.page-header h1 {
  font-size: 2.5rem;
  color: #2c3e50;
  margin-bottom: 0.5rem;
}

.subtitle {
  color: #7f8c8d;
  font-size: 1.1rem;
}

.loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 3rem;
}

.spinner {
  width: 40px;
  height: 40px;
  border: 4px solid #f3f3f3;
  border-top: 4px solid #3498db;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin-bottom: 1rem;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.error-message {
  text-align: center;
  padding: 2rem;
  color: #e74c3c;
}

.retry-btn {
  margin-top: 1rem;
  padding: 0.5rem 1.5rem;
  background-color: #3498db;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  transition: background-color 0.3s;
}

.retry-btn:hover {
  background-color: #2980b9;
}

.empty-state {
  text-align: center;
  padding: 3rem;
}

.empty-icon {
  font-size: 4rem;
  margin-bottom: 1rem;
}

.empty-state h3 {
  color: #2c3e50;
  margin-bottom: 0.5rem;
}

.empty-state p {
  color: #7f8c8d;
  margin-bottom: 2rem;
}

.browse-courses-btn {
  display: inline-block;
  padding: 0.75rem 2rem;
  background-color: #27ae60;
  color: white;
  text-decoration: none;
  border-radius: 4px;
  transition: background-color 0.3s;
}

.browse-courses-btn:hover {
  background-color: #229954;
}

.bookings-list {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.booking-card {
  background: white;
  border-radius: 8px;
  padding: 1.5rem;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
  transition: transform 0.3s, box-shadow 0.3s;
}

.booking-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
}

.booking-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
}

.booking-header h3 {
  color: #2c3e50;
  font-size: 1.3rem;
  margin: 0;
}

.status-badge {
  padding: 0.25rem 0.75rem;
  border-radius: 20px;
  font-size: 0.85rem;
  font-weight: 500;
}

.status-badge.confirmed {
  background-color: #d4edda;
  color: #155724;
}

.status-badge.cancelled {
  background-color: #f8d7da;
  color: #721c24;
}

.status-badge.completed {
  background-color: #d1ecf1;
  color: #0c5460;
}

.booking-details {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1rem;
  margin-bottom: 1.5rem;
}

.detail-item {
  display: flex;
  align-items: center;
}

.label {
  font-weight: 500;
  color: #7f8c8d;
  margin-right: 0.5rem;
}

.booking-actions {
  display: flex;
  justify-content: flex-end;
  align-items: center;
}

.cancel-btn {
  padding: 0.5rem 1.5rem;
  background-color: #e74c3c;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  transition: background-color 0.3s;
}

.cancel-btn:hover:not(:disabled) {
  background-color: #c0392b;
}

.cancel-btn:disabled {
  background-color: #95a5a6;
  cursor: not-allowed;
}

.cannot-cancel {
  color: #e74c3c;
  font-size: 0.9rem;
}

@media (max-width: 768px) {
  .my-bookings {
    padding: 1rem;
  }

  .page-header h1 {
    font-size: 2rem;
  }

  .booking-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 0.5rem;
  }

  .booking-details {
    grid-template-columns: 1fr;
  }
}
</style>