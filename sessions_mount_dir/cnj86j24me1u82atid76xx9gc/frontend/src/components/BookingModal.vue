<template>
  <div v-if="isVisible" class="modal-overlay" @click="closeModal">
    <div class="modal-content" @click.stop>
      <div class="modal-header">
        <h2>{{ $t('booking.confirmTitle') }}</h2>
        <button class="close-btn" @click="closeModal">&times;</button>
      </div>
      <div class="modal-body">
        <div class="course-info">
          <h3>{{ course.name }}</h3>
          <p><strong>{{ $t('booking.instructor') }}:</strong> {{ course.instructor }}</p>
          <p><strong>{{ $t('booking.time') }}:</strong> {{ formatTime(course.startTime) }} - {{ formatTime(course.endTime) }}</p>
          <p><strong>{{ $t('booking.date') }}:</strong> {{ formatDate(course.date) }}</p>
          <p><strong>{{ $t('booking.capacity') }}:</strong> {{ course.bookedSlots }}/{{ course.maxCapacity }}</p>
        </div>
        <div class="booking-actions">
          <button 
            v-if="!isBooked" 
            class="btn btn-primary" 
            @click="confirmBooking"
            :disabled="isLoading || course.bookedSlots >= course.maxCapacity || !isLoggedIn"
          >
            {{ isLoading ? $t('booking.processing') : (isLoggedIn ? $t('booking.confirm') : $t('booking.loginRequired')) }}
          </button>
          <button 
            v-else 
            class="btn btn-danger" 
            @click="cancelBooking"
            :disabled="isLoading || !isLoggedIn"
          >
            {{ isLoading ? $t('booking.processing') : (isLoggedIn ? $t('booking.cancel') : $t('booking.loginRequired')) }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useBookingStore } from '@/stores/booking'
import { useToast } from 'vue-toastification'
import { useUserStore } from '@/stores/user'

const props = defineProps({
  isVisible: {
    type: Boolean,
    required: true
  },
  course: {
    type: Object,
    required: true
  },
  isBooked: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['close', 'booking-changed'])

const { t } = useI18n()
const bookingStore = useBookingStore()
const userStore = useUserStore()
const toast = useToast()
const isLoading = ref(false)

// 检查用户是否已登录
const isLoggedIn = computed(() => userStore.currentUser !== null)

const closeModal = () => {
  emit('close')
}

const formatTime = (time) => {
  return new Date(`2000-01-01T${time}`).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}

const formatDate = (date) => {
  return new Date(date).toLocaleDateString()
}

const confirmBooking = async () => {
  if (isLoading.value) return
  
  isLoading.value = true
  try {
    await bookingStore.createBooking({
      courseId: props.course.id,
      memberId: bookingStore.currentMemberId
    })
    toast.success(t('booking.success'))
    emit('booking-changed')
    closeModal()
  } catch (error) {
    toast.error(error.message || t('booking.error'))
  } finally {
    isLoading.value = false
  }
}

const cancelBooking = async () => {
  if (isLoading.value) return
  
  isLoading.value = true
  try {
    await bookingStore.cancelBooking(props.course.id)
    toast.success(t('booking.cancelSuccess'))
    emit('booking-changed')
    closeModal()
  } catch (error) {
    toast.error(error.message || t('booking.cancelError'))
  } finally {
    isLoading.value = false
  }
}
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
  color: #333;
}

.close-btn {
  background: none;
  border: none;
  font-size: 1.5rem;
  cursor: pointer;
  color: #666;
}

.close-btn:hover {
  color: #333;
}

.modal-body {
  padding: 1.5rem;
}

.course-info {
  margin-bottom: 1.5rem;
}

.course-info h3 {
  margin-top: 0;
  color: #2c3e50;
}

.course-info p {
  margin: 0.5rem 0;
  color: #555;
}

.booking-actions {
  display: flex;
  justify-content: center;
  gap: 1rem;
}

.btn {
  padding: 0.75rem 1.5rem;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 1rem;
  transition: all 0.3s ease;
}

.btn-primary {
  background-color: #3498db;
  color: white;
}

.btn-primary:hover:not(:disabled) {
  background-color: #2980b9;
}

.btn-danger {
  background-color: #e74c3c;
  color: white;
}

.btn-danger:hover:not(:disabled) {
  background-color: #c0392b;
}

.btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
</style>