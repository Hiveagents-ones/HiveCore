<template>
  <div class="course-card">
    <div class="course-image">
      <img :src="course.image || '/default-course.jpg'" :alt="course.name" />
    </div>
    <div class="course-content">
      <h3 class="course-title">{{ course.name }}</h3>
      <p class="course-instructor">教练: {{ course.instructor }}</p>
      <div class="course-info">
        <span class="course-time">{{ formatTime(course.time) }}</span>
        <span class="course-duration">{{ course.duration }}分钟</span>
      </div>
      <div class="course-availability">
        <span class="available-spots">剩余名额: {{ course.available_spots }}</span>
        <span class="total-spots">/ {{ course.capacity }}</span>
      </div>
      <div class="course-actions">
        <button 
          class="btn btn-primary"
          @click="viewDetails"
          :disabled="course.available_spots === 0"
        >
          {{ course.available_spots === 0 ? '已满' : '查看详情' }}
        </button>
        <button 
          class="btn btn-secondary"
          @click="bookCourse"
          :disabled="course.available_spots === 0"
        >
          {{ course.available_spots === 0 ? '已满' : '立即预约' }}
        </button>
      </div>
    </div>
  </div>
</template>

<script>
import { useRouter } from 'vue-router'
import { useBookingStore } from '../stores/booking'

export default {
  name: 'CourseCard',
  props: {
    course: {
      type: Object,
      required: true,
      validator: (value) => {
        return value && 
               typeof value.id === 'number' &&
               typeof value.name === 'string' &&
               typeof value.instructor === 'string' &&
               typeof value.time === 'string' &&
               typeof value.duration === 'number' &&
               typeof value.capacity === 'number' &&
               typeof value.available_spots === 'number'
      }
    }
  },
  setup(props) {
    const router = useRouter()
    const bookingStore = useBookingStore()

    const formatTime = (timeString) => {
      const date = new Date(timeString)
      return date.toLocaleString('zh-CN', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit'
      })
    }

    const viewDetails = () => {
      router.push(`/course/${props.course.id}`)
    }

    const bookCourse = async () => {
      if (props.course.available_spots === 0) return
      
      try {
        await bookingStore.bookCourse(props.course.id)
        // 可以添加成功提示
      } catch (error) {
        // 可以添加错误提示
        console.error('预约失败:', error)
      }
    }

    return {
      formatTime,
      viewDetails,
      bookCourse
    }
  }
}
</script>

<style scoped>
.course-card {
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  overflow: hidden;
  transition: transform 0.3s ease, box-shadow 0.3s ease;
  max-width: 320px;
}

.course-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.15);
}

.course-image {
  height: 180px;
  overflow: hidden;
}

.course-image img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.course-content {
  padding: 16px;
}

.course-title {
  font-size: 18px;
  font-weight: 600;
  margin: 0 0 8px 0;
  color: #333;
}

.course-instructor {
  font-size: 14px;
  color: #666;
  margin: 0 0 12px 0;
}

.course-info {
  display: flex;
  gap: 12px;
  margin-bottom: 12px;
}

.course-time,
.course-duration {
  font-size: 13px;
  color: #888;
}

.course-availability {
  margin-bottom: 16px;
}

.available-spots {
  font-size: 14px;
  font-weight: 500;
  color: #4CAF50;
}

.total-spots {
  font-size: 14px;
  color: #888;
}

.course-actions {
  display: flex;
  gap: 8px;
}

.btn {
  flex: 1;
  padding: 8px 16px;
  border: none;
  border-radius: 4px;
  font-size: 14px;
  cursor: pointer;
  transition: background-color 0.3s ease;
}

.btn-primary {
  background-color: #007bff;
  color: white;
}

.btn-primary:hover:not(:disabled) {
  background-color: #0056b3;
}

.btn-secondary {
  background-color: #6c757d;
  color: white;
}

.btn-secondary:hover:not(:disabled) {
  background-color: #545b62;
}

.btn:disabled {
  background-color: #ccc;
  cursor: not-allowed;
}
</style>