<template>
  <div class="course-card">
    <div class="course-header">
      <h3 class="course-title">{{ course.name }}</h3>
      <span class="course-category">{{ course.category }}</span>
    </div>
    <div class="course-body">
      <p class="course-instructor">{{ $t('instructor') }}: {{ course.instructor }}</p>
      <p class="course-time">{{ $t('time') }}: {{ formatTime(course.start_time) }} - {{ formatTime(course.end_time) }}</p>
      <p class="course-capacity">
        {{ $t('availableSlots') }}: {{ course.capacity - course.booked_count }}/{{ course.capacity }}
      </p>
      <div class="course-actions">
        <button
          v-if="isBooked"
          @click="handleCancel"
          class="btn btn-cancel"
          :disabled="loading"
        >
          {{ $t('cancelBooking') }}
        </button>
        <button
          v-else
          @click="handleBook"
          class="btn btn-book"
          :disabled="loading || course.capacity <= course.booked_count"
        >
          {{ $t('bookNow') }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useCourseStore } from '@/stores/course'
import { useUserStore } from '@/stores/user'

const props = defineProps({
  course: {
    type: Object,
    required: true
  }
})

const emit = defineEmits(['refresh'])

const { t } = useI18n()
const courseStore = useCourseStore()
const userStore = useUserStore()

const loading = ref(false)

const isBooked = computed(() => {
  return props.course.bookings?.some(booking => booking.user_id === userStore.currentUser?.id)
})

const formatTime = (timeString) => {
  if (!timeString) return ''
  const date = new Date(timeString)
  return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
}

const handleBook = async () => {
  if (!userStore.currentUser) {
    alert(t('pleaseLogin'))
    return
  }

  loading.value = true
  try {
    await courseStore.bookCourse(props.course.id)
    emit('refresh')
  } catch (error) {
    console.error('Booking failed:', error)
    alert(error.message || t('bookingFailed'))
  } finally {
    loading.value = false
  }
}

const handleCancel = async () => {
  if (!userStore.currentUser) {
    alert(t('pleaseLogin'))
    return
  }

  loading.value = true
  try {
    await courseStore.cancelBooking(props.course.id)
    emit('refresh')
  } catch (error) {
    console.error('Cancellation failed:', error)
    alert(error.message || t('cancellationFailed'))
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
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
  align-items: center;
  margin-bottom: 1rem;
}

.course-title {
  font-size: 1.25rem;
  font-weight: 600;
  color: #2c3e50;
  margin: 0;
}

.course-category {
  background: #e3f2fd;
  color: #1976d2;
  padding: 0.25rem 0.75rem;
  border-radius: 16px;
  font-size: 0.875rem;
}

.course-body {
  color: #546e7a;
}

.course-body p {
  margin: 0.5rem 0;
  font-size: 0.95rem;
}

.course-actions {
  margin-top: 1rem;
  padding-top: 1rem;
  border-top: 1px solid #e0e0e0;
}

.btn {
  padding: 0.5rem 1.5rem;
  border: none;
  border-radius: 4px;
  font-size: 0.95rem;
  cursor: pointer;
  transition: background-color 0.2s, opacity 0.2s;
  font-weight: 500;
}

.btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-book {
  background-color: #4caf50;
  color: white;
}

.btn-book:hover:not(:disabled) {
  background-color: #45a049;
}

.btn-cancel {
  background-color: #f44336;
  color: white;
}

.btn-cancel:hover:not(:disabled) {
  background-color: #da190b;
}
</style>